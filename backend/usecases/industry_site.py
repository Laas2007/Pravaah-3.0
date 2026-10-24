"""Site water-feasibility report for a new factory (owner: P4): a point in Karnataka + its water need -> verdict.

Everything is "as of" a date and uses only data on or before it. What each number rests on:
  REAL       taluk from the boundary polygons; NWDP wells within 10 km (depth now, 5-year trend, yearly May->Nov
             rise); IMD rain (normal, last 12 months, year-to-year variability); M1 drought labels per kharif season;
             M2 groundwater forecast (days to stress); M4 reservoir forecast for the district's reservoir system;
             CGWB/KGWD groundwater assessment 2023 (GWRA, GEC-2015): extractable resource, current extraction,
             stage of extraction, official category and the groundwater still available for future use;
             KIADB industrial land in the district; NWDP minor-irrigation tanks in the taluk.
  ESTIMATED  reuse 80 % of use becomes wastewater, 70 % of it recyclable; site rain harvesting 60 % runoff;
             groundwater vs surface share when the user doesn't give one.
  SCORE      transparent rules (no public records of factory water failures exist to train on); every component
             is returned with its reason so the verdict can be checked by hand.
"""
from __future__ import annotations

import datetime as dt
import json
from functools import lru_cache

import numpy as np

from core.data import KA, climate, last_complete_month, regions, tanks
from core.indicators import clean
from core.reservoirs import forecast_storage, storage_on
from core.risk import taluk_risk
from usecases.industry_m7 import ACRE_HA, NORM_KL_PER_HA_DAY, kiadb, system_of

TMC_M3 = 28.317e6
WELL_RADIUS_KM = 10.0
REUSE_SHARE = 0.8 * 0.7
RUNOFF = 0.6
LEVEL_SCORE = {"critical": 0, "high": 25, "medium": 60, "low": 100}
CATEGORY_SCORE = {"safe": 100, "semi_critical": 60, "critical": 30, "over_exploited": 0}
CATEGORY_TEXT = {"safe": "safe", "semi_critical": "semi-critical", "critical": "critical", "over_exploited": "over-exploited"}
VERDICTS = ["not_recommended", "risky", "conditional", "feasible"]


@lru_cache(maxsize=1)
def gwra() -> dict:
    f = KA / "gwra_2023.json"
    return json.loads(f.read_text(encoding="utf-8")) if f.exists() else {"taluks": {}}


# ---------- where is the point ----------

@lru_cache(maxsize=1)
def _polygons():
    g = json.loads((KA / "taluks.geojson").read_text(encoding="utf-8"))
    out = []
    for f in g["features"]:
        geom = f["geometry"]
        polys = [geom["coordinates"]] if geom["type"] == "Polygon" else geom["coordinates"]
        out.append((f["properties"]["idx"], [[np.asarray(ring, dtype=float) for ring in p] for p in polys]))
    return out


def _inside(ring: np.ndarray, x: float, y: float) -> bool:
    xs, ys = ring[:, 0], ring[:, 1]
    xj, yj = np.roll(xs, 1), np.roll(ys, 1)
    cross = ((ys > y) != (yj > y)) & (x < (xj - xs) * (y - ys) / np.where(yj - ys == 0, 1e-12, yj - ys) + xs)
    return bool(np.count_nonzero(cross) % 2)


def taluk_at(lat: float, lon: float) -> int | None:
    """Taluk idx whose polygon contains the point (holes respected), None if outside Karnataka."""
    for idx, polys in _polygons():
        for rings in polys:
            if _inside(rings[0], lon, lat) and not any(_inside(h, lon, lat) for h in rings[1:]):
                return int(idx)
    return None


def km(lat1, lon1, lat2, lon2):
    p1, p2 = np.radians(lat1), np.radians(lat2)
    a = np.sin((p2 - p1) / 2) ** 2 + np.cos(p1) * np.cos(p2) * np.sin(np.radians(lon2 - lon1) / 2) ** 2
    return 6371 * 2 * np.arcsin(np.sqrt(a))


# ---------- local evidence ----------

@lru_cache(maxsize=1)
def _wells():
    w = json.loads((KA / "gw_wells.json").read_text(encoding="utf-8"))["wells"]
    z = np.load(KA / "gw_well_monthly.npz")
    return (np.array([x["lat"] for x in w]), np.array([x["lon"] for x in w]), [str(m) for m in z["months"]],
            z["depth"].astype(float))


def nearby_wells(lat: float, lon: float, as_of: str) -> dict:
    """Wells within 10 km: latest depth, last-3-years trend, 10-year change and median yearly May->Nov rise
    (only months before as_of; + = deeper)."""
    la, lo, months, depth = _wells()
    d = km(lat, lon, la, lo)
    sel = np.where(d <= WELL_RADIUS_KM)[0]
    last = last_complete_month(as_of)
    k1 = max(i for i, m in enumerate(months) if m <= last)
    out = {"radius_km": WELL_RADIUS_KM, "count": int(sel.size), "nearest_km": round(float(d.min()), 1)}
    if sel.size == 0:
        return out
    D = depth[sel, : k1 + 1].copy()
    D[D <= 0] = np.nan                                       # 0 m readings are flowing / bad records
    recent = D[:, max(0, k1 - 11):]                          # last 12 months
    latest = [r[~np.isnan(r)][-1] for r in recent if (~np.isnan(r)).any()]
    yr = np.array([int(m[:4]) for m in months[: k1 + 1]])
    y_end = int(last[:4]) if last[5:] == "12" else int(last[:4]) - 1
    years = list(range(y_end - 9, y_end + 1))
    slopes, changes = [], []                                 # each well's own numbers, then the median well
    for row in D:
        ann = np.array([np.nanmedian(row[yr == y]) if np.isfinite(row[yr == y]).any() else np.nan for y in years])
        rec = ann[-3:]                                       # recent: last 3 full years
        if np.isfinite(rec).all():
            slopes.append(np.polyfit(years[-3:], rec, 1)[0])
        ok = np.where(np.isfinite(ann))[0]
        if ok.size >= 2 and ok[-1] - ok[0] >= 6:             # long-term: first vs last year, >= 6 years apart
            changes.append(ann[ok[-1]] - ann[ok[0]])
    trend = float(np.median(slopes)) if len(slopes) >= 2 else None
    rises = []
    for y in range(y_end - 9, y_end + 1):                    # May (pre-monsoon) minus Nov (post-monsoon), last 10 years
        try:
            k_may, k_nov = months.index(f"{y}-05"), months.index(f"{y}-11")
        except ValueError:
            continue
        if k_nov > k1:
            continue
        r = D[:, k_may] - D[:, k_nov]
        if np.isfinite(r).any():
            rises.append(float(np.nanmedian(r)))
    out.update({"depth_now_m": round(float(np.median(latest)), 1) if latest else None,
                "deepest_now_m": round(float(np.max(latest)), 1) if latest else None,
                "trend_m_per_year": round(trend, 2) if trend is not None else None,
                "trend_years": f"{years[-3]}-{years[-1]}", "trend_wells": len(slopes),
                "change_10y_m": round(float(np.median(changes)), 1) if len(changes) >= 2 else None,
                "change_years": f"{years[0]}-{years[-1]}", "change_wells": len(changes),
                "monsoon_rise_m": round(float(np.median(rises)), 2) if rises else None, "rise_years": len(rises)})
    return out


@lru_cache(maxsize=64)
def _annual_rain(as_of: str):
    """Per-taluk calendar-year rain totals for full years before as_of, plus last-365-day rain, ET0 and peak heat."""
    c = climate()
    y_last = dt.date.fromisoformat(as_of).year - 1
    tot = {}
    for y in sorted({int(d[:4]) for d in c.dates}):
        if y > y_last:
            break
        i0, i1 = c.index(f"{y}-01-01"), c.index(f"{y}-12-31")
        if c.dates[i0] == f"{y}-01-01" and c.dates[i1] == f"{y}-12-31":
            tot[y] = c.rain[i0:i1 + 1].sum(axis=0)
    t1 = c.index(as_of)
    t0 = max(0, t1 - 364)
    return tot, c.rain[t0:t1 + 1].sum(axis=0), c.et0[t0:t1 + 1].sum(axis=0), c.tmax[t0:t1 + 1].max(axis=0)


def drought_record(idx: int, as_of: str) -> dict:
    lab = json.loads((KA / "drought_labels.json").read_text(encoding="utf-8"))["years"]
    d = dt.date.fromisoformat(as_of)
    seen = [y for y in sorted(lab) if int(y) < d.year or (int(y) == d.year and d.month >= 10)]   # season finished
    hit = [y for y in seen if lab[y][idx] >= 1]
    return {"years_checked": len(seen), "drought_years": hit, "severe_years": [y for y in seen if lab[y][idx] == 2],
            "share": round(len(hit) / len(seen), 2) if seen else None}


# ---------- the report ----------

def feasibility(lat: float, lon: float, demand_kld: float, as_of: str, gw_share: float | None = None,
                site_area_ha: float | None = None) -> dict | None:
    idx = taluk_at(lat, lon)
    if idx is None:
        return None
    r = regions()[idx]
    district = r["district"]
    rk = taluk_risk(as_of)
    sname, dams = system_of(district)
    fc = forecast_storage(dams, as_of) if dams else None
    gw_default = gw_share is None
    if gw_default:
        gw_share = 0.4 if fc else 0.85                       # same dependence assumption as M7
    gw_share = float(np.clip(gw_share, 0, 1))
    gw_kld, sw_kld = demand_kld * gw_share, demand_kld * (1 - gw_share)

    # rain
    tot, last12, et0_12, tmax_12 = _annual_rain(as_of)
    yrs = list(tot)[-10:]
    ann = np.array([tot[y][idx] for y in yrs])
    normal = float(ann.mean())
    cv = float(ann.std() / normal) if normal else None
    drought = drought_record(idx, as_of)

    # groundwater
    wells = nearby_wells(lat, lon, as_of)
    off = gwra()["taluks"].get(str(idx))
    none_left = bool(off) and off["future_mld"] <= 0
    share_future = None if not off or none_left else 100 * gw_kld / (off["future_mld"] * 1000)
    extractable_mm = off["extractable_tmc"] * TMC_M3 / (r["area_km2"] * 1e6) * 1000 if off else None
    footprint_km2 = gw_kld * 365 / (extractable_mm / 1000) / 1e6 if extractable_mm else None
    level = rk["levels"][idx]
    days = {k: clean(rk[k][idx]) if rk[k] is not None else None for k in ("days_low", "days_mid", "days_high")}
    gap = None
    if rk.get("gw_threshold_m") is not None and rk.get("gw_anom_now_m") is not None:
        gap = clean(rk["gw_threshold_m"][idx] - rk["gw_anom_now_m"][idx])

    # surface
    surf = None
    if fc:
        st = {s["name"]: s for s in storage_on(as_of)}
        cap = sum(st[n]["design_gross_tmc"] for n in fc["dams"])
        p_low = max((p["p_low"] for p in fc["points"]), default=0.0)
        surf = {"system": sname, "dams": fc["dams"], "storage_now_tmc": fc["storage_now_tmc"], "capacity_tmc": round(cap, 1),
                "pct_full": round(100 * fc["storage_now_tmc"] / cap, 1) if cap else None,
                "p_low_6m": p_low, "months_of_supply": fc["months_of_supply"], "mode": fc["mode"],
                "demand_share_of_storage_pct": round(100 * sw_kld * 365 / (fc["storage_now_tmc"] * TMC_M3), 4)
                if fc["storage_now_tmc"] else None}

    # local competition
    k = kiadb().get(district)
    ind_mld = k["acres"] * ACRE_HA * NORM_KL_PER_HA_DAY / 1000 if k else 0.0
    tk = tanks().get(idx)

    # offsets
    reuse_kld = demand_kld * REUSE_SHARE
    rwh_kld = site_area_ha * 1e4 * normal / 1000 * RUNOFF / 365 if site_area_ha else None
    fresh_kld = max(0.0, demand_kld - reuse_kld - (rwh_kld or 0))

    # ----- score -----
    comps = []
    trend = wells.get("trend_m_per_year")
    s_gw_state = LEVEL_SCORE[level] if trend is None or trend <= 0.3 else max(0, LEVEL_SCORE[level] - 20)
    comps.append({"key": "gw_state", "label": "Groundwater outlook, next 6 months (M2 + nearby wells)", "score": s_gw_state,
                  "weight": gw_share, "why": f"taluk forecast tier {level}; wells within 10 km "
                  + (f"falling {trend} m a year" if (trend or 0) > 0 else "stable or rising" if trend is not None
                     else "too few readings for a trend")})
    if off:
        cat = off["category"]
        comps.append({"key": "gw_official", "label": "Official groundwater status (CGWB 2023)", "score": CATEGORY_SCORE[cat],
                      "weight": gw_share, "why": f"taluk is {CATEGORY_TEXT[cat]}: {off['stage_pct']}% of its yearly "
                                                 "extractable groundwater is already pumped"})
        if gw_kld > 0:
            s_load = 0 if none_left else 100 if share_future < 1 else 70 if share_future < 5 else 40 if share_future < 20 \
                else 10 if share_future < 100 else 0
            comps.append({"key": "gw_load", "label": "Groundwater still available for new use", "score": s_load,
                          "weight": gw_share, "why": "none: the official assessment leaves no groundwater for future use"
                          if none_left else f"the factory's groundwater part would take {share_future:.1f}% of the "
                                            f"{off['future_mld']} MLD still available"})
    if surf:
        comps.append({"key": "surface", "label": f"Reservoir reliability ({sname}, M4)",
                      "score": round(100 * (1 - surf["p_low_6m"])), "weight": 1 - gw_share,
                      "why": f"{round(surf['p_low_6m'] * 100)}% chance storage falls below 15% of capacity within 6 months; "
                             f"now {surf['pct_full']}% full"})
    elif gw_share < 1:
        comps.append({"key": "surface", "label": "Surface water", "score": 20, "weight": 1 - gw_share,
                      "why": "no modelled reservoir system serves this district: surface supply would rely on tanks, "
                             "a KIADB scheme or tankers"})
    sh = drought["share"] or 0
    s_rain = 100 if sh < 0.2 else 70 if sh < 0.35 else 40 if sh < 0.5 else 15
    if cv is not None and cv > 0.3:
        s_rain = max(0, s_rain - 15)
    comps.append({"key": "rain", "label": "Rainfall reliability", "score": s_rain, "weight": 0.5,
                  "why": f"kharif drought in {len(drought['drought_years'])} of {drought['years_checked']} seasons; "
                         f"yearly rain varies ±{round((cv or 0) * 100)}%"})
    wsum = sum(c["weight"] for c in comps)
    score = round(sum(c["score"] * c["weight"] for c in comps) / wsum)
    verdict = "feasible" if score >= 70 else "conditional" if score >= 45 else "risky" if score >= 25 else "not_recommended"
    gates = []
    if off and off["category"] == "over_exploited" and gw_share >= 0.5:
        gates.append("Mostly groundwater in an officially over-exploited taluk: capped at 'risky' whatever the score.")
        verdict = VERDICTS[min(VERDICTS.index(verdict), 1)]
    if none_left and gw_share > 0 and not gates:
        gates.append("No groundwater left for new use officially: capped at 'conditional' until the groundwater share is 0.")
        verdict = VERDICTS[min(VERDICTS.index(verdict), 2)]

    # expected shortfall days in the next 6 months for this supply mix (same logic as M7)
    mid = days["days_mid"]
    gw_short = (183 - min(mid, 183)) / 183 if mid is not None else 0.0
    shortfall_days = round(183 * (gw_share * gw_short + (1 - gw_share) * (surf["p_low_6m"] if surf else 0.5)))

    recs = []
    if off and off["category"] in ("over_exploited", "critical") and gw_kld > 0:
        recs.append(f"The taluk is officially {CATEGORY_TEXT[off['category']]} ({off['stage_pct']}% extracted): CGWA "
                    "groundwater permission (NOC) for new industry here is restricted and comes with recharge and "
                    "water-audit conditions. Plan for surface water, a KIADB supply or treated wastewater instead.")
    elif share_future is not None and share_future >= 5 and gw_kld > 0:
        recs.append(f"The groundwater draw would use {share_future:.0f}% of the taluk's remaining groundwater: lower "
                    "the groundwater share or build recharge structures.")
    if level in ("critical", "high") and gw_kld > 0:
        recs.append("Groundwater here is forecast to reach stress within 6 months: don't rely on new borewells as the "
                    "main source.")
    if (trend or 0) > 0.3:
        recs.append(f"Nearby wells are falling {trend} m a year: expect deeper, costlier borewells.")
    if surf and surf["p_low_6m"] >= 0.25:
        recs.append(f"{sname} has a {round(surf['p_low_6m'] * 100)}% chance of low storage in 6 months: keep "
                    f"{max(7, round(shortfall_days / 3))} days of on-site storage.")
    recs.append(f"Recycling 70% of wastewater (STP/ZLD) cuts fresh-water need from {demand_kld:,.0f} to "
                f"{demand_kld - reuse_kld:,.0f} kL/day.")
    if rwh_kld:
        recs.append(f"Harvesting rain on the {site_area_ha:g} ha site adds about {rwh_kld:,.0f} kL/day on average "
                    "(mostly Jun-Nov; needs storage).")
    if wells["count"] == 0:
        recs.append(f"No monitoring well within {WELL_RADIUS_KM:g} km (nearest {wells['nearest_km']} km): get a "
                    "hydrogeological survey and pumping test before relying on groundwater.")

    official = None
    if off:
        official = {k: off[k] for k in ("category", "stage_pct", "extractable_mld", "extraction_mld", "future_mld", "units")}
        official["industrial_mld"] = round(off["industrial_tmc"] * TMC_M3 / 365 / 1000, 1)
        official["irrigation_share_pct"] = round(100 * off["irrigation_tmc"] / off["extraction_tmc"]) if off["extraction_tmc"] else None
    return {
        "as_of": as_of, "model": rk["model"], "lat": lat, "lon": lon,
        "taluk_idx": idx, "taluk": r["name"], "district": district, "taluk_area_km2": r["area_km2"],
        "demand": {"kld": demand_kld, "mld": round(demand_kld / 1000, 3), "m3_per_year": round(demand_kld * 365),
                   "groundwater_share": gw_share, "groundwater_share_default": gw_default,
                   "groundwater_kld": round(gw_kld, 1), "surface_kld": round(sw_kld, 1),
                   "equiv_kiadb_ha": round(demand_kld / NORM_KL_PER_HA_DAY, 1)},
        "verdict": verdict, "score": score, "components": comps, "gates": gates, "risk": level,
        "shortfall_days_6m": shortfall_days,
        "rain": {"normal_mm": round(normal), "normal_years": f"{yrs[0]}-{yrs[-1]}", "last_12m_mm": round(float(last12[idx])),
                 "last_12m_dev_pct": round(100 * (float(last12[idx]) / normal - 1)) if normal else None,
                 "variability_pct": round(cv * 100) if cv is not None else None,
                 "et0_12m_mm": round(float(et0_12[idx])), "tmax_12m_c": round(float(tmax_12[idx]), 1), "drought": drought},
        "groundwater": {"tier": level, **days, "gap_to_stress_m": gap, "wells": wells, "official": official,
                        "share_of_available_pct": round(share_future, 2) if share_future is not None else None,
                        "nothing_available": none_left,
                        "footprint_km2": round(footprint_km2, 2) if footprint_km2 else None},
        "surface": surf,
        "context": {"kiadb_areas_in_district": k["areas"] if k else 0, "kiadb_demand_mld_district": round(ind_mld, 1),
                    "tanks_in_taluk": int(tk["tanks"]) if tk else 0,
                    "tank_storage_mcm": round(tk["storage_mcft"] * 0.0283168, 2) if tk else None},
        "offsets": {"reuse_kld": round(reuse_kld), "rainwater_kld": round(rwh_kld) if rwh_kld else None,
                    "fresh_after_offsets_kld": round(fresh_kld)},
        "recommendations": recs,
        "assumptions": {"reuse_share": REUSE_SHARE, "runoff": RUNOFF,
                        "groundwater_share_default": "40% where a modelled reservoir system serves the district, else 85%"},
        "sources": {"real": ["taluk boundaries", "NWDP wells within 10 km", "IMD rain", "M1 drought labels",
                             "M2 groundwater forecast", "CGWB groundwater assessment 2023 (GWRA)",
                             *(["M4 reservoir forecast"] if surf else []), "KIADB land", "NWDP tanks"],
                    "estimated": ["reuse and harvesting shares", "groundwater share default"]},
    }
