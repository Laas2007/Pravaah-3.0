"""/api/core/* — shared endpoints the 3 platforms use (taluk list, boundaries, per-taluk indicators)."""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from fastapi.responses import Response

from .data import climate, clamp_date, geojson_bytes, groundwater, last_complete_month, regions, taluk
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
        "taluks": [{"idx": r["idx"], "risk": levels[i], "stress": clean(score[i]), "source": rk["source"][i],
                    "days_mid": clean(rk["days_mid"][i]) if rk["days_mid"] is not None else None,
                    **{k: clean(v[i]) for k, v in ind.items()}} for i, r in enumerate(regions())],
    }


def forecast_for(rk: dict, idx: int, as_of: str) -> dict | None:
    """M2 forecast block for one taluk (None when the taluk falls back to the provisional index)."""
    if rk["days_mid"] is None or rk["source"][idx] != "m2":
        return None
    om = rk["origin_month"]
    y, mo = int(om[:4]), int(om[5:7])
    path = []
    for j in range(rk["gw_paths"][50].shape[1]):
        m = mo - 1 + j + 1
        path.append({"month": f"{y + m // 12}-{m % 12 + 1:02d}",
                     **{f"p{p}": clean(rk["gw_paths"][p][idx, j]) for p in (10, 50, 90)}})
    return {"days_low": clean(rk["days_low"][idx]), "days_mid": clean(rk["days_mid"][idx]),
            "days_high": clean(rk["days_high"][idx]), "threshold_m": clean(rk["gw_threshold_m"][idx]),
            "anom_now_m": clean(rk["gw_anom_now_m"][idx]), "origin_month": om, "path": path,
            "drivers": rk["drivers"][idx], "horizon_days": 183,
            "meaning": "days until the taluk's groundwater reaches its worst-10% level (stress); 366 = not within 6 months. "
                       "Driver metres = how much deeper groundwater will be in 3 months because of that factor."}


@router.get("/backtest")
def api_backtest(as_of: str | None = None, idx: int | None = None):
    """Time Machine: the forecast made on as_of vs what the wells showed afterwards (statewide; one taluk if idx)."""
    from .gwmodel import backtest
    as_of = clamp_date(as_of)
    b = backtest(as_of)
    if b is None or not b["available"]:
        return {"as_of": as_of, "available": False, "mode": b and b["mode"],
                "message": "No later well readings yet to compare with (pick an earlier date)."}
    out = {"as_of": as_of, "available": True, "origin_month": b["origin_month"], "mode": b["mode"],
           "by_horizon": [{**r, **{k: round(r[k], 2) for k in ("mae_model", "mae_no_change", "covered")}}
                          for r in b["by_horizon"]], "stress": b["stress"]}
    if idx is not None:
        taluk(idx)
        y, mo = int(b["origin_month"][:4]), int(b["origin_month"][5:7])
        out["taluk"] = {"idx": idx, "threshold_m": clean(b["threshold"][idx]), "now_m": clean(b["now"][idx]), "path": [
            {"month": f"{y + (mo - 1 + h) // 12}-{(mo - 1 + h) % 12 + 1:02d}",
             **{f"p{p}": clean(b["paths"][p][idx, h - 1]) for p in (10, 50, 90)},
             "actual": clean(b["actual"][h][idx]) if h in b["actual"] else None} for h in range(1, 7)]}
    return out


class TalukChatIn(BaseModel):
    idx: int
    as_of: str | None = None
    lang: str = "en"
    platform: str = "agri"
    messages: list[dict]


@router.post("/chat")
def api_chat(body: TalukChatIn):
    """JalaMitra for a taluk (Bengaluru wards use /api/chat). Claude if a key is set, else built-in EN/KN answers."""
    import chat
    if not body.messages or body.messages[-1].get("role") != "user":
        raise HTTPException(400, "last message must be from the user")
    t = api_taluk(body.idx, body.as_of)
    ctx = {k: t[k] for k in ("name", "district", "risk", "source", "forecast", "indicators")}
    if ctx["forecast"]:
        ctx["forecast"] = {k: ctx["forecast"][k] for k in
                           ("days_low", "days_mid", "days_high", "threshold_m", "anom_now_m", "drivers")}
    return chat.reply_taluk(ctx, t["as_of"], "kn" if body.lang == "kn" else "en", body.platform, body.messages)


@router.get("/model-card")
def model_card():
    import json

    from .gwmodel import MODELS, card
    blr = MODELS / "bengaluru_validation.json"
    b = json.loads(blr.read_text())["current_params"] if blr.exists() else None
    m3 = MODELS / "m3_card.json"
    from .reservoir_model import card as m4_card
    return {"m2": card(), "m1": {"status": "waiting for genuine drought-declaration labels"},
            "m3": json.loads(m3.read_text()) if m3.exists() else None, "m4": m4_card(),
            "m5": {"status": "estimated, physically based (no public metered demand to train on)"},
            "m6": {"status": "tested on synthetic meters with planted leaks (no public meter data); see /api/urban/leaks/demo"},
            "m7": {"status": "transparent score from KIADB land x M2 x M4 (no public disruption records to train on)"},
            "bengaluru_wards": {"rain": "IMD rain-gauge grid (QC-filled), was ERA5", "wells_checked": b and b["all"]["wells"],
                                "r_2015_2021": b and b["train"]["median_r"], "r_2022_on": b and b["test"]["median_r"],
                                "note": "median correlation between the ward model's simulated groundwater and real NWDP "
                                        "wells in/near the city (monthly anomalies)"}}


@router.get("/taluk/{idx}")
def api_taluk(idx: int, as_of: str | None = None):
    as_of = clamp_date(as_of)
    t = taluk(idx)
    ind = taluk_indicators(as_of)
    rk = taluk_risk(as_of)
    score, levels = rk["score"], rk["levels"]
    g = groundwater()
    hist = [{"month": m, "depth": clean(g.depth[k, idx]), "anom": clean(g.anom[k, idx]), "wells": int(g.wells[k, idx])}
            for k, m in enumerate(g.months) if "2014-01" <= m <= last_complete_month(as_of)]
    return {**t, "as_of": as_of, "model": rk["model"], "risk": levels[idx], "stress": clean(score[idx]),
            "source": rk["source"][idx], "forecast": forecast_for(rk, idx, as_of),
            "indicators": {k: clean(v[idx]) for k, v in ind.items()}, "groundwater_history": hist}
