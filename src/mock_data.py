from __future__ import annotations

import datetime as dt
from dataclasses import dataclass
from typing import List, Tuple

import numpy as np
import pandas as pd


ACTIVITIES = [
    "transport_inter_usines",
    "transport_copeaux",
    "construction_chemins",
    "chargement",
]


def _rng(seed: int) -> np.random.Generator:
    return np.random.default_rng(seed)


def generate_ops_runs(
    seed: int = 42,
    n_days: int = 90,
    n_equipment: int = 12,
    n_contracts: int = 6,
    subsidiaries: Tuple[str, ...] = ("Bécar inc.",),
) -> pd.DataFrame:
    rng = _rng(seed)

    start = dt.date.today() - dt.timedelta(days=n_days)
    dates = [start + dt.timedelta(days=i) for i in range(n_days)]

    equipment_ids = [f"EQ-{i:03d}" for i in range(1, n_equipment + 1)]
    contracts = [f"CTR-{i:03d}" for i in range(1, n_contracts + 1)]
    teams = ["Équipe A", "Équipe B", "Équipe C"]

    rows = []
    for d in dates:
        # variable activity mix by day
        for _ in range(rng.integers(6, 16)):
            sub = rng.choice(subsidiaries)
            act = rng.choice(ACTIVITIES, p=[0.42, 0.28, 0.18, 0.12])
            ctr = rng.choice(contracts)
            eq = rng.choice(equipment_ids)
            team = rng.choice(teams)

            hours = float(np.round(rng.normal(8.0, 1.8), 2))
            hours = max(0.5, hours)

            # km and volume depend on activity
            if act in ("transport_inter_usines", "transport_copeaux"):
                km = float(np.round(max(5.0, rng.normal(180, 60)), 1))
                m3 = float(np.round(max(2.0, rng.normal(85, 25)), 1))
            elif act == "construction_chemins":
                km = float(np.round(max(0.0, rng.normal(12, 6)), 1))
                m3 = float(np.round(max(0.0, rng.normal(25, 10)), 1))
            else:  # chargement
                km = float(np.round(max(0.0, rng.normal(6, 4)), 1))
                m3 = float(np.round(max(5.0, rng.normal(120, 35)), 1))

            # cost components
            fuel = float(np.round(max(0.0, rng.normal(210, 70)) * (km / 180 if km else 0.6), 2))
            labor = float(np.round(max(0.0, rng.normal(52, 8)) * hours, 2))
            maint = float(np.round(max(0.0, rng.normal(65, 25)) * (hours / 8), 2))
            overhead = float(np.round(max(0.0, rng.normal(45, 12)) * (hours / 8), 2))

            downtime = float(np.round(max(0.0, rng.normal(0.6, 0.8)), 2))
            downtime = min(downtime, hours * 0.6)

            # revenue model
            # (only to support profitability demo)
            if act in ("transport_inter_usines", "transport_copeaux"):
                revenue = float(np.round( (2.2 * km) + (4.0 * m3) + (18 * hours), 2))
            elif act == "construction_chemins":
                revenue = float(np.round( (55 * hours) + (1.2 * m3), 2))
            else:
                revenue = float(np.round( (28 * hours) + (2.8 * m3), 2))

            # safety signals (optional)
            incident = int(rng.random() < 0.015)
            near_miss = int(rng.random() < 0.045)

            rows.append({
                "date": d.isoformat(),
                "subsidiary": sub,
                "activity": act,
                "contract": ctr,
                "team": team,
                "equipment_id": eq,
                "hours_operated": hours,
                "km_driven": km,
                "m3_moved": m3,
                "revenue": revenue,
                "fuel_cost": fuel,
                "labor_cost": labor,
                "maintenance_cost": maint,
                "overhead_cost": overhead,
                "downtime_hours": downtime,
                "incident_count": incident,
                "near_miss_count": near_miss,
            })

    df = pd.DataFrame(rows)
    return df


def generate_targets(ops_df: pd.DataFrame) -> pd.DataFrame:
    """Generate simple targets from historical medians (demo only)."""
    df = ops_df.copy()
    df["total_cost"] = df[["fuel_cost", "labor_cost", "maintenance_cost", "overhead_cost"]].sum(axis=1)

    def safe_div(a, b):
        return np.where(b > 0, a / b, np.nan)

    df["cph"] = safe_div(df["total_cost"], df["hours_operated"])
    df["cpkm"] = safe_div(df["total_cost"], df["km_driven"])
    df["cpm3"] = safe_div(df["total_cost"], df["m3_moved"])

    grp = df.groupby(["subsidiary", "activity"], as_index=False)
    targets = grp[["cph", "cpkm", "cpm3"]].median(numeric_only=True)

    # make targets slightly tighter
    for c in ["cph", "cpkm", "cpm3"]:
        targets[c] = targets[c] * 0.95

    targets = targets.rename(columns={
        "cph": "target_cph",
        "cpkm": "target_cpkm",
        "cpm3": "target_cpm3",
    })
    return targets


def generate_mir_events(seed: int, equipment_ids: List[str], n_events: int = 220) -> pd.DataFrame:
    rng = _rng(seed + 7)
    start = dt.date.today() - dt.timedelta(days=180)

    event_types = ["preventive", "corrective"]
    failure_modes = ["hydraulique", "freins", "pneus", "moteur", "électrique", "structure"]

    rows = []
    for i in range(n_events):
        eq = rng.choice(equipment_ids)
        day = start + dt.timedelta(days=int(rng.integers(0, 180)))
        et = rng.choice(event_types, p=[0.55, 0.45])
        labor_h = float(np.round(max(0.5, rng.normal(3.2, 1.6)), 2))
        parts = float(np.round(max(0.0, rng.normal(220, 160)), 2))
        downtime = float(np.round(max(0.0, rng.normal(1.4 if et == "corrective" else 0.8, 0.9)), 2))
        fm = rng.choice(failure_modes) if et == "corrective" else "inspection"
        rows.append({
            "equipment_id": eq,
            "event_date": day.isoformat(),
            "event_type": et,
            "work_order_id": f"WO-{i:05d}",
            "labor_hours": labor_h,
            "parts_cost": parts,
            "downtime_hours": downtime,
            "failure_mode": fm,
        })

    return pd.DataFrame(rows)


def generate_capa(seed: int, ops_df: pd.DataFrame, n_actions: int = 12) -> pd.DataFrame:
    rng = _rng(seed + 11)
    owners = ["Opérations", "Maintenance", "Approvisionnement", "Finances"]
    statuses = ["Open", "In progress", "Done", "Verified"]
    priorities = ["Low", "Medium", "High", "Critical"]

    sample = ops_df.sample(n=min(n_actions, len(ops_df)), random_state=seed)
    rows = []
    for i, r in enumerate(sample.itertuples(index=False), start=1):
        created = dt.date.fromisoformat(r.date)
        due = created + dt.timedelta(days=int(rng.integers(7, 30)))
        pr = rng.choice(priorities, p=[0.2, 0.45, 0.25, 0.1])
        st = rng.choice(statuses, p=[0.55, 0.25, 0.15, 0.05])
        rows.append({
            "capa_id": f"CAPA-{i:04d}",
            "created_date": created.isoformat(),
            "issue_type": "cost_variance",
            "priority": pr,
            "subsidiary": r.subsidiary,
            "activity": r.activity,
            "contract": r.contract,
            "equipment_id": r.equipment_id,
            "owner": rng.choice(owners),
            "due_date": due.isoformat(),
            "status": st,
            "root_cause": "",
            "action_plan": "",
            "expected_impact": "",
        })

    return pd.DataFrame(rows)


def generate_all(seed: int = 42, n_days: int = 90, n_equipment: int = 12, n_contracts: int = 6):
    ops = generate_ops_runs(seed=seed, n_days=n_days, n_equipment=n_equipment, n_contracts=n_contracts)
    targets = generate_targets(ops)
    equipment_ids = sorted(ops["equipment_id"].unique().tolist())
    mir = generate_mir_events(seed=seed, equipment_ids=equipment_ids)
    capa = generate_capa(seed=seed, ops_df=ops)
    return ops, targets, capa, mir
