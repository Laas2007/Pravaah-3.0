# Pravaah Karnataka – 24-hour hackathon build plan

> **For a new Claude/AI session:** read this file first, then `README.md`. We extended the original Bengaluru-only
> app to all of Karnataka with an ML backbone and **3 use-case platforms** (scope changed on 2026-10-24 from 5 to 3).
> Check the **Progress log** (§10) to see what's done, and update it as you go.

---

## 1. Goal (one sentence)

One Karnataka-wide water-scarcity engine (shared data + ML models), exposed through **3 platforms**:
🌾 **Agriculture & Farmers** · 🏙️ **Urban Population** · 🏭 **Industries & Businesses**, reached from one landing page.

Government and Reservoir platforms were **dropped** (2026-10-24). Their data stays as **model input**:
reservoir storage feeds Urban (Cauvery supply to Bengaluru), Agriculture (canal irrigation) and Industry
(surface-water supply); groundwater wells and drought declarations feed all three.

**Demo storyline:** *the 2023 Karnataka drought → 2024 Bengaluru crisis.* In 2023 most taluks were declared
drought-hit, KRS/Kabini storage collapsed, and by March 2024 Bengaluru's borewells ran dry. All 3 platforms share one
date selector, so judges can set it to "Aug 2023" and see each platform warn *before* the crisis (only data available
on that date is used, so the model never sees the future).

---

## 2. Starting point (what already existed)

| Piece | File | Reuse it for |
|---|---|---|
| Daily groundwater balance per ward, ensemble of past rainfall years → "days until shortage" range (25–75th pct) | `backend/model.py` | Urban (Bengaluru) as-is; generalise to taluks; **ensemble-of-past-years** trick reused for sowing dates and storage fans |
| Counterfactual "why" (reset a driver to typical, re-run, Δdays) | `backend/model.py` `predict()` | Same explanation method on top of any ML model (set feature to median → re-predict) |
| Backtest with no look-ahead | `backend/main.py` `/api/backtest` | 2023 drought backtests |
| EN/KN chatbot (Claude or built-in fallback) | `backend/chat.py`, `content.py` | Agri (farmer, Kannada) and Urban assistants |
| React + Leaflet map, charts, tour, i18n | `frontend/src/*` | Bengaluru app at `/urban/bengaluru`; shared components |

---

## 3. Architecture

```
                ┌──────────── Landing page  /  ────────────┐
                │  Karnataka risk map + 3 platform cards   │
                └──────┬───────────────┬───────────────┬───┘
                    /agri           /urban          /industry        ← frontend/src/platforms/{agri,urban,industry}
                       │       (/urban/bengaluru = ward model)
                 /api/agri/*      /api/urban/*    /api/industry/*     ← backend/usecases/{agri,urban,industry}.py
                       └───────────────┼───────────────┘
                                       ▼
        backend/core/  data · indicators · reservoirs · router (/api/core/*)  [+ ml, waterbalance, features: TODO]
                                       ▼
        backend/data/karnataka/  (precomputed JSON/NPZ)        backend/models/*.joblib (TODO)
```

### Key design decisions

1. **Spatial unit = taluk:** 227 taluks (LGD 2018 boundaries) in 31 districts. Bengaluru also has 243 wards.
2. **Region IDs:** `KA-<district-slug>-<taluk-slug>` (e.g. `KA-kolar-mulbagal`) + array index `idx`, see `data/karnataka/regions.json`.
3. **ML = hybrid, explainable (physics + ML):**
   - Physics (groundwater bucket, FAO-56 crop water use, reservoir mass balance) produces features and fills gaps.
   - ML (scikit-learn `HistGradientBoosting*`) is trained **only where we have real labels**.
   - Ranges from **quantile regression** (α = 0.25/0.5/0.75) or the past-years ensemble.
   - "Why" = counterfactual method + permutation importance. No black box.
4. **Precompute, don't compute live.** Training scripts write `data/karnataka/*` and `models/*.joblib`; the API
   serves lookups plus light what-ifs (keeps Vercel fast and inside its size limit).
5. **Libraries:** runtime `backend/requirements.txt`; offline `backend/requirements-train.txt` (shapely, pandas,
   scikit-learn, joblib, openpyxl, pdfplumber). Frontend uses `react-router-dom`.
6. **Parallel-safe layout:** each platform owns `backend/usecases/<x>.py` + `frontend/src/platforms/<x>/`.
   Platforms import from `core/` only, never from each other. Shared files get one-line additions.

### Folder layout (current)

```
backend/
  main.py                     # original Bengaluru API + one include_router line per platform
  model.py chat.py content.py # Bengaluru ward model + chatbot (used by /urban/bengaluru)
  core/
    data.py                   # cached loaders: regions, climate, groundwater, reservoirs, tanks, clamp_date
    indicators.py             # rain vs normal, groundwater now, provisional_risk (stand-in for ML)
    reservoirs.py             # storage on a date, normal for that day, combined series (Cauvery dams)
    router.py                 # /api/core/meta, regions, taluks.geojson, districts.geojson, indicators, taluk/{idx}
  usecases/  agri.py  urban.py  industry.py
  train/
    fetch_karnataka.py        # boundaries + IMD rain + ERA5 ET0/temp -> climate.npz
    fetch_nwdp.py clean_nwdp.py   # groundwater wells, reservoirs, tanks (NWDP)
  data/karnataka/  data/raw/  data/_downloads/ (git-ignored)
frontend/src/
  App.jsx                     # router: / · /agri · /urban · /urban/bengaluru · /industry (old /?view= links redirect)
  Landing.jsx
  platforms/agri/  platforms/urban/ (index.jsx + BengaluruApp.jsx)  platforms/industry/
  shared/  PlatformShell · KarnatakaMap · TalukDetail · hooks (useAsOf, useLoad) · ui · platforms.js · platform.css
```

### API contract
Every platform response includes `as_of`, a `risk` on the shared 4-level scale (`critical|high|medium|low`), and
`model` (`"provisional-index"` until the trained models replace it). Placeholder data is flagged `mock: true` and
shown with a yellow "Placeholder data" banner in the UI.

---

## 4. Data sources

| Data | Source | Used by | Status |
|---|---|---|---|
| **Daily rain** 2014→2025 | **IMD gridded rainfall 0.25°** (rain gauges), imdpune.gov.in | all | ✅ `climate.npz` |
| Daily rain 2026 (not yet in IMD) | ERA5 (Open-Meteo), bias-corrected per taluk × month vs IMD | all | ✅ |
| ET0 (FAO), Tmax/Tmin | ERA5 via Open-Meteo archive | agri (crop water), urban (demand) | ✅ (75/95 grid points, see §10) |
| Expected rainfall | Open-Meteo 16-day + seasonal forecast; else past-years ensemble | agri | TODO |
| Taluk / district boundaries | geoBoundaries IND ADM3 2018 (LGD); datta07 districts + Vijayanagara | all | ✅ |
| **Groundwater levels**, monthly, 2,701 wells, 1971→2026 | **NWDP** (nwdp.nwic.gov.in) | all (core ML label) | ✅ `gw_taluk.npz` |
| **Reservoir daily storage/inflow/outflow**, 1990→2026 | **NWDP** | urban (Cauvery), agri (canals), industry | ✅ `reservoirs.json` |
| Minor irrigation tanks (3,404) | NWDP | agri | ✅ `tanks_taluk.json` |
| River discharge daily | NWDP | (optional) inflow checks | downloaded, unused |
| **Drought-declared taluks by year** (labels) | Karnataka Revenue Dept / KSNDMC orders, news | agri M1 + backtest | ⏳ user → `data/raw/drought/` |
| **Crop area / production / yield** by district | ICRISAT DLD / data.gov.in | agri M3 | ⏳ user → `data/raw/crops/` |
| **KIADB industrial areas** | KIADB website | industry | ⏳ user → `data/raw/kiadb/` |
| CGWB assessment (stage of extraction) | INGRES | agri, industry | optional → `data/raw/cgwb/` |
| WRI Aqueduct baseline water stress | wri.org | industry | optional → `data/raw/aqueduct/` |
| Crop water needs / yield response | FAO-56 Kc, FAO-33 Ky tables | agri | type in |
| Crop calendar, soil water capacity | Raitamitra zones; ISRIC SoilGrids | agri | TODO |
| Population, city supply | Census 2011 (+ growth); KUWSDB/news | urban | estimated |
| Sector water intensity | CPCB / literature | industry | estimated |
| Household meter readings | **none public** → synthetic with planted leaks (say so) | urban M6 | TODO |

### 4a. Data reliability (agreed 2026-10-24)

ERA5 (reanalysis) gets wet vs dry years right but smooths extremes: Bengaluru 2017/2022 were record years of
~1,700 mm at the IMD station, but ERA5 says 965 / 1,113 mm. **Rules:** (1) rain from IMD gauges, ERA5 only for
ET0/temperature and bias-corrected current-year rain; (2) keep the ERA5-vs-IMD bias table (`rain_bias.json`) in the
model card; (3) **every platform shows a validation score against real past events**; (4) every number carries a
label: 🟢 real · 🟠 estimated · 🔵 simulated.

| Platform | 🟢 Real | 🟠 Estimated | 🔵 Simulated |
|---|---|---|---|
| 🌾 Agriculture | Rain, ET0, groundwater wells, reservoirs, tanks, drought list*, crop yields* | Soil water capacity, future rain | — |
| 🏙️ Urban | Rain, groundwater wells, Cauvery dam storage | Population today, city supply, pipe coverage, demand | Meter data (leaks), daily groundwater between readings |
| 🏭 Industry | Rain, groundwater wells, reservoirs, KIADB areas* | Water use per area (size × sector intensity) | — |

\* once the user's files arrive.

### 4b. Where data lives
- `backend/data/raw/<dataset>/`: hand-collected files (any format), see `data/raw/README.md`.
- `backend/data/_downloads/`: big auto-downloads (IMD binaries, India boundaries, NWDP CSVs). Git-ignored.
- `backend/data/karnataka/`: cleaned Karnataka outputs used by app + models. Committed.

---

## 5. ML models (the backbone)

| # | Model | Platform | Unit | Features | Label (real?) | Method | Output |
|---|---|---|---|---|---|---|---|
| M1 | **Agricultural drought classifier** | 🌾 (+ 🏭 location risk) | taluk × season | SPI-1/3/6, rain dev %, ET0 anomaly, groundwater anomaly (wells), tank storage, irrigated share | Drought declared (real, 2016/18/19/23) | `HistGradientBoostingClassifier`, leave-one-year-out | `drought_prob`, risk, drivers |
| M2 | **Groundwater days-to-shortage** | 🏙️ 🏭 🌾 | taluk (+ Bengaluru wards) | Water balance from `model.py`, generalised; calibrated to well levels | Well depth trajectories (real, NWDP) | Physics + quantile GBM residual + past-years ensemble | `days_low/mid/high` |
| M3 | **Crop yield-risk** | 🌾 | district × crop × year | Season rain, SPI, FAO-56 ET deficit, irrigation %, groundwater | Yield anomaly (real, ICRISAT) | Quantile `HistGradientBoostingRegressor` | yield loss % range per crop |
| M4 | **Reservoir storage forecast** | 🏙️ (Cauvery supply) 🏭 🌾 (canals) | reservoir × day | Storage today, catchment rain 7/30/90 d, day-of-year | Storage +30/60/90 d (real, NWDP 1990→) | Quantile GBM + past-years ensemble fan | months of supply left, P(below dead storage) |
| M5 | **Urban demand forecast** | 🏙️ | city/ward × day | Temperature, season, population, supply hours | Synthetic (state it) | GBM | demand MLD |
| M6 | **Leak / abnormal-use detection** | 🏙️ | meter × hour | Night-flow minimum, rolling z-score | Synthetic with planted leaks | IsolationForest + rule | alerts, precision/recall |
| M7 | **Industrial disruption risk** | 🏭 | industrial area | M2 days-to-shortage, M4 storage outlook, groundwater dependence, sector water intensity | No public label → transparent score, validated on 2023–24 (areas that had tanker/borewell stress) | Weighted score using M1/M2/M4 outputs | % output at risk, ₹ at risk |

**Validation to show judges:** M1 "as of 1 Aug 2023, which taluks did we flag vs the government declaration list"
(confusion matrix); M2 "predicted vs actual well-depth change 2023→2024"; M3/M4 leave-one-year-out error.
One "Model card" panel per platform.

---

## 6. The 3 platforms — scope by priority

**MUST** = ships in the demo. **SHOULD** = add if on schedule. **STRETCH** = roadmap slide.

### 🌾 Agriculture & Farmers — `/agri`
| Feature | Priority | How |
|---|---|---|
| Agricultural drought & crop water stress | MUST | M1 prob + daily FAO-56 soil water balance → stress days |
| Crop recommendation from water availability + expected rain | MUST | Available water = expected rain (ensemble) + soil AWC + irrigation (tanks/canal/groundwater); rank crops by FAO-56 need vs availability × M3 risk |
| Irrigation schedule & water requirement | MUST | FAO-56 Kc × ET0 daily bucket → "irrigate X mm on these dates", m³/acre |
| Groundwater depletion & agri water shortage | SHOULD | Well trend + M2 at taluk level |
| Sowing date planner & alternative crops | SHOULD | Bucket per candidate sowing week over every past rainfall year → P(stress) per week |
| Yield risk due to water scarcity | SHOULD | M3 range + FAO-33 Ky |
| Canal water outlook (reservoir command areas) | STRETCH | M4 for Tungabhadra / Bhadra / Almatti / KRS commands |
| Kannada farmer view + chatbot | STRETCH | `chat.py` with agri prompt |

### 🏙️ Urban Population — `/urban` (+ `/urban/bengaluru`)
| Feature | Priority | How |
|---|---|---|
| Ward shortage prediction & how long supply lasts (Bengaluru) | MUST | **Existing ward model** at `/urban/bengaluru` |
| Cauvery supply outlook for Bengaluru | MUST | Real storage now (built); M4 forecast → months of supply left |
| Other cities (Mysuru, Hubballi-Dharwad, Mangaluru, …) | MUST | City-level M2 with supply estimate |
| Areas needing tankers | MUST | Wards/cities with days_mid ≤ 30 → tanker MLD; ranked list + map layer |
| Household / apartment demand forecast | SHOULD | M5 + calculator (people, flats, garden) |
| Rainwater harvesting & conservation planner | SHOULD | Roof area × real rainfall × runoff coeff → litres/yr, days of supply covered |
| Abnormal consumption / leak detection | SHOULD | M6 on synthetic meters; "upload CSV" → flagged hours |

### 🏭 Industries & Businesses — `/industry`
| Feature | Priority | How |
|---|---|---|
| Location water-risk assessment | MUST | Click a point / pick a KIADB area → M1/M2 risk + reservoir dependence (+ Aqueduct) → score + report |
| Shortages affecting operations | MUST | M2 days-to-shortage per industrial area; timeline |
| Industrial water demand forecast | SHOULD | Sector intensity × size × growth |
| Production disruption estimate | SHOULD | M7: shortage days × groundwater dependence × water intensity → % output, ₹ at risk |
| Conservation & wastewater-reuse opportunities | SHOULD | Recyclable share (STP/ZLD) by sector → MLD saved, payback |

---

## 7. Team split

Decided 2026-10-24. Each person uses a different AI agent, so **`AGENTS.md` is the source of truth** for file
ownership, contracts and workflow (every agent reads it; `CLAUDE.md`, `GEMINI.md`, `.github/copilot-instructions.md`
point to it). `scripts/check.py` must PASS before every push.

| Person | Role | Main deliverables |
|---|---|---|
| P1 | Core data & ML | M1 drought classifier, M2 taluk days-to-shortage (calibrated to wells) behind `core.risk.taluk_risk()`; drought-list cleaning; model-card endpoint; ERA5 re-run |
| P2 | 🌾 Agriculture | FAO-56 soil water balance, crop ranking, irrigation schedule, sowing planner, M3 yield risk (crops data) |
| P3 | 🏙️ Urban + M4 | Bengaluru app upkeep, M4 reservoir forecast behind `core.reservoirs.forecast_storage()`, other cities, tankers, RWH, M5/M6 |
| P4 | 🏭 Industry | KIADB cleaning, location risk report, demand, M7 disruption, wastewater reuse |
| P5 | Integrator | Shared components, landing, design, Kannada, `scripts/check.py`, merges to `main`, Vercel deploy, README, pitch + video |

Dependencies: P2/P3/P4 build on the provisional `taluk_risk()` now and get M1/M2 automatically when P1 swaps the
inside. P4 uses P3's `forecast_storage()` and must handle `None` until M4 lands.

**Shared files rule:** `backend/main.py`, `App.jsx`, `api.js`, `requirements*.txt`, `package.json`: only add your one
line and push straight away; pull often. **Git:** branch per person, merge to `main` at each sync, `main` must always build.

### Timeline (24 h)

| Hours | Milestone |
|---|---|
| 0–1 | Kickoff, read this plan, branches. Skeleton is already on disk |
| 1–6 | Remaining data (drought list, crops, KIADB) cleaned → **Sync #1 (h6)** |
| 6–12 | Models M1/M2/M4 + real endpoints replacing mocks → **Sync #2 (h12):** each platform real end to end for 1 region |
| 12–16 | Staggered sleep shifts |
| 14–19 | SHOULD features, 2023 backtests, model cards → **Sync #3 (h19): feature freeze** |
| 19–22 | Bugs, Kannada labels, tours, deploy to Vercel |
| 22–24 | Pitch deck, 2-min demo video, rehearse the 2023→2024 story twice |

**Cut rules:** behind at Sync #2 → drop that platform's SHOULDs. A missing dataset never blocks more than 1 hour.

---

## 8. Gotchas

- **Vercel:** `vercel.json` already has the SPA rewrite. Keep heavy training out of the serverless path; commit precomputed outputs.
- **Unknown `/api/...` routes return 404** (`main.py` catch-all only serves the page for non-API paths).
- **Open-Meteo free daily limit** is easy to hit; finished chunks are cached, so just re-run the next day.
- **Groundwater noise:** taluks with few wells jump around; weight by `wells` in `gw_taluk.npz`.
- **Recharts + CSS variables:** pass real colours (`platform('x').color`) to chart strokes, not `var(--pc)`.
- **Windows venv:** `python -m venv` prints a launcher copy warning, but `.venv` works. Python 3.14 wheels OK.

---

## 9. Run commands

```bash
cd backend && .venv\Scripts\activate
pip install -r requirements-train.txt          # includes requirements.txt
uvicorn main:app --reload --port 8000           # http://localhost:8000 serves the built frontend
cd frontend && npm install && npm run dev       # http://localhost:5173 (proxies /api to :8000)
npm run build                                   # so :8000 serves the new UI

# data (re-runnable)
python train/fetch_karnataka.py all            # boundaries, IMD rain, ERA5, climate merge
python train/fetch_nwdp.py && python train/clean_nwdp.py
```

---

## 10. Progress log (update this as you go)

- [x] 2026-10-24 — Original Bengaluru app verified running locally; plan written.
- [x] 2026-10-24 — `backend/data/raw/` folders + README for hand-collected files; `requirements-train.txt`.
- [x] 2026-10-24 — Taluk boundaries: `taluks.geojson`, `districts.geojson`, `regions.json` (227 taluks, 31 districts).
- [x] 2026-10-24 — Climate `climate.npz`: daily rain/et0/tmax/tmin × 227 taluks, 2014-01-01 → 2026-10-18. Rain = IMD
      (area-weighted) until 2025-12-31, then bias-corrected ERA5. 7 IMD taluk-months that read ~0 while neighbours had
      rain were replaced (listed in `rain_bias.json`). ERA5 vs IMD: state-wide −6…+22 %, per district up to +39 %,
      Bengaluru 2022 ERA5 1,211 vs IMD 1,692 mm. IMD shows the droughts (2016: 831 mm, 2023: 885 mm vs ~1,300 normal).
- [ ] **ERA5 grid incomplete (75/95 points):** Open-Meteo daily limit. Northern taluks borrow the nearest point for
      ET0/temperature. Re-run `python train/fetch_karnataka.py era5 climate` on/after 2026-10-25.
- [x] 2026-10-24 — **NWDP data**: `gw_taluk.npz` (monthly depth + anomaly + well count per taluk, 2005-01 → 2026-10,
      2,701 wells, all 227 taluks covered; validated: Nov 2023 vs Nov 2022, 201/225 taluks deeper, median +2.9 m),
      `gw_wells.json`, `reservoirs.json` (35 dams, daily; KRS 1 Oct 2023 = 21 TMC vs ~48 normal; 1 Oct 2026 = 26 TMC),
      `tanks_taluk.json` (3,404 tanks, all matched). Groundwater levels and reservoir storage are now 🟢 real.
- [x] 2026-10-24 — **App skeleton** with real data where available (provisional risk = 0.35·12-month rain deficit +
      0.25·3-month deficit + 0.40·groundwater deeper than normal, stand-in until M1/M2).
- [x] 2026-10-24 — **Scope change 5 → 3 platforms.** Removed `/gov`, `/reservoir` (pages + routers). Reservoir helpers moved
      to `core/reservoirs.py`. Cities renamed **Urban** (`/urban`, `/api/urban/*`, `/urban/bengaluru`), with a new
      **Cauvery supply outlook** card (`/api/urban/cauvery`, KRS+Kabini+Harangi+Hemavathy; 1 Oct 2023: 59.9 vs 97.4 TMC
      normal, −39 %). Landing shows 3 cards. Verified: build OK, endpoints 200, removed API routes 404, screenshots OK.
      **Mock (labelled in UI):** crop ranking, city population/supply, industrial area list/demand.
- [x] 2026-10-24 — **Team split + AGENTS.md** (rules for 5 people with different AI agents), `core/risk.py`
      `taluk_risk()` contract, `core/reservoirs.forecast_storage()` stub (M4), `scripts/check.py`. Pushed to GitHub.
- [x] 2026-10-24 — **Drought file rejected as labels.** `data/raw/drought/karnataka_drought_taluks_detailed (1).xlsx`
      is not genuine: years are nested prefixes of one list in identical order (2019 ⊂ 2018 ⊂ 2016 ⊂ 2023), 2016
      contains taluks created in 2017–18, Koppa/Sringeri listed every year, 2019 lists Belagavi (+26 % monsoon rain,
      floods) but not Kolar (−27 %). M1 waits for real government orders.
- [x] 2026-10-24 — **M2 groundwater forecast trained** (`core/gwmodel.py`, `train/train_gw.py`,
      `train/precompute_gw.py`, `models/gw_m2.joblib`, `models/gw_m2_card.json`, `models/gw_m2_forecasts.npz`).
      Well-level quantile GBM (5/50/95 %) on 1.34 M real well-change examples (2,698 NWDP wells); future rain replayed
      from the 8 previous years; taluk = median of wells. Validation (train ≤ 2021, test 2022–26): taluk MAE 2.06 m vs
      2.22 m no-change, 10–90 % range covers 86 %; 2023 drought (Oct 2023 → Apr 2024, 20 taluks at stress): watch tier
      (pessimistic path) caught 18/20 but flags ~168, warning tier (likely path) 4/20 at 33 % precision. Ranks well
      (ρ 0.71), under-predicts extremes. First attempt (taluk-median panel) was worse than no-change and was dropped; an
      earlier "105/117" event figure came from a buggy experiment (wrong month normal) and is void.
      Risk levels now: critical = at stress / likely ≤ 90 d, high = likely ≤ 6 months, medium = watch, low.
      Drivers are metres (effect on groundwater in 3 months). Forecasts are precomputed per month (API ~instant).
- [ ] Real drought declarations (M1 labels), crop yields, KIADB cleaning
- [ ] M1 drought classifier + 2023 backtest
- [x] M2 taluk groundwater forecast (see above)
- [ ] M4 Cauvery storage forecast → Urban supply outlook
- [ ] Agri MUSTs · Urban MUSTs · Industry MUSTs
- [ ] Deploy to Vercel; README updated with Karnataka data table
