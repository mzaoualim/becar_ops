from __future__ import annotations

import pandas as pd
import numpy as np

OPS_REQUIRED = [
    "date",
    "subsidiary",
    "activity",
    "contract",
    "team",
    "equipment_id",
    "hours_operated",
    "km_driven",
    "m3_moved",
    "revenue",
    "fuel_cost",
    "labor_cost",
    "maintenance_cost",
    "overhead_cost",
    "downtime_hours",
]

CAPA_REQUIRED = [
    "capa_id",
    "created_date",
    "issue_type",
    "priority",
    "subsidiary",
    "activity",
    "contract",
    "equipment_id",
    "owner",
    "due_date",
    "status",
]

MIR_REQUIRED = [
    "equipment_id",
    "event_date",
    "event_type",
    "work_order_id",
    "labor_hours",
    "parts_cost",
    "downtime_hours",
]


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Best-effort column normalization for common synonyms."""
    mapping = {
        "equip": "equipment_id",
        "equipment": "equipment_id",
        "equip_id": "equipment_id",
        "heure": "hours_operated",
        "hours": "hours_operated",
        "heures": "hours_operated",
        "km": "km_driven",
        "kilometres": "km_driven",
        "m3": "m3_moved",
        "volume_m3": "m3_moved",
        "revenus": "revenue",
        "fuel": "fuel_cost",
        "carburant": "fuel_cost",
        "main_oeuvre": "labor_cost",
        "labor": "labor_cost",
        "maintenance": "maintenance_cost",
        "overhead": "overhead_cost",
        "frais_fixes": "overhead_cost",
        "downtime": "downtime_hours",
    }

    cols = {}
    for c in df.columns:
        key = c.strip().lower()
        cols[c] = mapping.get(key, c)

    return df.rename(columns=cols)


def _issue(issue_type: str, column: str, message: str, count: int) -> dict:
    return {
        "issue_type": issue_type,
        "column": column,
        "message": message,
        "count": int(count),
    }


def ops_quality_report(df: pd.DataFrame) -> dict:
    issues = []
    missing = [c for c in OPS_REQUIRED if c not in df.columns]
    if missing:
        issues.append(_issue("missing_columns", "*", f"Missing required columns: {', '.join(missing)}", len(missing)))
        return {"issues": pd.DataFrame(issues), "summary": {"rows": len(df), "ok": False}}

    # date parse
    d = pd.to_datetime(df["date"], errors="coerce")
    bad_date = d.isna().sum()
    if bad_date:
        issues.append(_issue("invalid_date", "date", "Unparseable dates", bad_date))

    numeric_cols = [
        "hours_operated",
        "km_driven",
        "m3_moved",
        "revenue",
        "fuel_cost",
        "labor_cost",
        "maintenance_cost",
        "overhead_cost",
        "downtime_hours",
    ]
    for c in numeric_cols:
        x = pd.to_numeric(df[c], errors="coerce")
        n_bad = x.isna().sum()
        if n_bad:
            issues.append(_issue("non_numeric", c, "Non numeric values", n_bad))
        n_neg = (x < 0).sum()
        if n_neg:
            issues.append(_issue("negative", c, "Negative values", n_neg))

    # downtime > hours
    hours = pd.to_numeric(df["hours_operated"], errors="coerce")
    down = pd.to_numeric(df["downtime_hours"], errors="coerce")
    n = (down > hours).sum()
    if n:
        issues.append(_issue("inconsistent", "downtime_hours", "Downtime greater than operated hours", n))

    # duplicates
    dup = df.duplicated(subset=["date", "subsidiary", "activity", "contract", "equipment_id"], keep=False).sum()
    if dup:
        issues.append(_issue("duplicates", "*", "Potential duplicate run rows (date/sub/activity/contract/equipment)", dup))

    issues_df = pd.DataFrame(issues) if issues else pd.DataFrame(columns=["issue_type", "column", "message", "count"])
    ok = issues_df.empty
    return {"issues": issues_df, "summary": {"rows": len(df), "ok": ok}}


def capa_quality_report(df: pd.DataFrame) -> dict:
    issues = []
    missing = [c for c in CAPA_REQUIRED if c not in df.columns]
    if missing:
        issues.append(_issue("missing_columns", "*", f"Missing required columns: {', '.join(missing)}", len(missing)))
        return {"issues": pd.DataFrame(issues), "summary": {"rows": len(df), "ok": False}}

    for c in ["created_date", "due_date"]:
        d = pd.to_datetime(df[c], errors="coerce")
        bad = d.isna().sum()
        if bad:
            issues.append(_issue("invalid_date", c, "Unparseable dates", bad))

    dup = df.duplicated(subset=["capa_id"], keep=False).sum()
    if dup:
        issues.append(_issue("duplicates", "capa_id", "Duplicate CAPA IDs", dup))

    issues_df = pd.DataFrame(issues) if issues else pd.DataFrame(columns=["issue_type", "column", "message", "count"])
    ok = issues_df.empty
    return {"issues": issues_df, "summary": {"rows": len(df), "ok": ok}}


def mir_quality_report(df: pd.DataFrame) -> dict:
    issues = []
    missing = [c for c in MIR_REQUIRED if c not in df.columns]
    if missing:
        issues.append(_issue("missing_columns", "*", f"Missing required columns: {', '.join(missing)}", len(missing)))
        return {"issues": pd.DataFrame(issues), "summary": {"rows": len(df), "ok": False}}

    d = pd.to_datetime(df["event_date"], errors="coerce")
    bad = d.isna().sum()
    if bad:
        issues.append(_issue("invalid_date", "event_date", "Unparseable dates", bad))

    for c in ["labor_hours", "parts_cost", "downtime_hours"]:
        x = pd.to_numeric(df[c], errors="coerce")
        n_bad = x.isna().sum()
        if n_bad:
            issues.append(_issue("non_numeric", c, "Non numeric values", n_bad))
        n_neg = (x < 0).sum()
        if n_neg:
            issues.append(_issue("negative", c, "Negative values", n_neg))

    issues_df = pd.DataFrame(issues) if issues else pd.DataFrame(columns=["issue_type", "column", "message", "count"])
    ok = issues_df.empty
    return {"issues": issues_df, "summary": {"rows": len(df), "ok": ok}}
