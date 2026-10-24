# Pravaah: features at a glance

Water scarcity forecasts for all **227 taluks of Karnataka** and **243 Bengaluru wards**, in English and Kannada.
Every number shows where it comes from (real, estimated or simulated) and how the model scored on years it never saw.

## Data (real, public)
- **Rain:** IMD 0.25° rain-gauge grid, daily, 2014 to today (quality-checked); ERA5 for evaporation and temperature.
- **Groundwater:** 2,664 government monitoring wells (NWDP, Karnataka Ground Water Directorate), monthly. NWDP's
  "not measured" placeholder (-0.05 m) is removed, and months that only a few wells have reported are skipped.
- **Reservoirs:** 34 dams, daily storage (NWDP). **Tanks:** minor-irrigation tanks per taluk (NWDP).
- **Official records:** CGWB groundwater assessment 2023 (stage of extraction per taluk), drought declarations
  (Govt. of Karnataka order of Sept 2023 + 2026 lists), KIADB industrial land, DES crop yields 2024-25.

## Models
| | What it predicts | How it was tested |
|---|---|---|
| **M1** | Kharif drought early warning per taluk (1 Jul to 30 Sep) | Against the official 2023 and 2026 drought declarations |
| **M2** | Days until each taluk's groundwater reaches stress, with a likely range | Trained to 2021, scored on 2022-26 against real wells |
| **M3** | Crop water stress and rainfed yield loss (FAO-56 / FAO-33) | Against real 2024-25 district yields |
| **M4** | Reservoir storage up to 6 months ahead | Trained to 2021, scored on 2022+ against real storage |
| **M5** | Urban demand and tanker need (estimated) | Physically based; no metered data exists |
| **M6** | Leak detection on water meters | Synthetic meters with planted leaks |
| **M7** | Industrial water-disruption risk per district | Transparent score from KIADB land, M2 and M4 |
| **Bengaluru** | Days to shortage for every ward (daily water balance) | Checked against real wells in the city |

## Agriculture & Farmers (`/agri`)
- Taluk map with layers: risk zones, kharif drought (M1), scarcity heatmap, 3-month rain, season water balance, groundwater.
- Taluk panel: groundwater forecast with "Why this number?", drought alert card with official declaration status.
- Crop advisor: crops ranked by water need and rainfed yield loss, irrigation schedule, sowing-date planner.

## Urban Population (`/urban`, `/urban/bengaluru`)
- Ward-level forecasts for all 243 Bengaluru wards inside the state map; other cities by taluk.
- Cauvery reservoir outlook (M4), demand and tanker estimates (M5), leak-detection test bench (M6).
- Full Bengaluru app: My Area, Officials (rankings, intervention planner), Time Machine.

## Industries & Businesses (`/industry`)
- **Factory site check:** pick any point and enter the daily water need to get a verdict (feasible / with conditions /
  risky / not recommended), a 0-100 score with reasons, and the statistics behind it: official groundwater status,
  water still available, nearby wells, reservoir outlook, rain and drought history, reuse and rainwater offsets.
- District disruption risk (M7) map and table.

## On every platform
- **Kannada / English** switch for the whole site.
- **Time Machine:** pick any past date; only data available on that date is used, then compare with what happened.
- **Timeline** with play button, story dates (2023 drought, 2024 crisis), guided tour.
- **JalaMitra chatbot** (Google Gemini, free tier) that answers in English or Kannada, quotes the local forecast,
  understands Kannada typed in English letters, and falls back to built-in answers when the free limit is reached.
- **Model card** with every model's honest test result; shareable links (`?as_of=`, `?taluk=`, `?lang=kn`).

## Limits we state openly
- Demand, pipe coverage and industrial water norms are estimates; leak detection is tested on synthetic meters.
- M1 cannot separate severe from moderate drought (the official decision also uses crop-loss surveys).
- Forecasts are screening tools, not permits or official declarations.
