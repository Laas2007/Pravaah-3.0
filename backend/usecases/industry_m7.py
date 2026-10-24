"""M7 — industrial water-disruption risk per district (owner: P4).

Transparent score, no trained weights (there are no public labels of industrial water disruption to learn from):
  demand        = KIADB developed area (REAL, data/raw/kiadb) x planning norm (ESTIMATED: 20 kL per hectare per day)
  groundwater   = M2 forecast for the district's taluks: share of the next 6 months spent at stress (middle path)
                  and the share of taluks on the watch list (pessimistic path)
  surface water = M4 forecast for the reservoir system that serves the district: probability that storage falls
                  below 15 % of capacity within 6 months
  dependence    = 60 % surface / 40 % groundwater where a modelled reservoir system serves the district, else
                  15 % / 85 % (ESTIMATED)
  disruption    = dependence-weighted share of the next 6 months with a water shortfall  ->  % output at risk,
                  water at risk (MLD), and reuse potential (80 % of use becomes wastewater, 70 % of it recyclable).
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache
from pathlib import Path

import numpy as np

from core.data import regions
from core.reservoirs import forecast_storage
from core.risk import taluk_risk

KIADB = Path(__file__).resolve().parent.parent / "data" / "raw" / "kiadb" / "kiadb_district_wise_industrial_land_bank.csv"
NORM_KL_PER_HA_DAY = 20.0
ACRE_HA = 0.404686
HORIZON = 183
NAME_ALIAS = {"Bagalkot": "Bagalkote", "Chamarajanagar": "Chamarajanagara"}
SYSTEMS = {
    "Cauvery (KRS, Kabini, Harangi, Hemavathy)": (("K.R.Sagara Dam", "Kabini Dam", "Harangi Dam", "Hemavathy Dam"),
        ("Bengaluru Urban", "Bengaluru Rural", "Ramanagara", "Mandya", "Mysuru", "Chamarajanagara", "Hassan", "Tumakuru")),
    "Tungabhadra": (("Tungabhadra Dam",), ("Ballari", "Vijayanagara", "Koppal", "Raichur")),
    "Bhadra": (("Bhadra Dam",), ("Shivamogga", "Davanagere", "Chitradurga", "Chikkamagaluru")),
    "Almatti (Krishna)": (("Almatti Dam",), ("Vijayapura", "Bagalkote", "Yadgir")),
    "Hidkal + Malaprabha": (("Hidkal Dam", "Malaprabha Dam"), ("Belagavi", "Dharwad", "Gadag")),
}


@lru_cache(maxsize=1)
def kiadb() -> dict[str, dict]:
    import csv
    out = {}
    with open(KIADB, encoding="utf-8") as f:
        for r in csv.DictReader(f):
            name = r["district"].strip()
            if name.upper().startswith("TOTAL"):
                continue
            out[NAME_ALIAS.get(name, name)] = {"areas": int(r["kiadb_industrial_area_count"]),
                                               "acres": float(r["developed_area_acres"])}
    return out


def system_of(district: str):
    for name, (dams, districts) in SYSTEMS.items():
        if district in districts:
            return name, dams
    return None, ()


@lru_cache(maxsize=32)
def districts(as_of: str) -> list[dict]:
    rk = taluk_risk(as_of)
    regs = regions()
    by_d = {}
    for r in regs:
        by_d.setdefault(r["district"], []).append(r["idx"])
    sys_fc = {name: forecast_storage(dams, as_of) for name, (dams, _) in SYSTEMS.items()}
    rows = []
    for d, info in kiadb().items():
        idx = by_d.get(d, [])
        mid = np.array([rk["days_mid"][i] for i in idx]) if rk["days_mid"] is not None else np.array([])
        lo = np.array([rk["days_low"][i] for i in idx]) if rk["days_low"] is not None else np.array([])
        mid, lo = mid[np.isfinite(mid)] if mid.size else mid, lo[np.isfinite(lo)] if lo.size else lo
        gw_share = float(np.mean(np.clip((HORIZON - np.minimum(mid, HORIZON)) / HORIZON, 0, 1))) if mid.size else 0.0
        gw_watch = float(np.mean(lo <= HORIZON)) if lo.size else 0.0
        sname, _ = system_of(d)
        fc = sys_fc.get(sname) if sname else None
        p_low = max((p["p_low"] for p in fc["points"]), default=0.0) if fc else 0.0
        surf_dep = 0.6 if fc else 0.15
        disruption = (1 - surf_dep) * gw_share + surf_dep * p_low
        demand = info["acres"] * ACRE_HA * NORM_KL_PER_HA_DAY / 1000          # MLD
        rows.append({
            "district": d, "kiadb_areas": info["areas"], "developed_acres": info["acres"],
            "demand_mld": round(demand, 1),
            "groundwater_stress_share": round(gw_share, 2), "groundwater_watch_share": round(gw_watch, 2),
            "reservoir_system": sname, "reservoir_p_low_6m": round(p_low, 2),
            "reservoir_months_of_supply": fc["months_of_supply"] if fc else None,
            "surface_dependence": surf_dep,
            "output_at_risk_pct": round(100 * disruption, 1),
            "water_at_risk_mld": round(demand * disruption, 1),
            "reuse_potential_mld": round(demand * 0.8 * 0.7, 1),
            "risk": "critical" if disruption >= 0.5 else "high" if disruption >= 0.25 else "medium" if disruption >= 0.1 else "low",
            "taluk_idx": idx,
        })
    rows.sort(key=lambda r: -r["output_at_risk_pct"])
    return rows
