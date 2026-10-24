# AGENTS.md — rules for every AI coding agent on this repo

This file is read by Claude Code (via `CLAUDE.md`), OpenAI Codex, Cursor, GitHub Copilot, Gemini CLI (via `GEMINI.md`),
Windsurf and others. **Five people work in parallel, each with a different agent. Following these rules is what makes
the pieces fit together.** If anything here conflicts with what you were asked, stop and ask your human.

## The project in one paragraph
Pravaah predicts water scarcity for all 227 taluks of Karnataka (plus 243 Bengaluru wards) with an explainable
physics + ML engine, shown on **3 platforms**: 🌾 Agriculture (`/agri`), 🏙️ Urban (`/urban`, `/urban/bengaluru`),
🏭 Industry (`/industry`). Backend: Python 3.14 + FastAPI + numpy/scikit-learn. Frontend: React 19 + Vite +
react-router + Leaflet + Recharts. Full plan and current status: **`PLAN.md`** (read §5 ML models, §6 features, §10 progress log).

## Golden rules
1. **Only edit files you own** (table below). Need a change in someone else's file? Ask that person; don't do it yourself.
2. **Never change a shared contract** (section "Contracts") without the owner agreeing. Add new fields; never rename or remove.
3. **Run `scripts/check.py` before every push.** It must print `PASS`. Add your new endpoints to its `ENDPOINTS` list.
4. **Shared files get one-line additions only:** `backend/main.py` (router include), `frontend/src/App.jsx` (route),
   `frontend/src/api.js`, `backend/requirements*.txt`, `frontend/package.json`. No reformatting, no reordering.
5. **No new dependencies without telling P5** (Vercel bundle size, Python 3.14 wheels). Prefer numpy/pandas/scikit-learn.
6. **Match the surrounding code style.** Python: type hints where useful, short docstrings, no black/ruff mass reformat.
   JS: function components + hooks, no TypeScript, no new UI/CSS frameworks, no class components.
7. **Real vs estimated vs simulated:** every number shown must be honest. Placeholder data → `mock: true` in the API and
   `<MockBanner>` in the UI. Never present synthetic data as real.
8. **No look-ahead:** anything computed "as of" a date may only use data on or before that date.
9. **Don't commit** `backend/.venv/`, `frontend/node_modules/`, `frontend/dist/`, `backend/data/_downloads/`, `.env`, API keys.
10. **Update `PLAN.md` §10 Progress log** (one line, dated) when you finish a feature.

## Who owns what
| Person | Role | Owns (edit freely) | Delivers to others |
|---|---|---|---|
| **P1** | Core data & ML lead | `backend/core/` (except `reservoirs.py`), `backend/train/` (except files below), `backend/models/`, `backend/data/karnataka/` (climate, gw, regions), `backend/data/raw/drought/` | `taluk_risk()` upgraded to M1 (drought) + M2 (days-to-shortage); `/api/core/model-card`; ERA5 re-run |
| **P2** | 🌾 Agriculture | `backend/usecases/agri.py` + any `backend/usecases/agri_*.py`, `backend/train/train_yield.py`, `backend/train/clean_crops.py`, `backend/data/raw/crops/`, `backend/data/karnataka/crops*`, `frontend/src/platforms/agri/` | — |
| **P3** | 🏙️ Urban + reservoir forecast | `backend/usecases/urban.py` + `urban_*.py`, `backend/model.py`, `backend/chat.py`, `backend/content.py`, `backend/core/reservoirs.py`, `backend/train/train_reservoir.py`, `backend/train/train_demand.py`, `frontend/src/platforms/urban/`, the original Bengaluru components in `frontend/src/*.jsx` (MapView, CitizenView, OfficialView, …) | `forecast_storage()` (M4), used by Industry too |
| **P4** | 🏭 Industry | `backend/usecases/industry.py` + `industry_*.py`, `backend/train/clean_kiadb.py`, `backend/data/raw/kiadb/`, `backend/data/raw/aqueduct/`, `backend/data/karnataka/kiadb*`, `frontend/src/platforms/industry/` | — |
| **P5** | Integrator: shell, design, QA, deploy, pitch | `frontend/src/shared/`, `frontend/src/Landing.jsx`, `frontend/src/App.jsx`, `frontend/src/index.css`, `frontend/src/i18n.js`, `scripts/`, `vercel.json`, `api/index.py`, `README.md`, `AGENTS.md`, `.github/` | Merges to `main`, shared components on request (e.g. `ModelCard`), Kannada labels, Vercel deploy, demo tour, pitch deck, video |

`backend/main.py`, `frontend/src/api.js`, requirements files: shared (one-line rule). `PLAN.md`: everyone appends to §10 only.

## Contracts (do not break)

### Backend: Python functions other people call
```python
from core.data import clamp_date, regions, taluk, climate, groundwater, reservoirs, tanks   # P1
from core.indicators import taluk_indicators, rain_deviation, clean                        # P1
from core.risk import taluk_risk                                                            # P1  <- THE risk API
from core.reservoirs import storage_on, combined_series, forecast_storage, CAUVERY_BENGALURU  # P3
```
- `taluk_risk(as_of) -> dict` keys: `model, levels, score, drought_prob, days_low, days_mid, days_high, drivers`
  (see docstring in `backend/core/risk.py`). Platforms use **only this** for risk. P1 improves the inside.
- `forecast_storage(names, as_of, horizon_days) -> dict | None`: None until M4 exists; keys in `backend/core/reservoirs.py`.
  Callers must handle None (show "forecast coming").
- Taluk index `idx` = 0…226, same order everywhere (`data/karnataka/regions.json`). Taluk id = `KA-<district>-<taluk>`.
- Dates are ISO strings `YYYY-MM-DD`; months `YYYY-MM`. Units: mm (rain/ET0), m below ground (groundwater, + = deeper),
  TMC (reservoir storage), MLD (city/industry water), cusecs (flows).

### Backend: HTTP API
- Each platform: `router = APIRouter(prefix="/api/<platform>")` in `backend/usecases/<platform>.py`, included in `main.py`.
- Every platform response: `as_of` (clamped with `clamp_date`), `model` (from `taluk_risk`), `risk` ∈
  `critical|high|medium|low` where a risk is shown, `mock: true` (or `mock_fields: [...]`) for placeholder data.
- JSON-safe values only: use `clean()` for numpy/NaN. Errors: `HTTPException(404|400, "message")`.
- Slow computations: cache with `functools.lru_cache` keyed on `as_of` strings (pattern used throughout).

### Frontend
- Each platform: `frontend/src/platforms/<x>/index.jsx` (page) + `api.js` (its own calls, built on `req` from `src/api.js`).
- Use the shared pieces, don't copy them: `PlatformShell` (header, date bar, layout), `KarnatakaMap`, `TalukDetail`,
  `useAsOf()` (date lives in `?as_of=` so it survives switching platforms), `useLoad()`, and `ui.jsx`
  (`RiskBadge`, `Stat`, `MockBanner`, `ProvisionalNote`, `Loading`, `ErrorBox`, `pct`, `m`).
- Colours: `RISK_COLOR` from `i18n.js`; platform colour `platform('<x>').color` from `shared/platforms.js`.
  Pass real colours to Recharts (not CSS variables) and set `isAnimationActive={false}`.
- New CSS goes in your platform folder (`platforms/<x>/<x>.css`, classes prefixed `<x>-`), not in shared CSS.
- Need a new shared component? Ask P5, or build it inside your platform folder first.

## Design rules (the site must not look AI-generated)
- No emoji anywhere in the UI or chatbot replies. Icons come from `frontend/src/shared/Icon.jsx` (add a path there if needed).
- No gradients (except data colour scales in map legends), no pill shapes (radius ≤ 8px), no purple, no glow/pulse/bounce
  or scroll/cursor animations, no hover lifts.
- Copy is specific and factual: real numbers from the data only (no invented metrics, testimonials or reviews), no vague
  hero lines, no em dashes, no "AI-powered" or "Made with AI" labels.
- Use `<DataTag k="real|estimated|simulated" />` from `shared/ui.jsx` to label where a number comes from.

## Workflow
- Branch per person: `p1-core`, `p2-agri`, `p3-urban`, `p4-industry`, `p5-shell`. Small commits.
- **Pull `main` at least every 2 hours** and at each sync point (h6, h12, h19 in `PLAN.md` §7); rebase/merge, re-run check.
- To merge: push your branch → tell P5 → P5 merges into `main` after `scripts/check.py` passes on the merged result.
- `main` must always build and pass the check.
- Data: raw files in `backend/data/raw/<dataset>/`, cleaning script in `backend/train/`, cleaned output in
  `backend/data/karnataka/` (compact JSON/NPZ, < 5 MB each). Never hand-edit cleaned outputs; re-run the script.

## Run
```
cd backend && .venv\Scripts\activate && pip install -r requirements-train.txt
uvicorn main:app --reload --port 8000          # API + built frontend on http://localhost:8000
cd frontend && npm install && npm run dev      # dev UI on http://localhost:5173
backend\.venv\Scripts\python scripts\check.py  # before every push
```
