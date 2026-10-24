"""Reservoir storage helpers (data: reservoirs.json from NWDP). Not a platform of its own: reservoirs are an
input to Urban (Cauvery supply to Bengaluru), Agriculture (canal irrigation) and Industry (surface-water supply)."""
import datetime as dt
import re
from functools import lru_cache

import numpy as np

from .data import reservoirs

# Dams whose storage drives Bengaluru's Cauvery piped supply.
CAUVERY_BENGALURU = ("K.R.Sagara Dam", "Kabini Dam", "Harangi Dam", "Hemavathy Dam")


def slug(name):
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def value(r, day: dt.date):
    k = (day - dt.date.fromisoformat(r["start"])).days
    return r["gross_tmc"][k] if 0 <= k < r["days"] else None


def normal(r, day: dt.date, years=8):
    """Median storage on the same calendar day over up to `years` earlier years (only data before `day`)."""
    vals = []
    for y in range(1, years + 1):
        try:
            v = value(r, day.replace(year=day.year - y))
        except ValueError:          # 29 Feb
            v = value(r, day.replace(year=day.year - y, day=28))
        if v is not None:
            vals.append(v)
    return round(float(np.median(vals)), 2) if len(vals) >= 3 else None


@lru_cache(maxsize=64)
def storage_on(as_of: str) -> list[dict]:
    day = dt.date.fromisoformat(as_of)
    out = []
    for r in reservoirs():
        v = value(r, day)
        n = normal(r, day)
        out.append({"slug": slug(r["name"]), "name": r["name"], "basin": r["basin"], "river": r["river"],
                    "state": r["state"], "design_gross_tmc": r["design_gross_tmc"], "storage_tmc": v,
                    "pct_full": round(100 * v / r["design_gross_tmc"], 1) if v is not None else None,
                    "normal_tmc": n, "vs_normal_pct": round(100 * (v / n - 1), 1) if v is not None and n else None,
                    "data_from": r["start"], "data_until": r["end"]})
    return out


@lru_cache(maxsize=256)
def _forecast_one(name: str, as_of: str):
    from . import reservoir_model as rm
    if name not in rm.DAMS:
        return None, None
    a = rm.arrays()
    t = (dt.date.fromisoformat(as_of) - a["d0"]).days
    # Replays of dates whose outcome is known (2022+) use the validation model that never saw them.
    validation = as_of > rm.TRAIN_UNTIL and t + 30 < a["n"]
    models = rm.load(validation=validation) or rm.load()
    if models is None:
        return None, None
    return rm.forecast(models, name, t), ("validation (trained to 2021)" if validation and rm.load(True) else "production")


def forecast_storage(names, as_of: str, horizon_days: int = 180) -> dict | None:
    """M4 contract (owner: P3). Summed storage forecast for `names` from `as_of`, using only data up to as_of.

    Returns None when M4 isn't available for any of the dams, else:
      {"model", "mode", "dams": [...used...], "capacity_tmc", "storage_now_tmc",
       "points": [{"days", "date", "p10", "p50", "p90" (TMC), "p_low"}],          # horizons 15..180 days
       "low_threshold_tmc", "days_to_low": {"p10", "p50", "p90"} (None = not within the horizon),
       "months_of_supply": float | None}                                          # middle path to the low threshold
    Dams are combined draw by draw (same past-year rain scenario and quantile), not by adding percentiles.
    Urban (Cauvery outlook) and Industry (surface-water dependence) call this; keep the keys stable.
    """
    from . import reservoir_model as rm
    res = {r["name"]: r for r in reservoirs()}
    used, total, now, cap, mode = [], None, 0.0, 0.0, None
    for n in names:
        f, m = _forecast_one(n, as_of)
        if f is None:
            continue
        c = float(res[n]["design_gross_tmc"])
        d = np.array(f["draws"]) * c                              # (horizons, draws) in TMC
        total = d if total is None else total + d     # same past-year scenarios for every dam on a given date
        now += f["s0"] * c
        cap += c
        used.append(n)
        mode = m
    if total is None:
        return None
    low = rm.LOW_FRAC * cap
    day0 = dt.date.fromisoformat(as_of)
    points = []
    for j, h in enumerate(rm.HORIZONS):
        if h > horizon_days:
            break
        v = total[j]
        points.append({"days": h, "date": (day0 + dt.timedelta(days=h)).isoformat(),
                       "p10": round(float(np.percentile(v, 10)), 2), "p50": round(float(np.percentile(v, 50)), 2),
                       "p90": round(float(np.percentile(v, 90)), 2), "p_low": round(float(np.mean(v < low)), 2)})

    def first_below(key):
        for p in points:
            if p[key] < low:
                return p["days"]
        return None
    d50 = first_below("p50")
    return {"model": (rm.card() or {}).get("version", "m4"), "mode": mode, "dams": used, "capacity_tmc": round(cap, 2),
            "storage_now_tmc": round(now, 2), "points": points, "low_threshold_tmc": round(low, 2),
            "days_to_low": {"p10": first_below("p10"), "p50": d50, "p90": first_below("p90")},
            "months_of_supply": round(d50 / 30.44, 1) if d50 is not None else None}


def combined_series(names, as_of: str, days=730, step=3):
    """Summed storage (and summed normal) of several dams for the `days` before as_of."""
    rs = [r for r in reservoirs() if r["name"] in names]
    day = dt.date.fromisoformat(as_of)
    out = []
    for k in range(days, -1, -step):
        d = day - dt.timedelta(days=k)
        vals = [value(r, d) for r in rs]
        norms = [normal(r, d) for r in rs]
        if None in vals:
            continue
        out.append({"date": d.isoformat(), "storage_tmc": round(sum(vals), 2),
                    "normal_tmc": round(sum(norms), 2) if None not in norms else None})
    return out, round(sum(r["design_gross_tmc"] for r in rs), 2)


def reservoirs_end() -> str:
    """Last date with reservoir data (latest 'end' over the Cauvery dams)."""
    return min(r["end"] for r in reservoirs() if r["name"] in CAUVERY_BENGALURU)
