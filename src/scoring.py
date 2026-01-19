from __future__ import annotations

import numpy as np
import pandas as pd


def clamp(x, lo=0.0, hi=100.0):
    return float(max(lo, min(hi, x)))


def risk_score_row(r) -> tuple[float, list[str]]:
    reasons = []

    score = 0.0

    # Negative profit
    if r.profit < 0:
        score += 35
        reasons.append("negative_profit")

    # High variance on cost_per_km or cost_per_hour
    if pd.notna(r.var_cpkm_pct) and r.var_cpkm_pct > 0.12:
        score += 20
        reasons.append("high_cost_per_km_variance")
    if pd.notna(r.var_cph_pct) and r.var_cph_pct > 0.12:
        score += 20
        reasons.append("high_cost_per_hour_variance")

    # High downtime
    if pd.notna(r.downtime_hours) and pd.notna(r.hours_operated) and r.hours_operated > 0:
        if (r.downtime_hours / r.hours_operated) > 0.15:
            score += 15
            reasons.append("high_downtime")

    # Fuel share high
    if pd.notna(r.fuel_share) and r.fuel_share > 0.42:
        score += 10
        reasons.append("high_fuel_share")

    # Safety signal
    if getattr(r, "incident_count", 0) > 0:
        score += 10
        reasons.append("incident")
    if getattr(r, "near_miss_count", 0) > 0:
        score += 5
        reasons.append("near_miss")

    return clamp(score), reasons


def add_risk_scoring(df_var: pd.DataFrame) -> pd.DataFrame:
    df = df_var.copy()
    scores = []
    reason_codes = []
    for r in df.itertuples():
        s, reasons = risk_score_row(r)
        scores.append(s)
        reason_codes.append(",".join(reasons) if reasons else "")

    df["risk_score"] = scores
    df["reason_codes"] = reason_codes

    def level(s):
        if s >= 75:
            return "Critical"
        if s >= 55:
            return "High"
        if s >= 30:
            return "Medium"
        return "Low"

    df["risk_level"] = df["risk_score"].apply(level)
    return df


def build_recommendations(df_scored: pd.DataFrame, top_n: int = 8) -> pd.DataFrame:
    """Create a short, action-oriented recommendation list (demo)."""
    df = df_scored.sort_values(["risk_score", "profit"], ascending=[False, True]).head(top_n).copy()

    actions = []
    for r in df.itertuples():
        rec = []
        if "high_fuel_share" in r.reason_codes:
            rec.append("Revoir planification des trajets + politique carburant")
        if "high_downtime" in r.reason_codes:
            rec.append("Prioriser maintenance préventive (MIR) sur cet équipement")
        if "high_cost_per_km_variance" in r.reason_codes:
            rec.append("Analyser km à vide / charge utile / optimisation tournées")
        if "high_cost_per_hour_variance" in r.reason_codes:
            rec.append("Analyser taux d'opération et main-d'œuvre par quart")
        if "negative_profit" in r.reason_codes:
            rec.append("Analyse rentabilité contrat: ajuster taux ou réduire coûts")
        if "incident" in r.reason_codes or "near_miss" in r.reason_codes:
            rec.append("Vérifier facteurs SST associés (formation / procédure)")

        actions.append("; ".join(rec) if rec else "Revue opérationnelle ciblée")

    df["recommended_actions"] = actions

    keep = [
        "date",
        "subsidiary",
        "activity",
        "contract",
        "team",
        "equipment_id",
        "risk_level",
        "risk_score",
        "profit",
        "cost_per_km",
        "cost_per_hour",
        "downtime_hours",
        "recommended_actions",
    ]
    return df[keep]
