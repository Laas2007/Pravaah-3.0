# Raw data – drop files here

> **Already automated (don't download by hand):** groundwater well levels, reservoir daily data, river discharge and
> minor irrigation tanks come from the National Water Data Portal API (nwdp.nwic.gov.in) via
> `python train/fetch_nwdp.py`. The CSVs in `cgwb/` were the first manual downloads of the same data
> (Ballari, Belagavi, Bagalkot) and are kept only for reference.

Put downloaded files in the matching folder **as they are**: CSV, Excel, PDF, screenshots, copied text are all fine.
Don't clean or rename columns; the cleaning scripts handle that. Add a `SOURCE.txt` next to the files with
the link you got them from and the date.

| Folder | What | Where to get it | Needed columns / content |
|---|---|---|---|
| `reservoirs/` | **Reservoir storage history** (priority 1) | KSNDMC reservoir bulletin, CWC weekly "Live Storage" bulletin, India-WRIS reservoir module | Date, reservoir, storage (TMC/Mcft), inflow/outflow if shown. KRS, Kabini, Harangi, Hemavathi, Tungabhadra, Almatti, Narayanapur, Bhadra, Ghataprabha, Malaprabha, Linganamakki, Supa, Varahi. Weekly 2018–2024 is enough |
| `drought/` | **Drought-declared taluks by year** (priority 2) | Karnataka Revenue Dept government orders, KSNDMC, news | Taluk list per year (2016, 2018, 2019, 2023), severe/moderate if given |
| `cgwb/` | **CGWB groundwater assessment** (priority 3) | INGRES portal (ingres.iith.ac.in), Karnataka, latest year | Per taluk: stage of extraction %, category, recharge, extraction |
| `crops/` | **Crop area/production/yield** (priority 4) | ICRISAT District Level Database, data.gov.in district-wise crop production | District, year, crop, season, area, production, yield, irrigated area |
| `kiadb/` | KIADB industrial areas | KIADB website | Name, district/taluk, acreage, sectors |
| `aqueduct/` | WRI Aqueduct 4.0 baseline (optional) | wri.org Aqueduct data | Baseline annual CSV |
| `wells/` | Groundwater well levels (stretch) | India-WRIS groundwater level | Date, well, lat/lon, depth to water |

Partial data is fine. If a site blocks you for more than ~15 minutes, skip it and tell the team; the plan has a fallback.
API keys go in `.env` (git-ignored), never in these folders.
