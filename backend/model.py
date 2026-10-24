"""Ward-level groundwater balance model for Bengaluru.

Every ward carries a groundwater store S (mm of water over the ward's area).
Each day:

    S += recharge(rain) - borewell_draw + lateral_inflow

    recharge        = rc * min(max(rain - 2, 0), 40)        (rc lower in paved wards)
    demand          = population * lpcd + commercial/industrial load
    piped supply    = demand * cauvery_coverage * cauvery_reliability
    borewell_draw   = demand - piped supply
    lateral_inflow  = lam * (regional_level - S)            (deeper/neighbouring aquifer)

A shortage starts when S falls below SHORTAGE_LEVEL of capacity (borewells
start failing, tanker dependence spikes).

Forecast: from the as-of date, the model is re-run once for every past
rainfall year available at that date (and three demand scenarios), giving an
ensemble of "days until shortage"; the reported range is its 25th-75th
percentile. Backtests only use rainfall years that had fully happened before
the as-of date, so there is no look-ahead.

Explanations: each driver is reset to the city-typical value and the forecast
is re-run; the change in days is that driver's contribution.
"""
from __future__ import annotations

import datetime as dt
import json
import math
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import numpy as np

DATA = Path(__file__).parent / "data"

CITY_CENTRE = (12.9791, 77.5913)  # Vidhana Soudha
POP_2011_PER_WARD = 8_443_675 / 243  # 2023 delimitation splits the 2011 census evenly
LPCD = 135  # CPHEEO domestic norm, litres/person/day
STAGE5_START = dt.date(2024, 10, 16)  # Cauvery Water Supply Scheme Stage V commissioned
HORIZON = 365

# Commercial / industrial / IT-park load, ML per day (estimates, see README).
COMMERCIAL_LOAD = {
    "Whitefield": 3.0, "Hagadur": 2.0, "Kadugodi": 1.5, "Mahadevapura": 2.0,
    "Marathahalli": 1.5, "Bellanduru": 2.0, "Doddakanahalli": 1.0, "Varthuru": 1.0,
    "Peenya": 3.0, "Bommanahalli": 1.0, "Begur": 0.8, "HAL Airport": 1.0,
    "Koramangala": 0.8, "Hebbala": 0.8, "Nagavara": 0.8, "Thanisandra": 0.6,
    "Jakkuru": 0.5, "Kudlu": 0.8, "HSR - Singasandra": 1.0, "T Dasarahalli": 1.0,
    "Chokkasandra": 1.0, "Rajagopal Nagar": 0.5, "Dodda Nekkundi": 1.0,
    "A Narayanapura": 0.5, "K R Puram": 0.6, "Devasandra": 0.4,
    "Kumaraswamy Layout": 0.3, "Hulimavu": 0.5, "Kodigehalli": 0.5,
}


@dataclass(frozen=True)
class Params:
    capacity_mm: float = 300.0      # usable aquifer storage (specific yield x saturated depth)
    regional_frac: float = 0.66     # regional equilibrium level, fraction of capacity
    lam: float = 1 / 150            # lateral exchange rate, per day
    shortage_frac: float = 0.30     # below this, borewells fail
    lpcd: float = LPCD
    reliability_k: float = 0.30     # Cauvery supply cut per unit catchment deficit
    leak_frac: float = 0.30         # share of piped supply that leaks / seeps back to groundwater
    reg_k: float = 1.0              # regional water table response to a wet/dry year


@dataclass(frozen=True)
class Intervention:
    """Official-view what-ifs, applied from the as-of date onwards."""
    extra_piped: float = 0.0        # add to Cauvery coverage (0..1)
    rwh_boost: float = 0.0          # rainwater harvesting: relative recharge boost (0..1)
    demand_cut: float = 0.0         # relative demand reduction (0..1)
    tanker_mld: float = 0.0         # trucked-in water from outside the ward, ML/day


# ---------------------------------------------------------------- geometry

def _ring_area_centroid(ring, lat0):
    kx = 111.32 * math.cos(math.radians(lat0))
    ky = 110.57
    pts = [(x * kx, y * ky) for x, y in ring]
    a = cx = cy = 0.0
    for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]):
        c = x1 * y2 - x2 * y1
        a += c
        cx += (x1 + x2) * c
        cy += (y1 + y2) * c
    a *= 0.5
    if abs(a) < 1e-12:
        return 0.0, ring[0][0], ring[0][1]
    return abs(a), cx / (6 * a) / kx, cy / (6 * a) / ky


def _ward_shape(geom):
    polys = geom["coordinates"] if geom["type"] == "MultiPolygon" else [geom["coordinates"]]
    lat0 = polys[0][0][0][1]
    tot = sx = sy = 0.0
    for poly in polys:
        a, x, y = _ring_area_centroid(poly[0], lat0)
        for hole in poly[1:]:
            a -= _ring_area_centroid(hole, lat0)[0]
        tot += a
        sx += a * x
        sy += a * y
    return tot, sx / tot, sy / tot


def _dist_km(lat, lon):
    dy = (lat - CITY_CENTRE[0]) * 110.57
    dx = (lon - CITY_CENTRE[1]) * 111.32 * math.cos(math.radians(lat))
    return math.hypot(dx, dy)


# ---------------------------------------------------------------- data

@dataclass
class World:
    names: list
    ids: list
    lat: np.ndarray
    lon: np.ndarray
    area: np.ndarray        # km2
    dist: np.ndarray        # km from centre
    coverage0: np.ndarray   # Cauvery piped coverage before Stage V
    stage5_gain: np.ndarray
    growth: np.ndarray      # population growth per year since 2011
    rc: np.ndarray          # recharge coefficient
    commercial: np.ndarray  # ML/day
    dates: list
    rain: np.ndarray        # (days, wards) mm
    catch: np.ndarray       # (days,) catchment mean mm
    rain_normal: np.ndarray # annual normal per ward (2014-2022 mean)
    catch_normal: float
    geojson: dict = field(repr=False)


@lru_cache(maxsize=1)
def load_world() -> World:
    gj = json.loads((DATA / "bbmp_wards.geojson").read_text())
    rf = json.loads((DATA / "rainfall.json").read_text())

    names, ids, lat, lon, area, dist = [], [], [], [], [], []
    for f in gj["features"]:
        p = f["properties"]
        a, x, y = _ward_shape(f["geometry"])
        names.append(p["KGISWardName"].strip().replace("  ", " "))
        ids.append(int(p["KGISWardNo"]))
        lat.append(y)
        lon.append(x)
        area.append(a)
        dist.append(_dist_km(y, x))
    lat, lon, area, dist = map(np.array, (lat, lon, area, dist))

    # Older core is on Cauvery pipes; the 110 villages merged in 2007 (outer
    # ring) mostly relied on borewells until Stage V.
    coverage0 = np.clip(0.90 - 0.055 * np.maximum(dist - 5, 0), 0.15, 0.90)
    stage5_gain = np.where(dist > 9, np.clip(0.04 * (dist - 9), 0, 0.30), 0.0)
    growth = np.clip(0.004 + 0.0045 * np.maximum(dist - 4, 0), 0.004, 0.06)
    lake_bonus = np.array([0.025 if any(k in n for k in ("Lake", "Bellanduru", "Varthuru", "Hebbala", "Agara", "Hulimavu", "Madivala", "Ulsoor", "Sarakki", "Kalkere", "Jakkuru")) else 0.0 for n in names])
    rc = 0.05 + 0.0075 * np.minimum(dist, 14) + lake_bonus
    commercial = np.array([COMMERCIAL_LOAD.get(n, 0.0) for n in names])

    # nearest rainfall grid point per ward
    grid = rf["city_grid"]
    glat = np.array([g["lat"] for g in grid])
    glon = np.array([g["lon"] for g in grid])
    nearest = [int(np.argmin((glat - la) ** 2 + (glon - lo) ** 2)) for la, lo in zip(lat, lon)]
    grain = np.array([g["rain"] for g in grid]).T  # (days, grid)
    rain = grain[:, nearest]
    catch = np.mean([np.array(v) for v in rf["catchment"].values()], axis=0)

    # "Normal" = mean of 2014-2022, i.e. only years before the 2023 drought.
    n_norm = sum(1 for x in rf["dates"] if x < "2023-01-01")
    rain_normal = rain[:n_norm].sum(axis=0) / (n_norm / 365.25)
    catch_normal = float(catch[:n_norm].sum() / (n_norm / 365.25))

    return World(names, ids, lat, lon, area, dist, coverage0, stage5_gain, growth, rc,
                 commercial, rf["dates"], rain, catch, rain_normal, catch_normal, gj)


# ---------------------------------------------------------------- core simulation

def _date_index(w: World, d: dt.date) -> int:
    i = (d - dt.date.fromisoformat(w.dates[0])).days
    return int(np.clip(i, 0, len(w.dates) - 1))


def _population(w: World, year: float, scale=1.0):
    return POP_2011_PER_WARD * (1 + w.growth * (year - 2011)) * scale


def _coverage(w: World, d: dt.date):
    if d < STAGE5_START:
        return w.coverage0
    ramp = min((d - STAGE5_START).days / 540, 1.0)  # connections roll out over ~18 months
    return np.minimum(w.coverage0 + w.stage5_gain * ramp, 0.92)


def _reliability(catch365_ratio, p: Params):
    return np.clip(1 - p.reliability_k * np.maximum(1 - catch365_ratio, 0), 0.75, 1.0)


@dataclass
class Drivers:
    """Per-ward driver arrays that the counterfactuals swap out."""
    coverage: np.ndarray
    density: np.ndarray       # people per km2
    commercial: np.ndarray    # ML/day
    rc: np.ndarray
    reliability: float | np.ndarray


def _daily_draw(w, drv: Drivers, p: Params, demand_scale=1.0, extra_piped=0.0, tanker=0.0):
    """Net groundwater draw in mm/day for each ward (negative = net seepage gain).

    Borewells cover whatever the pipes and tankers don't; a share of piped
    water leaks from mains and returns to the aquifer.
    """
    demand = (drv.density * p.lpcd / 1e6 + drv.commercial / w.area) * demand_scale  # mm/day
    cov = np.minimum(drv.coverage + extra_piped, 0.95)
    piped = demand * cov * drv.reliability
    borewell = np.maximum(demand - piped - tanker / w.area, 0.0)
    return borewell - p.leak_frac * piped


def _recharge(rain, rc):
    return rc * np.clip(rain - 2.0, 0, 40)


def _step(S, rain, draw, rc, p: Params, reg):
    cap = p.capacity_mm
    # borewell yield collapses as the aquifer empties
    yield_f = np.clip((S / cap - 0.05) / 0.25, 0.0, 1.0)
    draw = np.where(draw > 0, draw * yield_f, draw)
    S = S + _recharge(rain, rc) - draw + p.lam * (reg * cap - S)
    return np.clip(S, 0, cap)


def _regional(trailing365, normal, p: Params):
    """Regional water-table level (fraction of capacity) after a wet/dry year."""
    return np.clip(p.regional_frac + p.reg_k * (trailing365 / normal - 1), 0.15, 0.9)


def _trailing(rain_seq, lead):
    """Trailing 365-day sums for rows lead..end of rain_seq (needs lead >= 364)."""
    c = np.concatenate([np.zeros((1,) + rain_seq.shape[1:]), np.cumsum(rain_seq, axis=0)])
    idx = np.arange(lead, len(rain_seq))
    return c[idx + 1] - c[idx - 364]


@lru_cache(maxsize=4)
def simulate_history(p: Params = Params()) -> np.ndarray:
    """Groundwater store for every ward on every observed day, shape (days, wards)."""
    w = load_world()
    n = len(w.dates)
    d0 = dt.date.fromisoformat(w.dates[0])
    # first year has no trailing window: pad with the normal
    padded = np.vstack([np.tile(w.rain_normal / 365, (364, 1)), w.rain])
    reg = _regional(_trailing(padded, 364), w.rain_normal, p)
    catch_pad = np.concatenate([np.full(364, w.catch_normal / 365), w.catch])
    catch_t = _trailing(catch_pad, 364)
    S = np.full(len(w.names), p.regional_frac * p.capacity_mm)
    out = np.empty((n, len(w.names)))
    for warm in range(2):  # spin-up on the first year
        for t in range(365):
            S = _step(S, w.rain[t], _draw_at(w, d0, t, p, catch_t[t] / w.catch_normal), w.rc, p, reg[t])
    for t in range(n):
        S = _step(S, w.rain[t], _draw_at(w, d0, t, p, catch_t[t] / w.catch_normal), w.rc, p, reg[t])
        out[t] = S
    return out


def _draw_at(w, d0, t, p, catch_ratio):
    d = d0 + dt.timedelta(days=t)
    drv = Drivers(_coverage(w, d), _population(w, d.year + d.timetuple().tm_yday / 365) / w.area,
                  w.commercial, w.rc, _reliability(catch_ratio, p))
    return _daily_draw(w, drv, p)


# ---------------------------------------------------------------- forecasting

DEMAND_SCENARIOS = (0.92, 1.0, 1.08)


def _members(w: World, t0: int):
    """Start indices of past rainfall years usable as futures for as-of index t0.

    Member k replays the 365 days that followed the same calendar date k years
    earlier, so every member is weather that had already happened by t0.
    """
    starts = [t0 - 365 * k + 1 for k in range(1, 20) if t0 - 365 * k + 1 >= 0]
    return starts or [0]


def _past365(w, t0, rain_scale=None):
    """Observed rain for the 365 days ending at t0 (optionally rescaled)."""
    lo = t0 - 364
    if lo >= 0:
        past = w.rain[lo: t0 + 1].copy()
    else:
        past = np.vstack([np.tile(w.rain_normal / 365, (-lo, 1)), w.rain[: t0 + 1]])
    return past if rain_scale is None else past * rain_scale


def _forecast(w, S0, t0, drv: Drivers, p: Params, iv: Intervention, past=None):
    """Days until shortage for each ward x ensemble member. Returns (wards, members).

    All rainfall members and demand scenarios run together as one array of
    shape (wards, members, scenarios).
    """
    past = _past365(w, t0) if past is None else past
    thresh = p.shortage_frac * p.capacity_mm
    starts = _members(w, t0)
    fut = np.stack([w.rain[s: s + HORIZON] for s in starts], axis=2)                    # (H, W, M)
    reg = np.stack([_regional(_trailing(np.vstack([past, fut[:, :, m]]), 365), w.rain_normal, p)
                    for m in range(len(starts))], axis=2)                               # (H, W, M)
    scales = np.array(DEMAND_SCENARIOS) * (1 - iv.demand_cut)
    draw = np.stack([_daily_draw(w, drv, p, sc, iv.extra_piped, iv.tanker_mld) for sc in scales], axis=1)[:, None, :]
    rc = (drv.rc * (1 + iv.rwh_boost))[:, None, None]
    S = np.broadcast_to(S0[:, None, None], (len(S0), len(starts), len(scales))).copy()
    hit = np.where(S < thresh, 0.0, HORIZON + 1.0)
    for k in range(HORIZON):
        S = _step(S, fut[k][:, :, None], draw, rc, p, reg[k][:, :, None])
        hit[(S < thresh) & (hit > HORIZON)] = k + 1
    return hit.reshape(len(S0), -1)


def _summary(days_row):
    lo, mid, hi = np.percentile(days_row, [25, 50, 75])
    return float(lo), float(mid), float(hi)


def risk_level(mid):
    if mid <= 30:
        return "critical"
    if mid <= 90:
        return "high"
    if mid <= 180:
        return "medium"
    return "low"


def _rewind(w, hist, t0, drv: Drivers, p: Params, rain_scale=None):
    """Re-simulate the 365 days before t0 with alternative drivers / rainfall.

    Returns the counterfactual state at t0 and the rain series used."""
    ts = max(t0 - 364, 0)
    S = hist[ts - 1].copy() if ts > 0 else np.full(len(w.names), p.regional_frac * p.capacity_mm)
    past = _past365(w, t0, rain_scale)
    before = _past365(w, ts - 1) if ts > 0 else np.tile(w.rain_normal / 365, (365, 1))
    reg = _regional(_trailing(np.vstack([before, past]), 365), w.rain_normal, p)
    draw = _daily_draw(w, drv, p)
    for k in range(len(past)):
        S = _step(S, past[k], draw, drv.rc, p, reg[k])
    return S, past


def _drivers_at(w: World, d: dt.date, t0: int, p: Params) -> Drivers:
    catch365 = w.catch[max(t0 - 364, 0): t0 + 1].sum()
    return Drivers(_coverage(w, d), _population(w, d.year + d.timetuple().tm_yday / 365) / w.area,
                   w.commercial, w.rc, _reliability(catch365 / w.catch_normal, p))


FACTORS = {
    "rain_deficit": "Rainfall over the past 12 months vs normal",
    "borewell_dependence": "Dependence on borewells (low Cauvery pipe coverage)",
    "population_density": "Population density / demand",
    "commercial_load": "IT parks, industry & commercial water use",
    "cauvery_deficit": "Cauvery catchment deficit (cuts to piped supply)",
    "paved_surface": "Paved, built-up land limiting recharge",
}


@lru_cache(maxsize=64)
def predict(as_of: str, iv: Intervention = Intervention(), explain: bool = True):
    p = Params()
    w = load_world()
    hist = simulate_history(p)
    d = dt.date.fromisoformat(as_of)
    t0 = _date_index(w, d)
    d = dt.date.fromisoformat(w.dates[t0])
    drv = _drivers_at(w, d, t0, p)
    S0 = hist[t0]
    base = _forecast(w, S0, t0, drv, p, iv)
    summ = [_summary(r) for r in base]
    mids = np.array([s[1] for s in summ])

    contribs, level_pts = {}, {}
    rain12 = w.rain[max(t0 - 364, 0): t0 + 1].sum(axis=0)
    rnorm = w.rain_normal
    if explain:
        med = lambda a: float(np.median(a))
        cf = {
            "rain_deficit": (dict(), np.clip(rnorm / np.maximum(rain12, 1), 0.5, 2.0)),
            "borewell_dependence": (dict(coverage=np.full_like(drv.coverage, med(drv.coverage))), None),
            "population_density": (dict(density=np.full_like(drv.density, med(drv.density))), None),
            "commercial_load": (dict(commercial=np.zeros_like(drv.commercial)), None),
            "cauvery_deficit": (dict(reliability=1.0), None),
            "paved_surface": (dict(rc=np.full_like(drv.rc, med(drv.rc))), None),
        }
        for key, (over, rain_scale) in cf.items():
            d2 = Drivers(**{**drv.__dict__, **over})
            S_cf, past_cf = _rewind(w, hist, t0, d2, p, rain_scale)
            cf_days = _forecast(w, S_cf, t0, d2, p, iv, past_cf)
            # positive = this driver brings the shortage closer by N days
            contribs[key] = np.median(cf_days, axis=1) - mids
            level_pts[key] = (S_cf - S0) / p.capacity_mm * 100

    cap = p.capacity_mm
    D = drv.density * p.lpcd / 1e6 + drv.commercial / w.area
    wards = []
    for i, name in enumerate(w.names):
        lo, mid, hi = summ[i]
        wards.append({
            "idx": i,
            "name": name,
            "ward_no": w.ids[i],
            "lat": round(float(w.lat[i]), 5),
            "lon": round(float(w.lon[i]), 5),
            "days_low": int(round(lo)),
            "days_mid": int(round(mid)),
            "days_high": int(round(hi)),
            "risk": risk_level(mid),
            "groundwater_pct": round(float(S0[i] / cap * 100), 1),
            "inputs": {
                "area_km2": round(float(w.area[i]), 2),
                "population": int(drv.density[i] * w.area[i]),
                "cauvery_coverage_pct": round(float(drv.coverage[i] * 100), 1),
                "demand_mld": round(float(D[i] * w.area[i]), 2),
                "commercial_mld": float(w.commercial[i]),
                "rain_12m_mm": round(float(rain12[i])),
                "rain_normal_mm": round(float(rnorm[i])),
                "cauvery_supply_pct": round(float(np.mean(drv.reliability) * 100), 1),
                "recharge_coeff": round(float(w.rc[i]), 3),
            },
            "drivers": sorted(
                [{"key": k, "label": FACTORS[k], "days": int(round(float(v[i]))),
                  "prevents": bool(mid <= HORIZON and mid + v[i] > HORIZON),
                  "level_pts": round(float(level_pts[k][i]), 1)} for k, v in contribs.items()],
                key=lambda x: (-x["days"], -x["level_pts"]),
            ) if explain else [],
        })
    return {
        "as_of": d.isoformat(),
        "data_until": w.dates[-1],
        "ensemble_size": int(base.shape[1]),
        "horizon": HORIZON,
        "wards": wards,
    }


def ward_timeseries(idx: int, as_of: str, step: int = 7):
    """Simulated groundwater level history + forecast band for one ward."""
    p = Params()
    w = load_world()
    hist = simulate_history(p)
    t0 = _date_index(w, dt.date.fromisoformat(as_of))
    ts = max(t0 - 3 * 365, 0)
    cap = p.capacity_mm
    past = [{"date": w.dates[t], "level": round(float(hist[t, idx] / cap * 100), 1)} for t in range(ts, t0 + 1, step)]

    # forecast trajectories for this ward only
    d = dt.date.fromisoformat(w.dates[t0])
    drv = _drivers_at(w, d, t0, p)
    draw = _daily_draw(w, drv, p)[idx]
    trajs = []
    past_rain = _past365(w, t0)[:, idx]
    for s in _members(w, t0):
        fut = w.rain[s: s + HORIZON, idx]
        reg = _regional(_trailing(np.concatenate([past_rain, fut]), 365), w.rain_normal[idx], p)
        S = np.array([hist[t0, idx]])
        tr = []
        for k in range(HORIZON):
            S = _step(S, fut[k], np.array([draw]), w.rc[idx], p, reg[k])
            tr.append(float(S[0]) / cap * 100)
        trajs.append(tr)
    trajs = np.array(trajs)
    lo, mid, hi = np.percentile(trajs, [10, 50, 90], axis=0)
    future = []
    for k in range(step - 1, HORIZON, step):
        fd = d + dt.timedelta(days=k + 1)
        future.append({"date": fd.isoformat(), "lo": round(float(lo[k]), 1), "mid": round(float(mid[k]), 1), "hi": round(float(hi[k]), 1)})
    actual = []
    for t in range(t0 + step, min(t0 + HORIZON + 1, len(w.dates)), step):
        actual.append({"date": w.dates[t], "level": round(float(hist[t, idx] / cap * 100), 1)})
    return {"past": past, "future": future, "actual_after": actual, "shortage_level": p.shortage_frac * 100}
