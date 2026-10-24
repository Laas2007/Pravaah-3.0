"""/api/core/* — shared endpoints the 3 platforms use (taluk list, boundaries, per-taluk indicators)."""
from fastapi import APIRouter
from fastapi.responses import Response

from .data import climate, clamp_date, geojson_bytes, groundwater, regions, taluk
from .indicators import clean, taluk_indicators
from .risk import taluk_risk

router = APIRouter(prefix="/api/core", tags=["core"])


@router.get("/meta")
def meta():
    c, g = climate(), groundwater()
    return {
        "taluk_count": len(regions()),
        "districts": sorted({r["district"] for r in regions()}),
        "climate_from": c.dates[0], "climate_until": c.dates[-1], "rain_imd_until": c.imd_until,
        "groundwater_from": g.months[0], "groundwater_until": g.months[-1],
        "min_as_of": c.dates[365],
        "story_dates": [
            {"label": "Latest data", "date": c.dates[-1]},
            {"label": "1 Aug 2023 (monsoon failing)", "date": "2023-08-01"},
            {"label": "1 Mar 2024 (crisis peak)", "date": "2024-03-01"},
            {"label": "1 Aug 2022 (wet year)", "date": "2022-08-01"},
        ],
    }


@router.get("/regions")
def api_regions():
    return {"taluks": regions()}


@router.get("/taluks.geojson")
def taluks_geojson():
    return Response(geojson_bytes("taluks"), media_type="application/geo+json")


@router.get("/districts.geojson")
def districts_geojson():
    return Response(geojson_bytes("districts"), media_type="application/geo+json")


@router.get("/indicators")
def api_indicators(as_of: str | None = None):
    """Real-data indicators + provisional risk for every taluk on a date (map colouring)."""
    as_of = clamp_date(as_of)
    ind = taluk_indicators(as_of)
    rk = taluk_risk(as_of)
    score, levels = rk["score"], rk["levels"]
    return {
        "as_of": as_of, "model": rk["model"],
        "taluks": [{"idx": r["idx"], "risk": levels[i], "stress": clean(score[i]),
                    **{k: clean(v[i]) for k, v in ind.items()}} for i, r in enumerate(regions())],
    }


@router.get("/taluk/{idx}")
def api_taluk(idx: int, as_of: str | None = None):
    as_of = clamp_date(as_of)
    t = taluk(idx)
    ind = taluk_indicators(as_of)
    rk = taluk_risk(as_of)
    score, levels = rk["score"], rk["levels"]
    g = groundwater()
    hist = [{"month": m, "depth": clean(g.depth[k, idx]), "anom": clean(g.anom[k, idx]), "wells": int(g.wells[k, idx])}
            for k, m in enumerate(g.months) if m >= "2014-01" and m <= as_of[:7]]
    return {**t, "as_of": as_of, "model": rk["model"], "risk": levels[idx], "stress": clean(score[idx]),
            "indicators": {k: clean(v[idx]) for k, v in ind.items()}, "groundwater_history": hist}
