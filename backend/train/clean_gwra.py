"""CGWB / Karnataka Ground Water Directorate "Dynamic Ground Water Resources of Karnataka 2023" (GWRA 2023) ->
data/karnataka/gwra_2023.json: per taluk annual extractable groundwater, current extraction by use, stage of
extraction (%) and official category (safe / semi_critical / critical / over_exploited).

Source PDF (44 MB, not committed): https://data.opencity.in/dataset/dynamic-ground-water-resources-of-karnataka-2023
  -> data/_downloads/cgwb/gwra_karnataka_2023.pdf;  `pdftotext -raw` -> data/raw/cgwb_gwra/annexure_v_b1.txt
Annexure V B1 (values in TMC/yr), one row per assessment unit. The result is checked against the report's own
district totals (Annexure VI A) and the script fails if any district is off by more than 0.05 TMC.
Run:  python train/clean_gwra.py
"""
import difflib
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW = ROOT / "data" / "raw" / "cgwb_gwra" / "annexure_v_b1.txt"
OUT = ROOT / "data" / "karnataka" / "gwra_2023.json"
TMC_M3 = 28.317e6
NUM = r"([\d.]+)"
CAT = r"(safe|semi_critical|critical|over_exploited)"
DATA = rf"{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+(?:{NUM}\s+)?{CAT}\s*$"
ROW = re.compile(rf"^\s*(\d{{1,3}})\s+([A-Za-z][A-Za-z .()&-]*?)\s+{DATA}")
DIST_TOTAL = re.compile(rf"^\s*(\d{{1,2}})\s+([A-Za-z][A-Za-z .()]*?)\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s+{NUM}\s*$")
RANK = {"safe": 0, "semi_critical": 1, "critical": 2, "over_exploited": 3}
PDF_DISTRICTS = {"Bagalkot": "Bagalkote", "Ballari": "Ballari", "Belagavi": "Belagavi", "Bengaluru (Rural)": "Bengaluru Rural",
                 "Bengaluru (Urban)": "Bengaluru Urban", "Bidar": "Bidar", "Chamaraja nagara": "Chamarajanagara",
                 "Chamarajanagara": "Chamarajanagara", "Chikkaballapura": "Chikkaballapura", "Chikkamagaluru": "Chikkamagaluru",
                 "Chitradurga": "Chitradurga", "Dakshina Kannada": "Dakshina Kannada", "Davanagere": "Davanagere",
                 "Dharwad": "Dharwad", "Gadag": "Gadag", "Hassan": "Hassan", "Haveri": "Haveri", "Kalburgi": "Kalaburagi",
                 "Kalaburagi": "Kalaburagi", "Kodagu": "Kodagu", "Kolara": "Kolar", "Kolar": "Kolar", "Koppal": "Koppal",
                 "Mandya": "Mandya", "Mysuru": "Mysuru", "Raichur": "Raichur", "Ramanagara": "Ramanagara",
                 "Shivamogga": "Shivamogga", "Tumakuru": "Tumakuru", "Udupi": "Udupi", "Uttara Kannada": "Uttara Kannada",
                 "Vijayanagara": "Vijayanagara", "Vijayapura": "Vijayapura", "Yadgir": "Yadgir"}
# official unit -> our taluk where the names differ too much for fuzzy matching (Bengaluru city units -> city taluks)
ALIAS = {"bangalore city": "Bengaluru South", "bangalore north": "Bengaluru North", "bangalore east": "Bengaluru East",
         "bangalore south": "Bengaluru South", "kollegala hanur": "Hanur", "gulbarga": "Kalaburagi",
         "kolhara": "Kolhar", "bijapur": "Vijayapura", "hospet": "Hosapete", "mysore": "Mysuru", "ramanagar": "Ramanagara",
         "gangavathi": "Gangawati", "somavarapete": "Somvarpet", "chinthamani": "Chintamani", "chikballapur": "Chikkaballapura",
         "chikmagalur": "Chikkamagaluru", "kgf": "Kolar Gold Field", "kolar gold fields": "Kolar Gold Field",
         "dandelli": "Dandeli", "t narasipura": "Tirumakudal - Narsipur", "h d kote": "Heggadadevankote",
         "heggadadevanakote": "Heggadadevankote", "hunagund": "Hungund", "athani": "Athni", "kagavada": "Kagwad",
         "hulasuru": "Hulsoor", "mudabidri": "Moodubidire", "k g f": "Kolar Gold Field", "kukanuru": "Kukunoor",
         "k r nagar": "Krishnarajanagara", "sirivara": "Sirwar", "joida": "Supa",
         # new taluks not in our 227 -> the taluk they were carved from
         "yaragatti": "Savadatti", "kalasa": "Mudigere", "kushalanagara": "Somvarpet", "ponnampete": "Virajpet",
         "harohalli": "Kanakapura", "alamela": "Sindgi"}


def norm(s: str) -> str:
    return " ".join(re.sub(r"[^a-z]+", " ", s.lower()).split())


def split_label(label: str, last_district: str | None):
    """'Chamaraja nagara Kollegala (Hanur)' -> ('Chamarajanagara', 'Kollegala (Hanur)')."""
    for pdf in sorted(PDF_DISTRICTS, key=len, reverse=True):
        if label.startswith(pdf + " ") or label == pdf:
            return PDF_DISTRICTS[pdf], label[len(pdf):].strip()
    return last_district, label.strip()


def main():
    regs = json.loads((ROOT / "data" / "karnataka" / "regions.json").read_text(encoding="utf-8"))["taluks"]
    by_d = {}
    for r in regs:
        by_d.setdefault(r["district"], {})[norm(r["name"])] = r["idx"]
    lines = RAW.read_text(encoding="utf-8", errors="replace").splitlines()
    start = next(i for i, l in enumerate(lines) if "ANNEXURE - V B1" in l) - 60     # first page has no title line
    end = next(i for i, l in enumerate(lines) if "ANNEXURE- VIA" in l)
    units, seen = [], set()
    for l in lines[start:end]:
        if not (m := ROW.match(l)) or m.group(1) in seen:
            continue
        seen.add(m.group(1))
        g = [m.group(3 + k) for k in range(9)]
        d, t = split_label(m.group(2), None)
        units.append({"n": int(m.group(1)), "district": d, "unit": t, "extractable_tmc": float(g[0]),
                      "irrigation_tmc": float(g[1]), "industrial_tmc": float(g[2]), "domestic_tmc": float(g[3]),
                      "extraction_tmc": float(g[4]), "future_tmc": float(g[6]), "category": g[8]})
    gaps = sorted(set(range(1, max(u["n"] for u in units) + 1)) - {u["n"] for u in units})
    if gaps:
        print("row numbers missing:", gaps)

    # check against the report's district totals
    totals = {}
    for l in lines[end:end + 200]:
        if m := DIST_TOTAL.match(l):
            totals[PDF_DISTRICTS.get(m.group(2).strip(), m.group(2).strip())] = float(m.group(4))
    bad = []
    for d, tot in totals.items():
        s = sum(u["extractable_tmc"] for u in units if u["district"] == d)
        if abs(s - tot) > 0.05:
            bad.append(f"{d}: units {s:.2f} vs district total {tot:.2f}")

    out, unmatched = {}, []
    for u in units:
        cands = by_d.get(u["district"], {})
        key = norm(u["unit"].split("(")[0]) if "(" in u["unit"] and norm(u["unit"]) not in ALIAS else norm(u["unit"])
        name = ALIAS.get(norm(u["unit"])) or ALIAS.get(key)
        idx = cands.get(norm(name)) if name else None
        if idx is None:
            hit = difflib.get_close_matches(key, list(cands), n=1, cutoff=0.72)
            idx = cands[hit[0]] if hit else None
        if idx is None:
            unmatched.append(f"{u['district']} / {u['unit']}")
            continue
        o = out.setdefault(idx, {"units": [], "extractable_tmc": 0.0, "extraction_tmc": 0.0, "industrial_tmc": 0.0,
                                 "irrigation_tmc": 0.0, "domestic_tmc": 0.0, "future_tmc": 0.0, "category": "safe"})
        o["units"].append(u["unit"])
        for k in ("extractable_tmc", "extraction_tmc", "industrial_tmc", "irrigation_tmc", "domestic_tmc", "future_tmc"):
            o[k] = round(o[k] + u[k], 3)
        if RANK[u["category"]] > RANK[o["category"]]:          # merged units take the worst official category
            o["category"] = u["category"]
    for o in out.values():
        o["stage_pct"] = round(100 * o["extraction_tmc"] / o["extractable_tmc"], 1) if o["extractable_tmc"] else None
        o["extractable_mld"] = round(o["extractable_tmc"] * TMC_M3 / 365 / 1000, 1)
        o["extraction_mld"] = round(o["extraction_tmc"] * TMC_M3 / 365 / 1000, 1)
        o["future_mld"] = round(o["future_tmc"] * TMC_M3 / 365 / 1000, 1)
    missing = [f"{r['district']} / {r['name']}" for r in regs if r["idx"] not in out]
    print(f"{len(units)} units, {len(totals)} district totals checked, "
          f"{len(out)}/227 taluks covered")
    print("district mismatches:", bad or "none")
    print("unmatched units:", unmatched or "none")
    print("our taluks without a unit:", missing or "none")
    if bad or unmatched:
        return 1
    OUT.write_text(json.dumps({"source": "Dynamic Ground Water Resources of Karnataka 2023 (CGWB + Karnataka Ground Water "
                                         "Directorate, GEC-2015 method), Annexure V B1, via data.opencity.in",
                               "units": "TMC per year (1 TMC = 28.317 million m3); *_mld = million litres per day",
                               "categories": {"safe": "stage <= 70 %", "semi_critical": "70-90 %", "critical": "90-100 %",
                                              "over_exploited": "> 100 %"},
                               "missing_taluks": missing,
                               "taluks": {str(k): v for k, v in sorted(out.items())}}, indent=0), encoding="utf-8")
    print("wrote", OUT)
    return 0


if __name__ == "__main__":
    sys.exit(main())
