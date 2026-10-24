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


def forecast_storage(names, as_of: str, horizon_days: int = 180) -> dict | None:
    """M4 contract (owner: P3). Summed storage forecast for `names` from `as_of`, using only data up to as_of.

    Returns None until M4 exists, then:
      {"model": str, "dates": [iso...], "p25": [...], "p50": [...], "p75": [...]   # TMC, every 7 days
       "dead_storage_tmc": float, "p_below_dead_by": {iso_date: prob}, "months_of_supply": float | None}
    Urban (Cauvery outlook) and Industry (surface-water dependence) call this; keep the keys stable.
    """
    return None


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
