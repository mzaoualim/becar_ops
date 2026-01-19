from __future__ import annotations

import numpy as np
import pandas as pd


def safe_div(num, den):
    return np.where(den > 0, num / den, np.nan)


def compute_ops_kpis(df_ops: pd.DataFrame) -> pd.DataFrame:
    df = df_ops.copy()
    for c in [
        "hours_operated",
        "km_driven",
        "m3_moved",
        "revenue",
        "fuel_cost",
        "labor_cost",
        "maintenance_cost",
        "overhead_cost",
        "downtime_hours",
        "incident_count",
        "near_miss_count",
    ]:
        if c in df.columns:
            df[c] = pd.to_numeric(df[c], errors="coerce")

    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    df["total_cost"] = df[["fuel_cost", "labor_cost", "maintenance_cost", "overhead_cost"]].sum(axis=1)
    df["profit"] = df["revenue"] - df["total_cost"]
    df["margin"] = safe_div(df["profit"], df["revenue"])

    df["cost_per_hour"] = safe_div(df["total_cost"], df["hours_operated"])
    df["cost_per_km"] = safe_div(df["total_cost"], df["km_driven"])
    df["cost_per_m3"] = safe_div(df["total_cost"], df["m3_moved"])

    df["fuel_share"] = safe_div(df["fuel_cost"], df["total_cost"])
    df["maint_share"] = safe_div(df["maintenance_cost"], df["total_cost"])
    df["labor_share"] = safe_div(df["labor_cost"], df["total_cost"])

    df["utilization"] = safe_div(df["hours_operated"], df["hours_operated"] + df["downtime_hours"])

    return df


def compute_variances(df_kpi: pd.DataFrame, targets: pd.DataFrame) -> pd.DataFrame:
    df = df_kpi.copy()
    t = targets.copy()

    merged = df.merge(t, on=["subsidiary", "activity"], how="left")

    merged["var_cph"] = merged["cost_per_hour"] - merged["target_cph"]
    merged["var_cpkm"] = merged["cost_per_km"] - merged["target_cpkm"]
    merged["var_cpm3"] = merged["cost_per_m3"] - merged["target_cpm3"]

    merged["var_cph_pct"] = safe_div(merged["var_cph"], merged["target_cph"])
    merged["var_cpkm_pct"] = safe_div(merged["var_cpkm"], merged["target_cpkm"])
    merged["var_cpm3_pct"] = safe_div(merged["var_cpm3"], merged["target_cpm3"])

    return merged


def summarize(df: pd.DataFrame) -> dict:
    out = {}
    out["revenue"] = float(df["revenue"].sum())
    out["total_cost"] = float(df["total_cost"].sum())
    out["profit"] = float(df["profit"].sum())
    out["margin"] = float(np.nanmean(df["margin"])) if len(df) else float("nan")

    out["cost_per_km"] = float(np.nanmedian(df["cost_per_km"])) if len(df) else float("nan")
    out["cost_per_hour"] = float(np.nanmedian(df["cost_per_hour"])) if len(df) else float("nan")
    out["cost_per_m3"] = float(np.nanmedian(df["cost_per_m3"])) if len(df) else float("nan")

    out["downtime_hours"] = float(df["downtime_hours"].sum()) if "downtime_hours" in df.columns else 0.0
    return out
