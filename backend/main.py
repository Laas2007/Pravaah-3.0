"""Pravaah API.  Run:  uvicorn main:app --reload --port 8000"""
import datetime as dt
import json
import tempfile
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

import chat
from content import DRIVER, RISK, actions_for
from model import FACTORS, Intervention, load_world, predict, risk_level, simulate_history, ward_timeseries

app = FastAPI(title="Pravaah – Water Scarcity Prediction Portal")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

# Karnataka platforms (PLAN.md §3). One line per platform; each module owns its own /api/<name>/* routes.
from core.router import router as core_router  # noqa: E402
from usecases import agri, industry, urban  # noqa: E402

for r in (core_router, agri.router, urban.router, industry.router):
    app.include_router(r)

# Backtest results are cached as JSON. The bundled copy in data/cache is read-only on
# serverless hosts (e.g. Vercel), so new results fall back to the temp directory.
BUNDLED_CACHE = Path(__file__).parent / "data" / "cache"


def _cache_dir() -> Path:
    for d in (BUNDLED_CACHE, Path(tempfile.gettempdir()) / "pravaah-cache"):
        try:
            d.mkdir(parents=True, exist_ok=True)
            probe = d / ".write-test"
            probe.write_text("ok")
            probe.unlink()
            return d
        except OSError:
            continue
    return BUNDLED_CACHE

# Public reference point for the 2024 backtest. Media reports put the peak of
# the crisis (widespread dry borewells, tanker shortages and price spikes in
# Whitefield, Mahadevapura, RR Nagar, Bommanahalli etc.) in early March 2024.
CRISIS_2024 = {
    "date": "2024-03-01",
    "label": "Bengaluru water crisis peaks: borewells run dry, tanker shortages (media reports, early Mar 2024)",
}


def _clamp_date(s: str | None) -> str:
    w = load_world()
    if not s:
        return w.dates[-1]
    try:
        d = dt.date.fromisoformat(s)
    except ValueError:
        raise HTTPException(400, "date must be YYYY-MM-DD")
    lo = dt.date.fromisoformat(w.dates[0]) + dt.timedelta(days=365)
    hi = dt.date.fromisoformat(w.dates[-1])
    return min(max(d, lo), hi).isoformat()


@app.get("/api/meta")
def meta():
    w = load_world()
    return {
        "data_from": w.dates[0],
        "data_until": w.dates[-1],
        "min_as_of": (dt.date.fromisoformat(w.dates[0]) + dt.timedelta(days=365)).isoformat(),
        "ward_count": len(w.names),
        "factors": FACTORS,
        "driver_labels": DRIVER,
        "risk_labels": RISK,
        "crisis_2024": CRISIS_2024,
        "presets": [
            {"label": "Latest data", "date": w.dates[-1]},
            {"label": "1 Jan 2024 (before the crisis)", "date": "2024-01-01"},
            {"label": "1 Jan 2023 (normal year)", "date": "2023-01-01"},
        ],
    }


@lru_cache(maxsize=1)
def _geojson_bytes():
    w = load_world()
    feats = []
    for i, f in enumerate(w.geojson["features"]):
        # round coordinates to ~1 m to shrink the payload
        def rnd(c):
            return [rnd(x) for x in c] if isinstance(c[0], list) else [round(c[0], 5), round(c[1], 5)]
        feats.append({"type": "Feature", "properties": {"idx": i, "name": w.names[i], "ward_no": w.ids[i]},
                      "geometry": {"type": f["geometry"]["type"], "coordinates": rnd(f["geometry"]["coordinates"])}})
    return json.dumps({"type": "FeatureCollection", "features": feats}, separators=(",", ":")).encode()


@app.get("/api/wards.geojson")
def wards_geojson():
    return Response(_geojson_bytes(), media_type="application/geo+json")


@app.get("/api/predict")
def api_predict(as_of: str | None = None):
    """All wards for a date (no explanations; fast enough for a slider)."""
    r = predict(_clamp_date(as_of), Intervention(), False)
    return {**r, "wards": [{k: v for k, v in x.items() if k != "drivers"} for x in r["wards"]]}


def _ward(idx: int, as_of: str):
    r = predict(as_of, Intervention(), True)
    if not 0 <= idx < len(r["wards"]):
        raise HTTPException(404, "unknown ward")
    return r, r["wards"][idx]


@app.get("/api/ward/{idx}")
def api_ward(idx: int, as_of: str | None = None):
    as_of = _clamp_date(as_of)
    r, x = _ward(idx, as_of)
    ranked = sorted(r["wards"], key=lambda y: (y["days_mid"], y["groundwater_pct"]))
    return {
        **x,
        "as_of": r["as_of"],
        "rank": next(k for k, y in enumerate(ranked) if y["idx"] == idx) + 1,
        "of": len(ranked),
        "actions": actions_for(x["drivers"]),
        "timeseries": ward_timeseries(idx, r["as_of"]),
    }


@app.get("/api/explanations")
def api_explanations(as_of: str | None = None):
    """All wards with driver attributions (official view ranking table)."""
    return predict(_clamp_date(as_of), Intervention(), True)


class InterventionIn(BaseModel):
    as_of: str | None = None
    idx: int
    extra_piped: float = 0.0
    rwh_boost: float = 0.0
    demand_cut: float = 0.0
    tanker_mld: float = 0.0


@app.post("/api/intervene")
def api_intervene(body: InterventionIn):
    as_of = _clamp_date(body.as_of)
    iv = Intervention(round(min(max(body.extra_piped, 0), 0.8), 2), round(min(max(body.rwh_boost, 0), 3), 2),
                      round(min(max(body.demand_cut, 0), 0.5), 2), round(min(max(body.tanker_mld, 0), 20), 1))
    base = predict(as_of, Intervention(), False)["wards"][body.idx]
    new = predict(as_of, iv, False)["wards"][body.idx]
    keys = ("days_low", "days_mid", "days_high", "risk")
    return {"before": {k: base[k] for k in keys}, "after": {k: new[k] for k in keys}}


@app.get("/api/backtest")
def api_backtest(start: str = "2023-09-01", end: str = "2024-04-30", step: int = 7):
    """Re-run the model weekly as if it were each date, using only data available then."""
    start, end = _clamp_date(start), _clamp_date(end)
    step = max(step, 7)
    name = f"backtest_{start}_{end}_{step}.json"
    for d in (BUNDLED_CACHE, Path(tempfile.gettempdir()) / "pravaah-cache"):
        if (d / name).exists():
            return json.loads((d / name).read_text())
    key = _cache_dir() / name
    w = load_world()
    d, stop = dt.date.fromisoformat(start), dt.date.fromisoformat(end)
    if (stop - d).days > 400:
        raise HTTPException(400, "backtest window limited to ~13 months")
    runs = []
    while d <= stop:
        r = predict(d.isoformat(), Intervention(), False)
        runs.append({"as_of": r["as_of"], "days": [x["days_mid"] for x in r["wards"]],
                     "low": [x["days_low"] for x in r["wards"]], "high": [x["days_high"] for x in r["wards"]]})
        d += dt.timedelta(days=step)

    hist = simulate_history()
    from model import Params
    p = Params()
    thresh = p.shortage_frac * p.capacity_mm
    i0 = w.dates.index(runs[0]["as_of"])
    wards = []
    for i, name in enumerate(w.names):
        flag = next((r for r in runs if risk_level(r["days"][i]) in ("high", "critical")), None)
        onset = next((w.dates[t] for t in range(i0, len(w.dates)) if hist[t, i] < thresh), None)
        wards.append({
            "idx": i, "name": name,
            "flag_date": flag["as_of"] if flag else None,
            "flag_pred_days": [flag["low"][i], flag["high"][i]] if flag else None,
            "sim_onset": onset,
        })
    out = {
        "start": start, "end": end, "step": step,
        "dates": [r["as_of"] for r in runs],
        "high_or_critical_count": [sum(risk_level(v) in ("high", "critical") for v in r["days"]) for r in runs],
        "runs": runs,
        "wards": wards,
        "reference": CRISIS_2024 if start <= CRISIS_2024["date"] <= end else None,
    }
    key.write_text(json.dumps(out))
    return out


class ChatIn(BaseModel):
    idx: int
    as_of: str | None = None
    lang: str = "en"
    messages: list[dict]


@app.post("/api/chat")
def api_chat(body: ChatIn):
    if not body.messages or body.messages[-1].get("role") != "user":
        raise HTTPException(400, "last message must be from the user")
    as_of = _clamp_date(body.as_of)
    _, x = _ward(body.idx, as_of)
    return chat.reply(x, as_of, "kn" if body.lang == "kn" else "en", body.messages)


# Serve the built React app (frontend/dist) from the same server for demos.
DIST = Path(__file__).parent.parent / "frontend" / "dist"
if DIST.exists():
    app.mount("/assets", StaticFiles(directory=DIST / "assets"), name="assets")

    @app.get("/{path:path}")
    def spa(path: str):
        if path.startswith("api/"):  # unknown API route: a real 404, not the HTML page
            raise HTTPException(404, "unknown API route")
        f = DIST / path
        return FileResponse(f if path and f.is_file() else DIST / "index.html")
