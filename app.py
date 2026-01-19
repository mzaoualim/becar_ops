from __future__ import annotations

import datetime as dt
import json
from typing import Tuple, Optional
from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px

from src.i18n import LOCALES, t
from src.auth import check_password
from src.mock_data import generate_all
from src.quality import normalize_columns, ops_quality_report, capa_quality_report, mir_quality_report
from src.kpi import compute_ops_kpis, compute_variances, summarize
from src.scoring import add_risk_scoring, build_recommendations
from src.exports import df_to_csv_bytes, make_briefing_pdf, make_zip_pack


def k(page: str, name: str) -> str:
    """Stable unique key helper for Streamlit widgets."""
    return f"{page}__{name}"


def init_state(seed: int = 42, n_days: int = 90, n_equipment: int = 12, n_contracts: int = 6) -> None:
    if "ops_df" not in st.session_state:
        ops, targets, capa, mir = generate_all(seed=seed, n_days=n_days, n_equipment=n_equipment, n_contracts=n_contracts)
        st.session_state["ops_df"] = ops
        st.session_state["targets_df"] = targets
        st.session_state["capa_df"] = capa
        st.session_state["mir_df"] = mir

    if "scenario_library" not in st.session_state:
        st.session_state["scenario_library"] = []


def get_current_data() -> Tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    return (
        st.session_state.get("ops_df", pd.DataFrame()),
        st.session_state.get("targets_df", pd.DataFrame()),
        st.session_state.get("capa_df", pd.DataFrame()),
        st.session_state.get("mir_df", pd.DataFrame()),
    )


def apply_filters(df: pd.DataFrame, date_range: Optional[Tuple[pd.Timestamp, pd.Timestamp]],
                  subsidiary: str, activity: str, contract: str, equipment_id: str) -> pd.DataFrame:
    out = df.copy()
    if date_range and len(date_range) == 2:
        start, end = date_range
        out = out[(out["date"] >= start) & (out["date"] <= end)]

    if subsidiary != "(All)":
        out = out[out["subsidiary"] == subsidiary]
    if activity != "(All)":
        out = out[out["activity"] == activity]
    if contract != "(All)":
        out = out[out["contract"] == contract]
    if equipment_id != "(All)":
        out = out[out["equipment_id"] == equipment_id]

    return out


def home_tab(locale: str, presenter: bool) -> None:
    st.title(t(locale, "app_title"))
    st.caption(t(locale, "app_subtitle"))

    st.info(t(locale, "disclaimer"))

    ops_df, targets_df, capa_df, mir_df = get_current_data()
    df_kpi = compute_ops_kpis(ops_df)
    df_var = compute_variances(df_kpi, targets_df)
    df_scored = add_risk_scoring(df_var)

    summ = summarize(df_kpi)

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t(locale, "metric_revenue"), f"{summ['revenue']:,.0f}")
    c2.metric(t(locale, "metric_cost"), f"{summ['total_cost']:,.0f}")
    c3.metric(t(locale, "metric_profit"), f"{summ['profit']:,.0f}")
    c4.metric(t(locale, "metric_margin"), f"{summ['margin']*100:,.1f}%")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t(locale, "metric_cpkm"), f"{summ['cost_per_km']:,.2f}")
    c2.metric(t(locale, "metric_cph"), f"{summ['cost_per_hour']:,.2f}")
    c3.metric(t(locale, "metric_cpm3"), f"{summ['cost_per_m3']:,.2f}")
    c4.metric("Downtime (h)", f"{summ['downtime_hours']:,.1f}")

    st.subheader(t(locale, "section_quick_value"))
    st.write("\n".join([
        f"1) {t(locale, 'value_1')}" ,
        f"2) {t(locale, 'value_2')}" ,
        f"3) {t(locale, 'value_3')}" ,
        f"4) {t(locale, 'value_4')}" ,
        f"5) {t(locale, 'value_5')}" ,
    ]))
    if presenter:
        with st.expander("🎙️ Talk track (90 seconds)", expanded=True):
            st.markdown(
                """
- **15s**: Je vous montre un cockpit KPI (coût/km, coût/h, coût/m³) par activité/contrat/équipement.
- **20s**: On drill‑down sur les écarts vs cibles (carburant, entretien, downtime) et la rentabilité.
- **20s**: On obtient une liste priorisée d’optimisations d’actifs (utilisation, arrêts, surcoûts).
- **20s**: On transforme les écarts en **plan de redressement** (CAPA) : qui/quoi/quand/statut.
- **15s**: Et on prépare l’implantation **MIR** via des gabarits + contrôles qualité + KPIs maintenance.
                """
            )

    # Briefing PDF
    highlights = []
    top_issues = df_scored.sort_values(["risk_score", "profit"], ascending=[False, True]).head(6)
    for r in top_issues.itertuples():
        highlights.append(
            f"{r.subsidiary} | {r.activity} | {r.contract} | {r.equipment_id} — risk {r.risk_level} ({r.risk_score:.0f}), profit {r.profit:,.0f}"
        )

    pdf = make_briefing_pdf(
        title="Bécar — Operational Controller Cockpit (Demo)",
        subtitle=f"Synthetic demo dataset • generated {dt.datetime.now().strftime('%Y-%m-%d %H:%M')}",
        summary=summ,
        highlights=highlights,
    )

    pack_files = {
        "data/ops_runs.csv": df_to_csv_bytes(ops_df),
        "data/targets.csv": df_to_csv_bytes(targets_df),
        "data/capa.csv": df_to_csv_bytes(capa_df),
        "data/mir_events.csv": df_to_csv_bytes(mir_df),
        "outputs/scored_variances.csv": df_to_csv_bytes(df_scored),
        "outputs/recommendations.csv": df_to_csv_bytes(build_recommendations(df_scored, top_n=12)),
        "briefing_note.pdf": pdf,
    }
    meta = {
        "generated_at": dt.datetime.now().isoformat(timespec="seconds"),
        "data": "synthetic (default)",
        "note": "Portfolio demo – do not use confidential data without permission.",
    }
    zip_bytes = make_zip_pack(pack_files, meta=meta)

    c1, c2 = st.columns(2)
    c1.download_button(
        t(locale, "btn_download_brief"),
        data=pdf,
        file_name="becar_briefing_note.pdf",
        mime="application/pdf",
        key=k("home", "dl_brief"),
    )
    c2.download_button(
        t(locale, "btn_download_pack"),
        data=zip_bytes,
        file_name="becar_demo_pack.zip",
        mime="application/zip",
        key=k("home", "dl_pack"),
    )


def data_tab(locale: str) -> None:
    st.subheader(t(locale, "tabs_data"))

    ops_df, targets_df, capa_df, mir_df = get_current_data()

    source = st.radio(
        t(locale, "data_source"),
        [t(locale, "data_synthetic"), t(locale, "data_upload")],
        key=k("data", "source"),
    )

    st.markdown("---")
    st.subheader(t(locale, "templates"))

    # Download CSV templates
    tmpl_ops = (Path("data") / "template_ops_runs.csv").read_bytes()
    tmpl_capa = (Path("data") / "template_capa.csv").read_bytes()
    tmpl_mir = (Path("data") / "template_mir_events.csv").read_bytes()

    c1, c2, c3 = st.columns(3)
    c1.download_button(
        t(locale, "download_template_ops"),
        data=tmpl_ops,
        file_name="template_ops_runs.csv",
        mime="text/csv",
        key=k("data", "dl_tmpl_ops"),
    )
    c2.download_button(
        t(locale, "download_template_capa"),
        data=tmpl_capa,
        file_name="template_capa.csv",
        mime="text/csv",
        key=k("data", "dl_tmpl_capa"),
    )
    c3.download_button(
        t(locale, "download_template_mir"),
        data=tmpl_mir,
        file_name="template_mir_events.csv",
        mime="text/csv",
        key=k("data", "dl_tmpl_mir"),
    )

    st.markdown("---")

    if source == t(locale, "data_synthetic"):
        c1, c2, c3, c4 = st.columns(4)
        seed = c1.number_input(t(locale, "seed"), min_value=0, max_value=999999, value=42, step=1, key=k("data", "seed"))
        days = c2.slider(t(locale, "days"), min_value=30, max_value=365, value=90, step=15, key=k("data", "days"))
        equip = c3.slider(t(locale, "equip"), min_value=4, max_value=60, value=12, step=2, key=k("data", "equip"))
        contracts = c4.slider(t(locale, "contracts"), min_value=2, max_value=30, value=6, step=1, key=k("data", "contracts"))

        if st.button(t(locale, "btn_generate"), key=k("data", "btn_generate")):
            ops, targets, capa, mir = generate_all(seed=int(seed), n_days=int(days), n_equipment=int(equip), n_contracts=int(contracts))
            st.session_state["ops_df"] = ops
            st.session_state["targets_df"] = targets
            st.session_state["capa_df"] = capa
            st.session_state["mir_df"] = mir
            st.success("✅ Data regenerated")

    else:
        ops_file = st.file_uploader(t(locale, "uploader_ops"), type=["csv"], key=k("data", "upl_ops"))
        capa_file = st.file_uploader(t(locale, "uploader_capa"), type=["csv"], key=k("data", "upl_capa"))
        mir_file = st.file_uploader(t(locale, "uploader_mir"), type=["csv"], key=k("data", "upl_mir"))

        if ops_file is not None:
            df = pd.read_csv(ops_file)
            df = normalize_columns(df)
            st.session_state["ops_df"] = df
            # re-generate targets from imported data
            from src.mock_data import generate_targets
            st.session_state["targets_df"] = generate_targets(df)

        if capa_file is not None:
            dfc = pd.read_csv(capa_file)
            st.session_state["capa_df"] = normalize_columns(dfc)

        if mir_file is not None:
            dfm = pd.read_csv(mir_file)
            st.session_state["mir_df"] = normalize_columns(dfm)

    st.markdown("---")
    st.subheader(t(locale, "preview"))
    st.write("Operations")
    st.dataframe(st.session_state["ops_df"].head(30), use_container_width=True)
    st.write("CAPA")
    st.dataframe(st.session_state["capa_df"].head(20), use_container_width=True)
    st.write("MIR events")
    st.dataframe(st.session_state["mir_df"].head(20), use_container_width=True)


def quality_tab(locale: str) -> None:
    st.subheader(t(locale, "tabs_quality"))

    ops_df, targets_df, capa_df, mir_df = get_current_data()

    ops_r = ops_quality_report(ops_df)
    capa_r = capa_quality_report(capa_df)
    mir_r = mir_quality_report(mir_df)

    c1, c2, c3 = st.columns(3)
    c1.metric("Ops rows", ops_r["summary"]["rows"])
    c2.metric("CAPA rows", capa_r["summary"]["rows"])
    c3.metric("MIR rows", mir_r["summary"]["rows"])

    st.markdown("### Operations")
    st.dataframe(ops_r["issues"], use_container_width=True)

    st.markdown("### CAPA")
    st.dataframe(capa_r["issues"], use_container_width=True)

    st.markdown("### MIR")
    st.dataframe(mir_r["issues"], use_container_width=True)


def cockpit_tab(locale: str, presenter: bool) -> None:
    st.subheader(t(locale, "tabs_cockpit"))

    ops_df, targets_df, capa_df, mir_df = get_current_data()
    df_kpi = compute_ops_kpis(ops_df)

    # Filters
    st.markdown(f"#### {t(locale, 'kpi_filters')}")
    df_kpi = df_kpi.dropna(subset=["date"])
    min_d = df_kpi["date"].min()
    max_d = df_kpi["date"].max()

    c1, c2, c3, c4, c5 = st.columns(5)
    date_range = c1.date_input(
        t(locale, "date_range"),
        value=(min_d.date(), max_d.date()),
        key=k("cockpit", "date"),
    )
    # Convert to timestamps
    if isinstance(date_range, tuple) and len(date_range) == 2:
        date_range_ts = (pd.to_datetime(date_range[0]), pd.to_datetime(date_range[1]))
    else:
        date_range_ts = None

    subs = ["(All)"] + sorted(df_kpi["subsidiary"].dropna().unique().tolist())
    acts = ["(All)"] + sorted(df_kpi["activity"].dropna().unique().tolist())
    ctrs = ["(All)"] + sorted(df_kpi["contract"].dropna().unique().tolist())
    eqs = ["(All)"] + sorted(df_kpi["equipment_id"].dropna().unique().tolist())

    subsidiary = c2.selectbox(t(locale, "subsidiary"), subs, key=k("cockpit", "sub"))
    activity = c3.selectbox(t(locale, "activity"), acts, key=k("cockpit", "act"))
    contract = c4.selectbox(t(locale, "contract"), ctrs, key=k("cockpit", "ctr"))
    equipment_id = c5.selectbox(t(locale, "equipment_id"), eqs, key=k("cockpit", "eq"))

    df_f = apply_filters(df_kpi, date_range_ts, subsidiary, activity, contract, equipment_id)

    summ = summarize(df_f)
    c1, c2, c3, c4 = st.columns(4)
    c1.metric(t(locale, "metric_revenue"), f"{summ['revenue']:,.0f}")
    c2.metric(t(locale, "metric_cost"), f"{summ['total_cost']:,.0f}")
    c3.metric(t(locale, "metric_profit"), f"{summ['profit']:,.0f}")
    c4.metric(t(locale, "metric_margin"), f"{summ['margin']*100:,.1f}%")

    # Charts
    st.markdown("---")
    left, right = st.columns(2)

    # Time series cost/km
    ts = df_f.groupby(pd.Grouper(key="date", freq="W"), as_index=False)["cost_per_km"].median(numeric_only=True)
    fig1 = px.line(ts, x="date", y="cost_per_km", title="Median cost per km (weekly)")
    left.plotly_chart(fig1, use_container_width=True)

    # Profit by contract
    by_ctr = df_f.groupby("contract", as_index=False).agg({"profit": "sum", "revenue": "sum"})
    by_ctr["margin"] = by_ctr.apply(lambda r: (r.profit / r.revenue) if r.revenue else 0.0, axis=1)
    fig2 = px.bar(by_ctr.sort_values("profit"), x="contract", y="profit", title="Profit by contract")
    right.plotly_chart(fig2, use_container_width=True)

    st.markdown("---")
    st.markdown("### Asset optimization (actionable)")

    # Build recommendations from scored variances
    df_var = compute_variances(df_kpi, targets_df)
    df_scored = add_risk_scoring(df_var)
    recs = build_recommendations(df_scored, top_n=10)

    st.dataframe(recs, use_container_width=True)

    if presenter:
        st.caption("Tip: pick 1 recommendation and show the drill‑down in the Variances tab.")


def variance_tab(locale: str, presenter: bool) -> None:
    st.subheader(t(locale, "tabs_variance"))

    ops_df, targets_df, capa_df, mir_df = get_current_data()
    df_kpi = compute_ops_kpis(ops_df)
    df_var = compute_variances(df_kpi, targets_df)
    df_scored = add_risk_scoring(df_var)

    st.markdown(f"#### {t(locale, 'variance_title')}")

    # Aggregate by contract/equipment
    grp = df_scored.groupby(["subsidiary", "activity", "contract", "equipment_id"], as_index=False).agg({
        "revenue": "sum",
        "total_cost": "sum",
        "profit": "sum",
        "cost_per_km": "median",
        "cost_per_hour": "median",
        "cost_per_m3": "median",
        "var_cpkm_pct": "mean",
        "var_cph_pct": "mean",
        "downtime_hours": "sum",
        "risk_score": "mean",
    })

    grp = grp.sort_values(["risk_score", "profit"], ascending=[False, True])

    st.dataframe(grp.head(40), use_container_width=True)

    if presenter:
        with st.expander("🎙️ Talk track: plan de redressement", expanded=True):
            st.markdown(
                """
- **Choisir une ligne** à risque élevé (risk_score + profit négatif).
- Expliquer les drivers: variance coût/km vs cible, downtime, carburant.
- Proposer 2–3 actions (ex: optimisation tournées, maintenance préventive via MIR, revue de taux/contrat).
- Conclure: on suit l'action dans un tableau CAPA avec échéances + reddition.
                """
            )

    # Auto-generate CAPA proposals
    if st.button(t(locale, "btn_generate_capa"), key=k("var", "btn_gen_capa")):
        # Create CAPA rows from top issues
        top = grp.head(10)
        new_rows = []
        today = dt.date.today()
        for i, r in enumerate(top.itertuples(index=False), start=1):
            new_rows.append({
                "capa_id": f"AUTO-{today.strftime('%Y%m%d')}-{i:02d}",
                "created_date": today.isoformat(),
                "issue_type": "cost_variance",
                "priority": "High" if r.risk_score >= 55 else "Medium",
                "subsidiary": r.subsidiary,
                "activity": r.activity,
                "contract": r.contract,
                "equipment_id": r.equipment_id,
                "owner": "Opérations",
                "due_date": (today + dt.timedelta(days=14)).isoformat(),
                "status": "Open",
                "root_cause": "",
                "action_plan": "",
                "expected_impact": "",
            })
        capa_df = pd.concat([capa_df, pd.DataFrame(new_rows)], ignore_index=True)
        st.session_state["capa_df"] = capa_df
        st.success(f"✅ {len(new_rows)} actions added to CAPA")

    # Export
    st.download_button(
        "Download scored variances (CSV)",
        data=df_to_csv_bytes(df_scored),
        file_name="becar_scored_variances.csv",
        mime="text/csv",
        key=k("var", "dl_scored"),
    )


def actions_tab(locale: str) -> None:
    st.subheader(t(locale, "tabs_actions"))

    ops_df, targets_df, capa_df, mir_df = get_current_data()

    st.markdown(f"#### {t(locale, 'actions_title')}")

    # Editable action plan
    editable = capa_df.copy()
    edited = st.data_editor(
        editable,
        num_rows="dynamic",
        use_container_width=True,
        key=k("actions", "editor"),
    )
    st.session_state["capa_df"] = edited

    st.download_button(
        t(locale, "download_actions"),
        data=df_to_csv_bytes(edited),
        file_name="becar_capa.csv",
        mime="text/csv",
        key=k("actions", "dl_capa"),
    )


def mir_tab(locale: str, presenter: bool) -> None:
    st.subheader(t(locale, "tabs_mir"))

    ops_df, targets_df, capa_df, mir_df = get_current_data()

    st.markdown("### MIR events (maintenance)")
    st.dataframe(mir_df.head(40), use_container_width=True)

    # Compute simple maintenance KPIs
    df = mir_df.copy()
    df["event_date"] = pd.to_datetime(df["event_date"], errors="coerce")
    for c in ["labor_hours", "parts_cost", "downtime_hours"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")

    agg = df.groupby("equipment_id", as_index=False).agg({
        "work_order_id": "count",
        "labor_hours": "sum",
        "parts_cost": "sum",
        "downtime_hours": "sum",
    }).rename(columns={"work_order_id": "event_count"})

    agg["maint_cost"] = agg["parts_cost"] + (agg["labor_hours"] * 55.0)  # demo hourly rate

    st.markdown("### Maintenance KPIs by equipment")
    st.dataframe(agg.sort_values("downtime_hours", ascending=False).head(30), use_container_width=True)

    fig = px.bar(agg.sort_values("downtime_hours", ascending=False).head(15), x="equipment_id", y="downtime_hours", title="Downtime by equipment")
    st.plotly_chart(fig, use_container_width=True)

    if presenter:
        st.caption("MIR readiness = define the data model, enforce quality rules, and automate weekly maintenance KPIs.")

    st.download_button(
        "Download MIR events (CSV)",
        data=df_to_csv_bytes(mir_df),
        file_name="becar_mir_events.csv",
        mime="text/csv",
        key=k("mir", "dl_mir"),
    )


def scenarios_tab(locale: str) -> None:
    st.subheader(t(locale, "tabs_scenarios"))

    ops_df, targets_df, capa_df, mir_df = get_current_data()
    base_kpi = compute_ops_kpis(ops_df)
    base_summary = summarize(base_kpi)

    st.markdown(f"#### {t(locale, 'scenarios_title')}")

    c1, c2, c3 = st.columns(3)
    scenario_name = c1.text_input(t(locale, "scenario_name"), value="Scenario A", key=k("sc", "name"))
    mult_fuel = c1.slider(t(locale, "mult_fuel"), 0.7, 1.6, 1.0, 0.05, key=k("sc", "fuel"))
    mult_maint = c1.slider(t(locale, "mult_maint"), 0.7, 1.8, 1.0, 0.05, key=k("sc", "maint"))

    mult_labor = c2.slider(t(locale, "mult_labor"), 0.7, 1.5, 1.0, 0.05, key=k("sc", "labor"))
    mult_over = c2.slider(t(locale, "mult_over"), 0.7, 1.5, 1.0, 0.05, key=k("sc", "over"))

    mult_rev = c3.slider(t(locale, "mult_rev"), 0.7, 1.5, 1.0, 0.05, key=k("sc", "rev"))
    mult_vol = c3.slider(t(locale, "mult_vol"), 0.7, 1.5, 1.0, 0.05, key=k("sc", "vol"))

    if st.button(t(locale, "btn_apply_scenario"), key=k("sc", "apply")):
        df = ops_df.copy()
        # Apply multipliers
        df["fuel_cost"] = pd.to_numeric(df["fuel_cost"], errors="coerce") * float(mult_fuel)
        df["maintenance_cost"] = pd.to_numeric(df["maintenance_cost"], errors="coerce") * float(mult_maint)
        df["labor_cost"] = pd.to_numeric(df["labor_cost"], errors="coerce") * float(mult_labor)
        df["overhead_cost"] = pd.to_numeric(df["overhead_cost"], errors="coerce") * float(mult_over)
        df["revenue"] = pd.to_numeric(df["revenue"], errors="coerce") * float(mult_rev)
        df["km_driven"] = pd.to_numeric(df["km_driven"], errors="coerce") * float(mult_vol)
        df["m3_moved"] = pd.to_numeric(df["m3_moved"], errors="coerce") * float(mult_vol)

        sc_kpi = compute_ops_kpis(df)
        sc_summary = summarize(sc_kpi)

        # Store in session
        st.session_state["current_scenario"] = {
            "name": scenario_name,
            "params": {
                "mult_fuel": float(mult_fuel),
                "mult_maint": float(mult_maint),
                "mult_labor": float(mult_labor),
                "mult_over": float(mult_over),
                "mult_rev": float(mult_rev),
                "mult_vol": float(mult_vol),
            },
            "summary": sc_summary,
        }

    sc = st.session_state.get("current_scenario")
    if sc:
        st.markdown(f"### {t(locale, 'compare_to_base')}")
        s = sc["summary"]

        def delta(a, b):
            return a - b

        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Profit", f"{s['profit']:,.0f}", f"{delta(s['profit'], base_summary['profit']):,.0f}")
        c2.metric("Costs", f"{s['total_cost']:,.0f}", f"{delta(s['total_cost'], base_summary['total_cost']):,.0f}")
        c3.metric("Cost/km", f"{s['cost_per_km']:,.2f}", f"{delta(s['cost_per_km'], base_summary['cost_per_km']):,.2f}")
        c4.metric("Margin", f"{s['margin']*100:,.1f}%", f"{delta(s['margin'], base_summary['margin'])*100:,.1f} pp")

        if st.button(t(locale, "btn_save_scenario"), key=k("sc", "save")):
            lib = st.session_state.get("scenario_library", [])
            lib.append(sc)
            st.session_state["scenario_library"] = lib
            st.success("✅ Scenario saved")

    st.markdown("---")
    st.markdown("### Scenario library")
    lib = st.session_state.get("scenario_library", [])
    if lib:
        df_lib = pd.DataFrame([
            {
                "name": x.get("name"),
                "profit": x.get("summary", {}).get("profit"),
                "total_cost": x.get("summary", {}).get("total_cost"),
                "margin": x.get("summary", {}).get("margin"),
                **x.get("params", {}),
            }
            for x in lib
        ])
        st.dataframe(df_lib, use_container_width=True)

        st.download_button(
            "Download scenario library (CSV)",
            data=df_to_csv_bytes(df_lib),
            file_name="becar_scenarios.csv",
            mime="text/csv",
            key=k("sc", "dl_lib"),
        )
    else:
        st.caption("No saved scenarios yet.")


def main() -> None:
    st.set_page_config(page_title="Bécar Ops Controller Cockpit", layout="wide")

    # Sidebar: language selection BEFORE auth, so the login prompt can be localized.
    with st.sidebar:
        st.markdown("###")
        lang_label = st.selectbox(
            "Language / Langue",
            list(LOCALES.keys()),
            index=0,
            key=k("sidebar", "lang"),
        )

    locale = LOCALES.get(lang_label, "fr_qc")

    with st.sidebar:
        presenter = st.toggle(
            t(locale, "sidebar_mode"),
            value=True,
            help=t(locale, "sidebar_mode_help"),
            key=k("sidebar", "presenter"),
        )

    # Password gate
    if not check_password(locale):
        st.stop()

    init_state()

    tabs = st.tabs([
        t(locale, "tabs_home"),
        t(locale, "tabs_data"),
        t(locale, "tabs_quality"),
        t(locale, "tabs_cockpit"),
        t(locale, "tabs_variance"),
        t(locale, "tabs_actions"),
        t(locale, "tabs_mir"),
        t(locale, "tabs_scenarios"),
    ])

    with tabs[0]:
        home_tab(locale, presenter)
    with tabs[1]:
        data_tab(locale)
    with tabs[2]:
        quality_tab(locale)
    with tabs[3]:
        cockpit_tab(locale, presenter)
    with tabs[4]:
        variance_tab(locale, presenter)
    with tabs[5]:
        actions_tab(locale)
    with tabs[6]:
        mir_tab(locale, presenter)
    with tabs[7]:
        scenarios_tab(locale)


if __name__ == "__main__":
    main()
