# Pravaah - Error 404 - Laasya Deepak, Niharika Singh, Keerthi Virupapura, K Mahalakshmi, Jyothsna Sivakumar


# Pravaah: water scarcity forecasting for Karnataka

Pravaah forecasts how many days each of Karnataka's **227 taluks** and Bengaluru's **243 wards** have before
groundwater reaches stress, and explains why. It is built on public government records (rain gauges, monitoring
wells, reservoirs) and serves three groups through separate platforms: **farmers**, **urban residents** and
**industry**. The whole site works in **English and Kannada**. Every number is labelled real, estimated or simulated,
and every model shows how it scored on years it never saw.

SDG 11 (Sustainable Cities and Communities)
SDG 12 (Responsible Consumption and Production)
SDG 13 (Climate Action)
. A short feature summary is in [FEATURES.md](FEATURES.md).

---

## Features

### Agriculture and Farmers (`/agri`)
- **Taluk risk map** with six layers: risk zones, kharif drought alert (M1), water scarcity heatmap, rain in the last
  3 months, season water balance (rain minus evaporation), groundwater vs normal (with the month of the readings).
- **Groundwater forecast per taluk (M2):** days until stress as a likely value and a dry-year / wet-year range, a
  6-month chart against the stress line, and a plain-language "Why this number?" box with the main drivers.
- **Kharif drought early warning (M1):** drought likely / watch / no alert from 1 July to 30 September, the chance the
  season ends in drought, the Drought Manual trigger evidence (rain deficit, dry spell, soil moisture) and whether the
  taluk was officially declared.
- **Crop advisor (M3):** crops for the current season ranked by water need and rainfed yield loss (typical and dry
  year), an irrigation schedule and a sowing-date planner.
- **State summary:** how many taluks are likely to reach stress within 6 months and the most urgent ones.

### Urban Population (`/urban`, `/urban/bengaluru`)
- **Ward-level Bengaluru inside the state map:** zoom in to all 243 wards with their own forecast and reasons.
- **Cauvery supply outlook (M4):** combined storage of KRS, Kabini, Harangi and Hemavathy with a 6-month forecast range.
- **Demand and tankers (M5, estimated):** city and ward demand, piped vs borewell share, wards that will need tankers.
- **Leak detection (M6):** night-flow rule plus anomaly detection on meter readings; demo on synthetic meters, CSV upload.
- **Full Bengaluru app** (`/urban/bengaluru`): city overview, "My Area" in plain words, an officials view with
  rankings and an intervention planner (rainwater harvesting, recharge, leak repair, Cauvery connections), and the
  Time Machine for the 2024 crisis.

### Industries and Businesses (`/industry`)
- **Factory site check:** pick any point in Karnataka (map click or coordinates) and enter the daily water need. You
  get a verdict (feasible / feasible with conditions / risky / not recommended), a 0-100 score with the reason for each
  part, and the statistics behind it:
  - official groundwater status from the CGWB 2023 assessment, share already pumped and water still available;
  - M2 forecast for the taluk and monitoring wells within 10 km (depth, 3-year trend, 10-year change);
  - reservoir system serving the district, current storage and chance of low storage (M4);
  - normal rain, last 12 months, year-to-year variability, past drought years, evaporation and peak heat;
  - savings from recycling and rainwater harvesting, other industrial demand nearby, and what to do next.
- **District disruption risk (M7):** share of industrial output at risk in the next 6 months per district, water at
  risk and reuse potential, from KIADB industrial land, M2 and M4.

### On every platform
- **Kannada / English** switch for the whole site, including the chatbot.
- **JalaMitra chatbot:** an AI assistant (Google Gemini, free tier) that answers questions about the selected taluk or
  ward using its forecast numbers, in English or Kannada, and understands Kannada typed in English letters. When no
  key is set or the free limit is reached, a built-in engine answers from the same data.
- **Time Machine:** pick any past date; the forecast uses only data available on that date, then compares it with what
  the wells actually showed.
- **Timeline with play button**, story dates (2023 drought, March 2024 crisis, 2022 wet year) and a **guided tour**.
- **Model card** with every model's test result, and shareable links (`?as_of=`, `?taluk=`, `?layer=`, `?lang=kn`).

---

## Models

| Model | What it predicts | Method | How it was tested |
|---|---|---|---|
| **M1** kharif drought | Drought likely / watch / no alert per taluk | Drought Manual-style labels from real data + monotonic gradient boosting | Against the official 2023 drought order and the 2026 list |
| **M2** groundwater | Days until each taluk reaches its stress level, with a range | Well-level quantile gradient boosting, future rain replayed from past years | Trained to 2021, scored on 2022-26 against real wells |
| **M3** crop water | Crop water stress, rainfed yield loss, irrigation need | FAO-56 soil water balance + FAO-33 yield response | Against real 2024-25 district yields (DES) |
| **M4** reservoirs | Dam storage up to 6 months ahead | Quantile gradient boosting with catchment rain | Trained to 2021, scored on 2022+ |
| **M5** urban demand | Demand, supply gap, tanker need | Physically based estimate | No metered data exists (labelled estimated) |
| **M6** leaks | Leaks and abnormal use on meters | Night-minimum rule + Isolation Forest | Synthetic meters with planted leaks |
| **M7** industry | Industrial output at risk per district | Transparent score from KIADB land, M2, M4 | No public disruption records exist |
| **Bengaluru wards** | Days to shortage for each ward | Daily groundwater balance per ward, 30 rain scenarios | Compared with real wells in and near the city |

Explanations are counterfactual: each driver is reset to normal and the forecast re-run, so "1.0 m deeper because of
low rain" means exactly that. No forecast uses data from after its as-of date.

## Data

| Data | Status | Source |
|---|---|---|
| Daily rain 2014 to today | real | IMD 0.25° gauge grid (quality-checked); ERA5 after IMD's last published year |
| Evaporation (ET0), temperature | real (reanalysis) | ERA5 via Open-Meteo |
| Groundwater, 2,664 wells, monthly | real | NWDP (Karnataka Ground Water Directorate); placeholder values removed |
| Reservoir storage, 34 dams, daily | real | NWDP / Karnataka Water Resources Dept |
| Minor-irrigation tanks | real | NWDP |
| Groundwater extraction per taluk | real | CGWB + KGWD Dynamic Ground Water Resources 2023 |
| Drought declarations | real | Govt. of Karnataka order of 13 Sept 2023 (via NGT filing), later 2023 and 2026 lists from news |
| Industrial land per district | real | KIADB |
| Crop yields 2024-25 | real | Directorate of Economics and Statistics |
| Boundaries | real | LGD taluks / districts; BBMP wards (datameet) |
| Urban demand, pipe coverage, industrial water norms | estimated | Census-based and planning norms |
| Daily ward groundwater between readings, leak test meters | simulated | Model output / synthetic test data |

---

## Run it locally

```bash
# backend (Python 3.11+; the team uses 3.14)
cd backend
python -m venv .venv
.venv\Scripts\activate             # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt     # requirements-train.txt to retrain models
uvicorn main:app --port 8000        # http://localhost:8000 serves the API and the built site

# frontend development (optional)
cd frontend
npm install
npm run dev                         # http://localhost:5173, proxies /api to :8000
npm run build                       # so :8000 serves the new version
```

Before every push: `backend\.venv\Scripts\python scripts\check.py` must print `PASS`.

### Turn on the AI chatbot (free)
1. Get a free key at [Google AI Studio](https://aistudio.google.com/apikey) (no card needed).
2. Copy `backend/.env.example` to `backend/.env` and paste the key after `GEMINI_API_KEY=`.
3. Restart the server. `.env` is git-ignored: never commit it or paste the key anywhere public.

Optional: `GEMINI_MODELS` sets the models to try in order. On the free tier Google may use chat text to improve its
products, so users should not type personal information.

### Retrain the models
```bash
cd backend
python train/fetch_karnataka.py all        # boundaries, IMD rain, ERA5
python train/fetch_nwdp.py && python train/clean_nwdp.py
python train/clean_gwra.py                 # CGWB groundwater assessment
python train/clean_drought_official.py     # official drought lists
python train/train_gw.py && python train/precompute_gw.py && python train/precompute_backtest.py
python train/train_drought.py
python train/train_reservoir.py
python train/validate_crops.py && python train/validate_bengaluru.py
```

## Demo links
- Agriculture in the 2023 drought, drought layer: `/agri?as_of=2023-09-01&taluk=210&layer=drought`
- Groundwater layer at the 2024 crisis: `/agri?as_of=2024-03-01&layer=groundwater`
- Factory site check in Kolar: `/industry?as_of=2024-03-01&site=13.14,78.05&kld=2000`
- Bengaluru wards: `/urban?zoom=blr&as_of=2024-03-01`
- Bengaluru app, guided tour: `/urban/bengaluru?tour=0`
- Any page in Kannada: add `&lang=kn`

## Deploy on Vercel
The repo is set up for Vercel: the React site is static and the FastAPI backend runs as a Python function
(`api/index.py`, configured in `vercel.json`).
1. On vercel.com: **Add New, Project, Import** this repo, keep the root directory `/`, and deploy.
2. Under **Settings, Environment Variables**, add `GEMINI_API_KEY` for the chatbot, then redeploy.
3. Before launch: connect the custom domain under **Settings, Domains**.

## Project layout
```
backend/
  main.py            FastAPI app (Bengaluru ward model + platform routers)
  chat.py            JalaMitra (Gemini / built-in EN-KN answers)
  core/              shared data, M1 drought, M2 groundwater, M4 reservoirs, /api/core
  usecases/          agri (M3), urban (M5, M6), industry (M7, site check)
  train/             data cleaning and training scripts
  models/            trained models and model cards
  data/              cleaned data (raw downloads are not committed)
frontend/src/
  platforms/         agri, urban, industry pages
  shared/            map, layers, shell, chatbot, Time Machine, tour, icons
api/index.py         Vercel entry point
scripts/check.py     end-to-end check run before every push
```

Team rules for people and AI agents working on this repo: [AGENTS.md](AGENTS.md). Plan and progress log: [PLAN.md](PLAN.md).

## Limits we state openly
- Urban demand, pipe coverage and industrial water norms are estimates; leak detection is tested on synthetic meters.
- M1 cannot separate severe from moderate drought (the official decision also uses crop-loss surveys it cannot see).
- The newest well readings arrive over several months, so the map uses the latest month most wells have reported.
- Forecasts are screening tools, not permits or official declarations.
