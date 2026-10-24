"""M2 — groundwater forecast (owner: P1). Trained by train/train_gw.py, served through core.risk.taluk_risk.

What it learns (REAL labels): how much each monitored well's depth to water changes over the next 1-6 months, from
2,698 NWDP wells (gw_well_monthly.npz), given the well's current state, recent rain/heat in its taluk and the rain
that falls during the forecast window.

How it forecasts without knowing future rain: the window's rain is replayed from every earlier year on record (the
same "past years as futures" trick as the Bengaluru model). Predictions from all those futures and three quantile
models (5/50/95 %) are pooled; the 10/50/90th percentiles of that pool give a pessimistic / middle / optimistic path.
Taluk value = median over its wells.

"Stress" = the taluk's median well anomaly (depth vs the well's own 2014-2021 normal for that month) reaches the
taluk's worst-10 % level of 2014-2021 (at least 1 m deeper than normal). Risk is a two-tier early warning (`level`):
critical = at stress now or likely (middle path) within 90 days, high = likely within 6 months, medium ("watch") =
possible on the pessimistic path within 6 months, low = otherwise.

Validated on years it never saw (models/gw_m2_card.json): ~7 % lower error than "no change", 10-90 % range covers
86 % of outcomes; for the 2023 drought the watch tier caught 18/20 stress taluks (with many false alarms) and the
warning tier 4/20 (33 % precision). It ranks taluks well but under-predicts extremes.
"""
from __future__ import annotations

import datetime as dt
import warnings
import json
from functools import lru_cache
from pathlib import Path

import numpy as np

from .data import KA, climate, regions

MODELS = Path(__file__).resolve().parent.parent / "models"
MODEL_FILE = MODELS / "gw_m2.joblib"
CARD_FILE = MODELS / "gw_m2_card.json"
HORIZONS = (1, 2, 3, 4, 5, 6)          # months ahead (validated skill fades beyond ~6 months)
QUANTILES = (0.05, 0.5, 0.95)
SCENARIO_YEARS = 8                     # earlier years replayed as possible futures
NORMAL_YEARS = (2014, 2021)            # well normals + stress thresholds (pre-test period)
FILL_MONTHS = 2                        # a well's reading may be up to 2 months older than the origin month

FEATURES = ["depth_now", "d3", "d12", "anom_now", "seas", "rain_dev_30", "rain_dev_90", "rain_dev_365",
            "et0_dev_90", "fut_dev", "fut_norm", "horizon", "target_month"]
DRIVER_LABELS = {
    "rain_deficit": "Less rain than normal in recent months",
    "groundwater_already_low": "Groundwater already deeper than normal",
    "heat": "Hotter / drier air than normal (high evaporation)",
}


# ---------------------------------------------------------------- shared arrays

@lru_cache(maxsize=1)
def arrays():
    c = climate()
    T = len(regions())
    d0 = dt.date.fromisoformat(c.dates[0])
    doy = np.array([(d0 + dt.timedelta(days=k)).timetuple().tm_yday - 1 for k in range(len(c.dates))])
    yr_d = np.array([int(d[:4]) for d in c.dates])
    base = (yr_d >= 2014) & (yr_d <= 2022)
    et0_doy = np.stack([c.et0[base & (doy == k)].mean(0) if (base & (doy == k)).any() else c.et0[base].mean(0)
                        for k in range(366)])
    zero = np.zeros((1, T))
    cum = lambda x: np.concatenate([zero, np.cumsum(x, axis=0)])

    z = np.load(KA / "gw_well_monthly.npz")
    months = [str(m) for m in z["months"]]
    W = z["depth"].astype(np.float64)
    wt = z["taluk"].astype(int)
    cal = np.array([int(m[5:7]) for m in months])
    yr = np.array([int(m[:4]) for m in months])
    norm_sel = (yr >= NORMAL_YEARS[0]) & (yr <= NORMAL_YEARS[1])
    normal = np.full((W.shape[0], 13), np.nan)
    for mo in range(1, 13):
        sel = norm_sel & (cal == mo)
        cnt = np.sum(~np.isnan(W[:, sel]), axis=1)
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            normal[:, mo] = np.where(cnt >= 3, np.nanmedian(W[:, sel], axis=1), np.nan)

    # stress threshold per taluk: p90 of the taluk's monthly median well anomaly in the normal period
    A = W - normal[:, cal]
    thr = np.full(T, np.nan)
    for t in range(T):
        m = np.where(wt == t)[0]
        if len(m) == 0:
            continue
        with np.errstate(all="ignore"), warnings.catch_warnings():
            warnings.simplefilter("ignore", RuntimeWarning)
            med = np.nanmedian(A[m][:, norm_sel], axis=0)
        med = med[np.isfinite(med)]
        if len(med) >= 24:
            thr[t] = max(float(np.percentile(med, 90)), 1.0)
    thr = np.where(np.isnan(thr), np.nanmedian(thr), thr)

    # cyclic day-of-year normal, so windows that run past the end of the record still get a normal
    cyc = np.concatenate([zero, np.cumsum(np.vstack([c.rain_doy_normal[:365]] * 3), axis=0)])
    return dict(c=c, T=T, d0=d0, rain_cum=cum(c.rain), norm_cum=cum(c.rain_doy_normal[doy]), et0_cum=cum(c.et0),
                et0n_cum=cum(et0_doy[doy]), cyc=cyc, months=months, mi={m: k for k, m in enumerate(months)},
                W=W, wt=wt, cal=cal, normal=normal, anom=A, thr=thr, nC=len(c.dates))


def month_end(m: str) -> dt.date:
    y, mo = int(m[:4]), int(m[5:7])
    return dt.date(y + (mo == 12), mo % 12 + 1, 1) - dt.timedelta(days=1)


def dev(a, lo, hi, obs="rain_cum", nrm="norm_cum"):
    """% vs normal per taluk over climate indices [lo, hi] inclusive (clipped to the record), and the normal mm."""
    lo, hi = max(lo, 0), min(hi, a["nC"] - 1)
    if hi < lo:
        return np.zeros(a["T"]), np.zeros(a["T"])
    o = a[obs][hi + 1] - a[obs][lo]
    n = a[nrm][hi + 1] - a[nrm][lo]
    return np.where(n > 5, (o / np.maximum(n, 1e-6) - 1) * 100, 0.0), n


def origin_index(k: int) -> int:
    """Climate index of the last day of groundwater month k (the forecast origin)."""
    a = arrays()
    return (month_end(a["months"][k]) - a["d0"]).days


def well_features(k: int, h: int, wells: np.ndarray, fut_shift_days: int = 0,
                  overrides: dict | None = None) -> np.ndarray:
    """Feature rows (len(wells) x FEATURES) for wells at origin month index k, forecasting h months ahead.

    The forecast window runs from the day after month k ends to the end of month k+h. fut_shift_days = 0 uses the
    rain that actually fell (training); 365*s replays the same calendar window from s years earlier (forecasting)."""
    a = arrays()
    W, cal, normal, wt = a["W"], a["cal"], a["normal"], a["wt"]
    ti = wt[wells]
    e = origin_index(k)
    om = a["months"][k]
    y, mo = int(om[:4]), int(om[5:7]) - 1 + h
    target_end = month_end(f"{y + mo // 12}-{mo % 12 + 1:02d}")
    end = e + (target_end - month_end(om)).days
    start_doy = (month_end(om) + dt.timedelta(days=1)).timetuple().tm_yday - 1
    dn = W[wells, k]
    d3 = dn - W[wells, k - 3] if k >= 3 else np.full(len(wells), np.nan)
    d12 = dn - W[wells, k - 12] if k >= 12 else np.full(len(wells), np.nan)
    tcal = (cal[k] - 1 + h) % 12 + 1
    cols = {
        "depth_now": dn, "d3": d3, "d12": d12, "anom_now": dn - normal[wells, cal[k]],
        "seas": normal[wells, tcal] - normal[wells, cal[k]],
        "rain_dev_30": dev(a, e - 29, e)[0][ti], "rain_dev_90": dev(a, e - 89, e)[0][ti],
        "rain_dev_365": dev(a, e - 364, e)[0][ti],
        "et0_dev_90": dev(a, e - 89, e, "et0_cum", "et0n_cum")[0][ti],
        "fut_dev": dev(a, e + 1 - fut_shift_days, end - fut_shift_days)[0][ti],
        "fut_norm": (a["cyc"][start_doy % 365 + (end - e)] - a["cyc"][start_doy % 365])[ti],
        "horizon": np.full(len(wells), float(h)), "target_month": np.full(len(wells), float(tcal)),
    }
    if overrides:
        for name, fn in overrides.items():
            cols[name] = fn(cols)
    return np.column_stack([np.asarray(cols[n], dtype=np.float64) for n in FEATURES])


# ---------------------------------------------------------------- serving

@lru_cache(maxsize=1)
def load():
    if not MODEL_FILE.exists():
        return None
    import joblib
    return joblib.load(MODEL_FILE)


def card() -> dict | None:
    return json.loads(CARD_FILE.read_text()) if CARD_FILE.exists() else None


def _origin(as_of: str):
    """Last complete month before as_of (no look-ahead) as a groundwater month index."""
    a = arrays()
    d = dt.date.fromisoformat(as_of)
    prev = (d.replace(day=1) - dt.timedelta(days=1)).strftime("%Y-%m")
    months = a["months"]
    k = a["mi"].get(prev, len(months) - 1 if prev > months[-1] else 0)
    return k, d


def _taluk_paths(models, k0, d, overrides=None, quick=False):
    """Pessimistic / middle / optimistic taluk anomaly paths (dict p -> T x len(HORIZONS)) for months k0+1..k0+6.

    All (horizon x well-origin x past-year) feature blocks are stacked and predicted in one call per quantile model
    (hundreds of small predict calls made this ~30 s per date; batched it is ~1-2 s)."""
    a = arrays()
    W, wt, T, normal, cal = a["W"], a["wt"], a["T"], a["normal"], a["cal"]
    # each well's origin = its latest reading within FILL_MONTHS before k0
    origin_k = np.full(W.shape[0], -1)
    for back in range(FILL_MONTHS + 1):
        k = k0 - back
        if k < 0:
            break
        free = (origin_k < 0) & ~np.isnan(W[:, k])
        origin_k[free] = k
    qs = (0.5,) if quick else QUANTILES
    # earlier years whose forecast window (up to 6 months after k0) is fully on record
    e0 = origin_index(k0)
    scen = [s for s in range(1, SCENARIO_YEARS + 1) if e0 + 190 - 365 * s < a["nC"] and e0 + 1 - 365 * s >= 0]
    if quick:
        scen = scen[:4]
    paths = {p: np.full((T, len(HORIZONS)), np.nan) for p in (10, 50, 90)}
    if not scen:
        return paths

    blocks, mats = [], []                     # block = (j, wells, tcal, depth_now); one matrix per past year
    for j, h_abs in enumerate(HORIZONS):
        for k in sorted(set(origin_k[origin_k >= 0])):
            wells = np.where(origin_k == k)[0]
            h = h_abs + (k0 - k)                                  # same target month for every well
            tcal = (cal[k] - 1 + h) % 12 + 1
            for s in scen:
                mats.append(well_features(k, h, wells, fut_shift_days=365 * s, overrides=overrides))
            blocks.append((j, wells, tcal, mats[-1][:, FEATURES.index("depth_now")]))
    X = np.vstack(mats)
    pred = {q: models[q].predict(X) for q in qs}

    pos, per_j = 0, {}
    for j, wells, tcal, depth_now in blocks:
        n = len(wells)
        draws = []
        for _ in scen:
            for q in qs:
                draws.append(pred[q][pos:pos + n])
            pos += n
        # model predicts the depth change; anomaly at target = depth now + change - normal(target month)
        V = depth_now[None, :] + np.array(draws) - normal[wells, tcal][None, :]
        per_j.setdefault(j, []).append((wells, V))
    for j, parts in per_j.items():
        wells_all = np.concatenate([w for w, _ in parts])
        V = np.concatenate([v for _, v in parts], axis=1)        # (draws, wells)
        tw = wt[wells_all]
        for p in (10, 50, 90):
            vals = np.percentile(V, p, axis=0)
            for t in np.unique(tw):
                m = (tw == t) & np.isfinite(vals)
                if m.any():
                    paths[p][t, j] = np.median(vals[m])
    return paths


def _days_to(path, thr, now, offset):
    """Days from as_of until the path reaches thr (0 if already there; 366 = not within the 6-month horizon)."""
    hit = path >= thr[:, None]
    first = np.where(hit.any(axis=1), hit.argmax(axis=1) + 1, 0)
    days = np.where(first > 0, first * 30.44 - offset, 366.0)
    days = np.where(np.nan_to_num(now, nan=-99.0) >= thr, 0.0, days)
    days = np.where(np.all(np.isnan(path), axis=1), np.nan, days)
    return np.clip(days, 0, 366)


def _now_anom(k0):
    """Current taluk anomaly (median over wells, latest reading within FILL_MONTHS)."""
    a = arrays()
    A, wt, T = a["anom"], a["wt"], a["T"]
    out = np.full(T, np.nan)
    for back in range(FILL_MONTHS + 1):
        k = k0 - back
        if k < 0:
            break
        for t in np.where(np.isnan(out))[0]:
            v = A[wt == t, k]
            v = v[np.isfinite(v)]
            if len(v):
                out[t] = np.median(v)
    return out


def level(days_low, days_mid):
    """Two-tier early warning (validated on 2023 in models/gw_m2_card.json, "warning_tiers"):
    critical = at stress now or likely within 90 days; high = likely within 6 months;
    medium ("watch") = possible within 6 months on the pessimistic path; low = otherwise."""
    if days_mid <= 90:
        return "critical"
    if days_mid <= 183:
        return "high"
    if days_low <= 183:
        return "medium"
    return "low"


PRECOMPUTED = MODELS / "gw_m2_forecasts.npz"
DRIVER_KEYS = ("rain_deficit", "groundwater_already_low", "heat")


def forecast_origin(models, k0: int) -> dict:
    """Everything that depends only on the origin month k0: current anomaly, 10/50/90 paths, driver metres.
    Precomputed for every month by train/precompute_gw.py so the API doesn't run the model live."""
    now = _now_anom(k0)
    paths = _taluk_paths(models, k0, None)
    # counterfactual drivers: reset a factor to normal, re-forecast, compare the 3-month middle forecast.
    # + = this factor makes groundwater that many metres deeper (worse) in 3 months.
    cf = {
        "rain_deficit": {"rain_dev_30": lambda c: 0 * c["rain_dev_30"], "rain_dev_90": lambda c: 0 * c["rain_dev_90"],
                         "rain_dev_365": lambda c: 0 * c["rain_dev_365"]},
        "groundwater_already_low": {"depth_now": lambda c: c["depth_now"] - np.nan_to_num(c["anom_now"]),
                                    "anom_now": lambda c: 0 * np.nan_to_num(c["anom_now"]),
                                    "d3": lambda c: c["d3"] * 0, "d12": lambda c: c["d12"] * 0},
        "heat": {"et0_dev_90": lambda c: 0 * c["et0_dev_90"]},
    }
    base = _taluk_paths(models, k0, None, quick=True)[50][:, 2]
    drivers = {key: base - _taluk_paths(models, k0, None, overrides=ov, quick=True)[50][:, 2] for key, ov in cf.items()}
    return {"now": now, "paths": paths, "drivers_m": drivers}


@lru_cache(maxsize=1)
def _precomputed():
    if not PRECOMPUTED.exists():
        return None
    z = np.load(PRECOMPUTED)
    return {"months": [str(m) for m in z["months"]], "now": z["now"], "p10": z["p10"], "p50": z["p50"],
            "p90": z["p90"], **{f"drv_{k}": z[f"drv_{k}"] for k in DRIVER_KEYS}}


def _origin_data(k0: int):
    a = arrays()
    pre = _precomputed()
    if pre is not None and a["months"][k0] in pre["months"]:
        j = pre["months"].index(a["months"][k0])
        return {"now": pre["now"][j], "paths": {10: pre["p10"][j], 50: pre["p50"][j], 90: pre["p90"][j]},
                "drivers_m": {k: pre[f"drv_{k}"][j] for k in DRIVER_KEYS}}
    models = load()
    return None if models is None else forecast_origin(models, k0)


@lru_cache(maxsize=64)
def predict(as_of: str) -> dict | None:
    if _precomputed() is None and load() is None:   # precomputed first: no scikit-learn needed to serve it
        return None
    a = arrays()
    k0, d = _origin(as_of)
    o = _origin_data(k0)
    if o is None:
        return None
    offset = (d - month_end(a["months"][k0])).days
    thr, now, paths = a["thr"], o["now"], o["paths"]
    lo, mid, hi = (_days_to(paths[p], thr, now, offset) for p in (90, 50, 10))
    return {"origin_month": a["months"][k0], "threshold_m": thr, "anom_now": now, "paths": paths,
            "days_low": lo, "days_mid": mid, "days_high": hi, "drivers_m": o["drivers_m"],
            "levels": [level(lo[i], mid[i]) if np.isfinite(mid[i]) else None for i in range(len(mid))]}
