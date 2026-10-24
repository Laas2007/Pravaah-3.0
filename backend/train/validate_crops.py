"""Check M3 (FAO-56 water balance + FAO-33 yield response) against real district yields, DES 2024-25.

    python train/validate_crops.py      -> models/m3_card.json

For each district x crop x season in the DES file (Ministry of Agriculture & Farmers Welfare, 2024-25), the model's
rainfed yield loss for that season (observed IMD rain + ERA5 ET0, no future replay) is averaged over the district's
taluks and compared with the reported yield (kg/ha). A useful model should show a negative rank correlation: more
modelled water stress -> lower yield. Irrigation, soils, varieties and pests also drive yields, so expect it to be weak.
"""
import datetime as dt
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import spearmanr

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.data import regions  # noqa: E402
from usecases import agri_fao as af  # noqa: E402

DES = Path(__file__).resolve().parent.parent / "data" / "raw" / "drought" / "DES-District-Data-For-2024-25.xlsx"
CARD = Path(__file__).resolve().parent.parent / "models" / "m3_card.json"
DES_CROP = {"Rice": "Rice (paddy)", "Maize": "Maize", "Jowar": "Jowar (sorghum)", "Ragi": "Ragi (finger millet)",
            "Bajra": "Bajra (pearl millet)", "Tur": "Tur (red gram)", "Urad": "Urad (black gram)",
            "Moong": "Moong (green gram)", "Gram": "Gram (chickpea)", "Wheat": "Wheat"}
DISTRICT_ALIAS = {"Bengaluru South": "Ramanagara", "Chamarajanagar": "Chamarajanagara"}
SEASON_SOW = {"Kharif": dt.date(2024, 6, 20), "Rabi": dt.date(2024, 10, 15)}


def main():
    d = pd.read_excel(DES, header=None, skiprows=7)
    d.columns = ["state", "district", "crop", "season", "area", "prod", "yield"]
    d[["state", "district", "crop"]] = d[["state", "district", "crop"]].ffill()
    d = d[(d.state == "Karnataka") & d.crop.isin(DES_CROP) & d.season.isin(SEASON_SOW)]
    for c in ("area", "yield"):
        d[c] = pd.to_numeric(d[c], errors="coerce")
    d = d[(d.area > 0.005) & (d["yield"] > 0)]                      # at least ~500 ha grown
    by_d = {}
    for r in regions():
        by_d.setdefault(r["district"], []).append(r["idx"])

    rows = []
    for (crop, season), g in d.groupby(["crop", "season"]):
        name = DES_CROP[crop]
        if season.lower() not in af.CROPS[name][7]:
            continue
        sow = SEASON_SOW[season]
        end = sow + dt.timedelta(days=len(af.kc_curve(name)))
        for _, r in g.iterrows():
            dist = DISTRICT_ALIAS.get(r.district, r.district)
            idxs = by_d.get(dist)
            if not idxs:
                continue
            loss = np.mean([af.water_balance(i, name, sow, end)["loss"][0] for i in idxs]) * 100
            rows.append({"crop": crop, "season": season, "district": r.district, "yield_kg_ha": float(r["yield"]),
                         "area_lakh_ha": float(r.area), "model_rainfed_loss_pct": round(float(loss), 1)})
    df = pd.DataFrame(rows)
    out = []
    for (crop, season), g in df.groupby(["crop", "season"]):
        if len(g) < 8:
            continue
        rho = spearmanr(g.model_rainfed_loss_pct, g.yield_kg_ha).statistic
        out.append({"crop": crop, "season": season, "districts": len(g), "spearman_loss_vs_yield": round(float(rho), 2),
                    "median_loss_pct": round(float(g.model_rainfed_loss_pct.median()), 1)})
        print(f"{crop:6s} {season:6s} n={len(g):2d}  rho(loss, yield) = {rho:+.2f}   median modelled loss {g.model_rainfed_loss_pct.median():.0f}%")
    # pooled: yield relative to the crop-season median vs modelled loss
    df["rel_yield"] = df.yield_kg_ha / df.groupby(["crop", "season"]).yield_kg_ha.transform("median")
    pooled = spearmanr(df.model_rainfed_loss_pct, df.rel_yield).statistic
    print(f"pooled (yield relative to crop median): rho = {pooled:+.2f}, n = {len(df)}")
    CARD.write_text(json.dumps({
        "model": "M3 crop water stress & yield risk: FAO-56 water balance + FAO-33 Ky (physics, published coefficients)",
        "inputs": "IMD daily rain + ERA5 ET0 per taluk; soil water estimated (black soils N of 15N 170 mm/m, else 110)",
        "check": "DES 2024-25 district yields (Ministry of Agriculture), rank correlation of modelled rainfed loss vs yield",
        "by_crop": out, "pooled_spearman": round(float(pooled), 2), "pairs": int(len(df)),
        "reading": "negative = more modelled water stress goes with lower yields (expected direction)"}, indent=2))
    print(f"wrote {CARD.name}")


if __name__ == "__main__":
    main()
