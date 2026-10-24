"""M5 — urban water demand, supply gap and tanker need (owner: P3). ESTIMATED, physically based (no public metered
demand exists to train on, and we don't fabricate training data).

Bengaluru, per ward (from the ward model, backend/model.py):
  demand   = population x 135 L/person/day (CPHEEO norm) + commercial / IT load      [estimated]
  piped    = demand x Cauvery pipe coverage x Cauvery supply reliability            [estimated coverage, real-rain reliability]
  borewell = demand - piped
  tankers  = the borewell share of wards whose groundwater is at / near shortage (days to shortage <= 30), because
             their borewells fail;  trips = MLD / 6,000-litre tanker
  next 6 months: demand x (1 + ward growth) x seasonal heat factor (+2 % per degC of normal Tmax above the annual mean,
             ERA5 temperature for Bengaluru's taluks)                                [assumed elasticity]
Other cities: population x 135 L/day x the same heat factor vs the (estimated) supply.
"""
from __future__ import annotations

import datetime as dt
from functools import lru_cache

import numpy as np

import model
from core.data import climate, regions

LPCD = 135
TANKER_L = 6000
HEAT_PER_DEGC = 0.02
BLR_TALUKS = ("Bengaluru South", "Bengaluru North", "Bengaluru East", "Yelahanka", "Anekal")


@lru_cache(maxsize=1)
def tmax_month_normal() -> np.ndarray:
    """Normal daily Tmax per calendar month (index 1..12) over Bengaluru's taluks, 2014-2022."""
    c = climate()
    idx = [r["idx"] for r in regions() if r["name"] in BLR_TALUKS]
    months = np.array([int(d[5:7]) for d in c.dates])
    years = np.array([int(d[:4]) for d in c.dates])
    base = (years >= 2014) & (years <= 2022)
    t = c.tmax[:, idx].mean(axis=1)
    out = np.zeros(13)
    for m in range(1, 13):
        out[m] = float(t[base & (months == m)].mean())
    out[0] = float(out[1:].mean())
    return out


def heat_factor(month: int) -> float:
    n = tmax_month_normal()
    return 1 + HEAT_PER_DEGC * (n[month] - n[0])


@lru_cache(maxsize=32)
def bengaluru(as_of: str) -> dict:
    r = model.predict(as_of, model.Intervention(), False)
    w = model.load_world()
    wards = []
    for x in r["wards"]:
        i = x["inputs"]
        demand = i["demand_mld"]
        piped = demand * i["cauvery_coverage_pct"] / 100 * i["cauvery_supply_pct"] / 100
        bore = max(demand - piped, 0.0)
        tanker = bore if x["days_mid"] <= 30 else 0.0
        wards.append({"idx": x["idx"], "name": x["name"], "ward_no": x["ward_no"], "risk": x["risk"],
                      "days_mid": x["days_mid"], "demand_mld": round(demand, 2), "piped_mld": round(piped, 2),
                      "borewell_mld": round(bore, 2), "tanker_mld": round(tanker, 2),
                      "tanker_trips_per_day": int(round(tanker * 1e6 / TANKER_L))})
    day = dt.date.fromisoformat(r["as_of"])
    growth = float(np.average(w.growth, weights=[x["demand_mld"] for x in wards]))
    base_demand = sum(x["demand_mld"] for x in wards)
    base_piped = sum(x["piped_mld"] for x in wards)
    f0 = heat_factor(day.month)
    months = []
    for k in range(1, 7):
        m = (day.month - 1 + k) % 12 + 1
        y = day.year + (day.month - 1 + k) // 12
        dmd = base_demand * (1 + growth * k / 12) * heat_factor(m) / f0
        months.append({"month": f"{y}-{m:02d}", "demand_mld": round(dmd), "piped_mld": round(base_piped),
                       "gap_mld": round(max(dmd - base_piped, 0))})
    tank = [x for x in wards if x["tanker_mld"] > 0]
    tank.sort(key=lambda x: -x["tanker_mld"])
    return {"as_of": r["as_of"], "demand_mld": round(base_demand), "piped_mld": round(base_piped),
            "borewell_mld": round(sum(x["borewell_mld"] for x in wards)),
            "tanker_mld": round(sum(x["tanker_mld"] for x in wards), 1),
            "tanker_trips_per_day": sum(x["tanker_trips_per_day"] for x in wards),
            "wards_needing_tankers": len(tank), "top_tanker_wards": tank[:15], "next_6_months": months,
            "wards": wards}


def city(pop_lakh: float, supply_mld: float, as_of: str) -> dict:
    """Other cities: estimated demand (population x 135 L/day, seasonal heat) vs the estimated supply."""
    day = dt.date.fromisoformat(as_of)
    base = pop_lakh * 1e5 * LPCD / 1e6
    f0 = heat_factor(day.month)
    months = []
    for k in range(1, 7):
        m = (day.month - 1 + k) % 12 + 1
        y = day.year + (day.month - 1 + k) // 12
        dmd = base * heat_factor(m) / f0
        months.append({"month": f"{y}-{m:02d}", "demand_mld": round(dmd), "gap_mld": round(max(dmd - supply_mld, 0))})
    return {"demand_mld": round(base), "supply_mld": supply_mld, "gap_mld": round(max(base - supply_mld, 0)),
            "next_6_months": months}
