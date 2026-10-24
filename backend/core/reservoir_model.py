"""M4 — reservoir storage forecast (owner: P3). Trained by train/train_reservoir.py; used through
core.reservoirs.forecast_storage().

What it learns (REAL labels): how much a dam's gross storage changes over the next 15-180 days, from NWDP daily
records of 9 Karnataka dams with long histories, given storage now, recent inflow/outflow, IMD rain over the dam's
catchment taluks (recent and during the forecast window) and the season.

Forecasting without knowing future rain: the window's catchment rain is replayed from each of the previous 8 years and
pooled with three quantile models (5/50/95 %) -> 10/50/90 % storage paths, like M2. For dates whose outcome is already
known and that fall after the validation cut (2022+), core.reservoirs uses the validation model that never saw them.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from .data import KA, climate, regions, reservoirs

MODELS = Path(__file__).resolve().parent.parent / "models"
MODEL_FILE = MODELS / "res_m4.joblib"
VALID_FILE = MODELS / "res_m4_validation.joblib"
CARD_FILE = MODELS / "res_m4_card.json"
HORIZONS = (15, 30, 60, 90, 120, 150, 180)       # days ahead
QUANTILES = (0.05, 0.5, 0.95)
SCENARIO_YEARS = 8
TRAIN_UNTIL = "2021-12-31"                        # validation models: targets up to this date
LOW_FRAC = 0.15                                   # "critically low" = below 15 % of design capacity
CUSEC_DAY_TMC = 86400 / 1e9                       # 1 cusec for a day = 86,400 ft3 = 8.64e-5 TMC

# Dams with long daily records, and the taluks whose IMD rain best represents their catchment.
CATCHMENT = {
    "K.R.Sagara Dam": ["Madikeri", "Somvarpet", "Virajpet", "Sakleshpur", "Mudigere"],
    "Kabini Dam": ["Heggadadevankote", "@wayanad_kabini"],         # @ = Bengaluru-model IMD point (Kerala)
    "Harangi Dam": ["Madikeri", "Somvarpet"],
    "Hemavathy Dam": ["Sakleshpur", "Mudigere", "Belur"],
    "Tungabhadra Dam": ["Tirthahalli", "Sringeri", "Koppa", "Narasimharajapura", "Mudigere", "Shivamogga"],
    "Bhadra Dam": ["Koppa", "Narasimharajapura", "Mudigere", "Chikkamagaluru", "Sringeri"],
    "Almatti Dam": ["Chikodi", "Athni", "Nippani", "Raybag"],    # most of the Krishna catchment is in Maharashtra
    "Hidkal Dam": ["Khanapur", "Belagavi", "Hukeri"],
    "Malaprabha Dam": ["Khanapur", "Belagavi"],
}
DAMS = list(CATCHMENT)
FEATURES = ["dam", "s_frac", "ds7", "ds30", "inflow7", "release7", "rain_dev_30", "rain_dev_90", "rain_dev_365",
            "rain_30_mm", "fut_dev", "fut_norm", "doy_sin", "doy_cos", "horizon"]


@lru_cache(maxsize=1)
def arrays():
    """Per dam: storage / inflow / release on the climate date axis, catchment rain + its day-of-year normal."""
    c = climate()
    d0 = dt.date.fromisoformat(c.dates[0])
    n = len(c.dates)
    idx = {r["name"]: r["idx"] for r in regions()}
    rf = json.loads((KA.parent / "rainfall.json").read_text())
    rf_start = dt.date.fromisoformat(rf["dates"][0])
    doy = np.array([(d0 + dt.timedelta(days=k)).timetuple().tm_yday - 1 for k in range(n)])
    yr = np.array([int(x[:4]) for x in c.dates])
    base = (yr >= 2014) & (yr <= 2022)
    out = {"c": c, "d0": d0, "n": n, "doy": doy, "dams": {}}
    res = {r["name"]: r for r in reservoirs()}
    for name, taluks in CATCHMENT.items():
        r = res[name]
        cols = []
        for t in taluks:
            if t.startswith("@"):
                series = np.full(n, np.nan)
                v = np.array(rf["catchment"][t[1:]], dtype=float)
                off = (rf_start - d0).days
                m = min(n - off, len(v))
                series[off:off + m] = v[:m]
                cols.append(series)
            else:
                cols.append(c.rain[:, idx[t]].astype(float))
        rain = np.nanmean(np.stack(cols, axis=1), axis=1)
        rain = np.where(np.isnan(rain), 0.0, rain)
        normal = np.array([rain[base & (doy == k)].mean() if (base & (doy == k)).any() else 0.0 for k in range(366)])
        cap = float(r["design_gross_tmc"])
        rs = dt.date.fromisoformat(r["start"])
        def align(v, scale=1.0):
            arr = np.full(n, np.nan)
            off = (rs - d0).days
            v = np.array([np.nan if x is None else x * scale for x in v], dtype=float)
            lo, hi = max(0, -off), min(len(v), n - off)
            if hi > lo:
                arr[off + lo: off + hi] = v[lo:hi]
            return arr
        rel = align(r["outflow_cusecs"], CUSEC_DAY_TMC / cap)
        canal = align(r["canal_cusecs"], CUSEC_DAY_TMC / cap)
        out["dams"][name] = {
            "cap": cap, "s": align(r["gross_tmc"]) / cap, "inflow": align(r["inflow_cusecs"], CUSEC_DAY_TMC / cap),
            "release": np.nan_to_num(rel) + np.nan_to_num(canal), "rain_cum": np.concatenate([[0], np.cumsum(rain)]),
            "norm_cum": np.concatenate([[0], np.cumsum(normal[doy])]),
            "cyc": np.concatenate([[0], np.cumsum(np.tile(normal[:365], 3))]),
        }
    return out


def _dev(D, lo, hi, n):
    lo, hi = max(lo, 0), min(hi, n - 1)
    if hi < lo:
        return 0.0, 0.0
    o = D["rain_cum"][hi + 1] - D["rain_cum"][lo]
    m = D["norm_cum"][hi + 1] - D["norm_cum"][lo]
    return ((o / m - 1) * 100 if m > 5 else 0.0), o


def features(name: str, t: int, h: int, fut_shift: int = 0) -> np.ndarray | None:
    """One feature row for dam `name` at climate index t forecasting h days ahead (None if storage is unknown).
    fut_shift > 0 replays the forecast-window catchment rain from that many days earlier (a past year)."""
    a = arrays()
    D, n = a["dams"][name], a["n"]
    s = D["s"]
    if t >= n or np.isnan(s[t]):
        return None
    past = lambda k: s[t - k] if t - k >= 0 and not np.isnan(s[t - k]) else np.nan
    win = slice(max(t - 6, 0), t + 1)
    fut_dev, _ = _dev(D, t + 1 - fut_shift, t + h - fut_shift, n)
    sd = a["doy"][t] if t < n else 0
    start = (sd + 1) % 365
    fut_norm = D["cyc"][start + h] - D["cyc"][start]
    row = {
        "dam": float(DAMS.index(name)), "s_frac": s[t], "ds7": s[t] - past(7), "ds30": s[t] - past(30),
        "inflow7": np.nanmean(D["inflow"][win]) if np.isfinite(D["inflow"][win]).any() else np.nan,
        "release7": float(np.mean(D["release"][win])),
        "rain_dev_30": _dev(D, t - 29, t, n)[0], "rain_dev_90": _dev(D, t - 89, t, n)[0],
        "rain_dev_365": _dev(D, t - 364, t, n)[0], "rain_30_mm": _dev(D, t - 29, t, n)[1],
        "fut_dev": fut_dev, "fut_norm": fut_norm,
        "doy_sin": np.sin(2 * np.pi * sd / 365), "doy_cos": np.cos(2 * np.pi * sd / 365), "horizon": float(h),
    }
    return np.array([row[f] for f in FEATURES], dtype=np.float64)


@lru_cache(maxsize=2)
def load(validation: bool = False):
    f = VALID_FILE if validation else MODEL_FILE
    if not f.exists():
        return None
    import joblib
    return joblib.load(f)


def card() -> dict | None:
    return json.loads(CARD_FILE.read_text()) if CARD_FILE.exists() else None


def forecast(models, name: str, t: int) -> dict | None:
    """10/50/90 % storage-fraction paths for HORIZONS from climate index t, + P(below LOW_FRAC) per horizon."""
    a = arrays()
    rows, meta = [], []
    scen = [s for s in range(1, SCENARIO_YEARS + 1) if t + 1 - 365 * s >= 0]
    if not scen:
        return None
    for h in HORIZONS:
        for s in scen:
            x = features(name, t, h, fut_shift=365 * s)
            if x is None:
                return None
            rows.append(x)
            meta.append(h)
    X = np.vstack(rows)
    draws = np.stack([models[q].predict(X) for q in QUANTILES])            # (q, rows)
    s0 = a["dams"][name]["s"][t]
    meta = np.array(meta)
    out = {"p10": [], "p50": [], "p90": [], "p_low": [], "draws": []}
    for h in HORIZONS:
        v = np.clip(s0 + draws[:, meta == h].ravel(), 0, 1.02)    # (quantile x past-year) draws, fixed order
        out["p10"].append(float(np.percentile(v, 10)))
        out["p50"].append(float(np.percentile(v, 50)))
        out["p90"].append(float(np.percentile(v, 90)))
        out["p_low"].append(float(np.mean(v < LOW_FRAC)))
        out["draws"].append(v)
    out["s0"] = float(s0)
    out["scenarios"] = scen
    return out
