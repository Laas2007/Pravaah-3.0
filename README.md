# Pravaah – ward-level water scarcity prediction (Bengaluru)

SDG 6 (Clean Water & Sanitation). Predicts, for each of Bengaluru's 243 BBMP wards, **in how many days
(as a range) a water shortage is expected, and why**. The app has a risk map, a citizen view, an official
view with an intervention planner, a 2024-crisis backtest, and an English/Kannada chatbot.

## Run it

```bash
# 1. backend (Python 3.11+)
cd backend
python -m venv .venv
.venv\Scripts\activate            # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
python fetch_data.py               # optional: refresh rainfall data (already included)
uvicorn main:app --port 8000

# 2. open http://localhost:8000   (serves the built frontend)
```

For frontend development, run `cd frontend && npm install && npm run dev` and open http://localhost:5173.
After changing the frontend, rebuild it with `npm run build` so `:8000` serves the new version.

**AI chatbot:** set `ANTHROPIC_API_KEY` before starting uvicorn (model: Claude Haiku 4.5; change it with
`CHAT_MODEL`). Without a key, a built-in engine answers in EN/KN from the ward's own prediction.

**Demo links:**
- Guided tour of all features: `http://localhost:8000/?tour=0` (or click **▶ Take the tour**)
- Heatmap during the 2024 crisis: `http://localhost:8000/?layer=heat&as_of=2024-03-01`
- Citizen: `http://localhost:8000/?view=area&ward=Whitefield&as_of=2024-01-01` (add `&lang=kn` for Kannada)
- Official: `http://localhost:8000/?view=official&ward=Whitefield&as_of=2024-01-01`
- Time Machine: `http://localhost:8000/?view=backtest&ward=Whitefield&as_of=2023-12-01&layer=heat`

## How the model works (explainable by design)

Each ward has a groundwater store, updated daily:

```
groundwater += rain recharge − borewell draw + pipe-leak seepage + lateral inflow from the regional aquifer
borewell draw = demand − Cauvery piped supply
```

- **Shortage** = groundwater falls below 30% of usable storage (borewells start failing).
- **Forecast range**: the model is re-run from today once for every past rainfall year × 3 demand
  scenarios (≈30 runs). The range shown is the 25th–75th percentile of "days until shortage".
- **Why**: each driver (rain deficit, borewell dependence, density, commercial load, Cauvery catchment
  deficit, paved surfaces) is reset to the city-typical value and the forecast is re-run. The change in
  days is that driver's contribution (counterfactual attribution, no black box).
- **Backtest**: the model only sees data available on the as-of date, and future-rain scenarios only use
  earlier years.

## Data: what's real and what's estimated

| Input | Status | Source |
|---|---|---|
| Ward boundaries (243) | real | BBMP via datameet/Municipal_Spatial_Data |
| Daily rainfall 2014–now, 16 grid points over the city | real | ERA5 reanalysis via Open-Meteo archive |
| Cauvery catchment rainfall (Kodagu→KRS, Wayanad→Kabini) | real | ERA5 via Open-Meteo |
| Stage V Cauvery commissioning (Oct 2024) | real event | public announcements |
| Ward population | estimated | 2011 census ÷ 243 (delimitation basis) × distance-based growth |
| Cauvery pipe coverage per ward | estimated | higher in the core, lower in the 110 villages merged in 2007 |
| IT/industrial load | estimated | named wards (Whitefield, Peenya, Bellandur…) |
| Groundwater level | simulated | calibrated so ~2–5% of wards are short in normal years and ~30–37% in Mar–Apr 2024 |

**Next steps (24-hour build):** plug in CGWB/KSNDMC well levels to calibrate each ward, BWSSB supply data,
KSNDMC hobli rainfall, and the KRS/Kabini reservoir storage series.

**Before the pitch:** cite a specific news article for the reference date "early March 2024 crisis peak"
used in the backtest (`CRISIS_2024` in `backend/main.py`).

## Deploy on Vercel

The repo is ready for Vercel: the React app is served as a static site and the FastAPI model runs as a
Python serverless function (`api/index.py`, configured in `vercel.json`).

1. On vercel.com: **Add New → Project → Import** this GitHub repo. Keep the root directory as `/`
   (the build settings come from `vercel.json`) and click **Deploy**.
2. Optional: under **Settings → Environment Variables** add `ANTHROPIC_API_KEY` to switch the chatbot to Claude, then redeploy.
