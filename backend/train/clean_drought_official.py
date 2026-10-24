"""Official Karnataka drought declarations -> data/karnataka/drought_official.json (labels for checking M1).

    python train/clean_drought_official.py

Sources (genuine, kept in data/raw/drought/official/):
  2023 kharif: Government Order RD 449 TNR 2023 dated 13.09.2023 (Revenue Dept, Disaster Management), translated copy
               filed with the National Green Tribunal (OA 196 of 2024, reply statement R2): 161 severe + 34 moderate
               taluks (Annexures I and II). Order of 04.11.2023: 7 more severe taluks (press reports, Deccan Chronicle).
               The 22 taluks added on 12.10.2023 are not named in any public source found -> left "unknown".
  2026 kharif: second-phase order of 17.09.2026 (Deccan Chronicle): 21 severe + 2 moderate taluks. The 101 first-phase
               taluks (27.08.2026) are not named publicly -> unknown.
Official taluk names (236 taluks) are matched to our 227 LGD-2018 taluks; taluks created after 2018 map to their parent
taluk (a parent counts as declared if any part was; severity = the most severe part).
"""
import difflib
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.data import regions  # noqa: E402

RAW = Path(__file__).resolve().parent.parent / "data" / "raw" / "drought" / "official"
OUT = Path(__file__).resolve().parent.parent / "data" / "karnataka" / "drought_official.json"

ALIAS = {   # official spelling -> our taluk name (or its parent for taluks created after 2018)
    "Bengaluru East": "Bengaluru East", "Harohalli": "Kanakapura", "K.G.F": "Kolar Gold Field", "Mulabagilu": "Mulbagal",
    "Chinthamani": "Chintamani", "Gowribidanuru": "Gauribidanur", "Shidlagatta": "Sidlaghatta",
    "Chikkanayakanahalli": "Chiknayakanhalli", "Pavgada": "Pavagada", "Shira": "Sira", "Tipaturu": "Tiptur",
    "Molakalmuuru": "Molakalmuru", "Chennagiri": "Channagiri", "Honnalli": "Honnali", "Jagalluru": "Jagalur",
    "Thanamati": "Nyamathi", "H.D. Kote": "Heggadadevankote", "Hunasuru": "Hunsur", "Nanjanagudu": "Nanjangud",
    "Piriyapatana": "Piriyapatna", "T. Narasipura": "Tirumakudal - Narsipur", "Saraguru": "Saraguru",
    "Saligrama": "Krishnarajanagara", "Krishnarajapete": "Krishnarajpet", "Srirangapatna": "Shrirangapattana",
    "Bellary": "Ballari", "Shiruguppa": "Siruguppa", "Yulburga": "Yelbarga", "Kukanooru": "Kukunoor",
    "Lingasuguru": "Lingsugur", "Maanvi": "Manvi", "Shiravaara": "Sirwar", "Afjalpura": "Afzalpur", "Aalanda": "Aland",
    "Chithapura": "Chittapur", "Kalaburgi": "Kalaburagi", "Jeevargi": "Jevargi", "Kalagi": "Kalagi",
    "Kamalapura": "Kamalapur", "Shahabhad": "Shahabad", "Balki": "Bhalki", "Hulasuru": "Hulsoor", "Athani": "Athni",
    "Bailahongala": "Bailahongala", "Chikkodi": "Chikodi", "Hikkeri": "Hukeri", "Ramadurga": "Ramdurg",
    "Rayabhag": "Raybag", "Savadathi": "Savadatti", "Kithuru": "Kittur", "Khagwad": "Kagwad", "Yaraghatti": "Savadatti",
    "Beelagi": "Bilgi", "Hunagunda": "Hungund", "Jamakandi": "Jamkhandi", "Mudhola": "Mudhol", "Hilkal": "Ilkal",
    "Rabakavi Banahatti": "Rabakavi Banahatti", "Basavana Bhagewadi": "Basavana Bagevadi", "Muddebihaala": "Muddebihal",
    "Sindagi": "Sindgi", "Bableshwara": "Babaleshwar", "Chadachana": "Chadachan", "Nidagundhi": "Nidagundi",
    "Thalikote": "Talikoti", "Kohlara": "Kolhar", "Devarahipparagi": "Devara Hipparagi", "Alamela": "Sindgi",
    "Naragunda": "Nargund", "Roona": "Ron", "Gajendragada": "Gajendragad", "Lakshmeshwara": "Laxmeshwar",
    "Hirekarur": "Hirekerur", "Savanuru": "Savanur", "Kundagola": "Kundgol", "Navalagunda": "Navalgund",
    "Hubbali": "Hubballi", "Hubbalinagara": "Hubballi Urban", "Hubballi City": "Hubballi Urban", "Annigeri": "Annigeri",
    "Baravathi": "Bhadravati", "Shikaripura": "Shikarpur", "Soraba": "Sorab", "Theertahalli": "Tirthahalli",
    "Arakalagudu": "Arkalgud", "Kaduru": "Kadur", "Madikere": "Madikeri", "Virajpete": "Virajpet",
    "Kushalnagara": "Somvarpet", "Shirasi": "Sirsi", "Mundagod": "Mundgod", "Shapura": "Shahpur", "Vadagera": "Wadagera",
    "Hadagali": "Hadagalli", "Harapannahalli": "Harapanahalli", "Kudlugi": "Kudligi", "Chennapattana": "Channapatna",
    "Kollgala": "Kollegal", "Hanuru": "Hanur", "Beluru": "Belur", "Chennarayapattana": "Channarayapatna",
    "Holenarasipura": "Hole Narsipur", "Sakaleshpura": "Sakleshpur", "Shrigeri": "Sringeri", "Kalasa": "Mudigere",
    "Somavarapete": "Somvarpet", "Mudabidre": "Moodubidire", "Brahmavara": "Brahmavara", "Batkala": "Bhatkal",
    "Karawar": "Karwar", "Joyida": "Supa", "Shorapura": "Shorapur", "Yadagiri": "Yadgir", "Gurumittal": "Gurumitkal",
    "Hunasigi": "Hunasagi", "Ponnampet": "Virajpet", "Chitaguppa": "Chitaguppa", "Humnabad": "Homnabad",
    "Kamala Nagar": "Kamalnagar", "Kamalanagar": "Kamalnagar", "Sindhanur": "Sindhnur", "Tikota": "Tikota",
    "Babaleshwar": "Babaleshwar", "Basavana Bagewadi": "Basavana Bagevadi", "Yadrami": "Yadrami",
}


def parse_annex(text, start, end):
    block = text[text.index(start): text.index(end) if end else len(text)]
    names = []
    for line in block.splitlines():
        m = re.match(r"^\s*(?:\d+\.?\s+[A-Za-z .]+?\s+)?(\d+)\.?\s+([A-Za-z][A-Za-z .\-]+?)\s*$", line)
        if m and not line.startswith(("S.No", "Page", "List")):
            names.append(m.group(2).strip())
    return names


def match(name, by_name, misses):
    n = ALIAS.get(name, name)
    if n in by_name:
        return by_name[n]
    close = difflib.get_close_matches(n, by_name, n=1, cutoff=0.8)
    if close:
        return by_name[close[0]]
    misses.append(name)
    return None


def main():
    text = (RAW / "order_2023_09_text.txt").read_text(encoding="utf-8")
    severe = parse_annex(text, "List of 161 taluks", "Annexure II")
    moderate = parse_annex(text, "List of 34 taluks", None)
    print(f"parsed 2023 order: {len(severe)} severe, {len(moderate)} moderate (expect 161 / 34)")
    nov = ["Aurad", "Bidar", "Chitaguppa", "Humnabad", "Kamala Nagar", "Sindhanur", "Tikota"]
    y26_sev = ["Tiptur", "Karatagi", "Manvi", "Sindhanur", "Sirwar", "Afzalpur", "Aland", "Chittapur", "Kalaburagi",
               "Yadrami", "Shahabad", "Bhalki", "Basavana Bagewadi", "Babaleshwar", "Tikota", "Rattihalli", "Hubballi",
               "Navalgund", "Hubballi City", "Annigeri", "Kadur"]
    y26_mod = ["Ponnampet", "Virajpet"]

    regs = regions()
    by_name = {r["name"]: r["idx"] for r in regs}
    misses = []
    lab = {}

    def put(year, names, level, phase):
        for nm in names:
            i = match(nm, by_name, misses)
            if i is None:
                continue
            cur = lab.setdefault(year, {}).get(i)
            rank = {"severe": 2, "moderate": 1}
            if cur is None or rank[level] > rank[cur["level"]]:
                lab[year][i] = {"level": level, "phase": phase, "official_name": nm}

    put("2023", severe, "severe", "2023-09-13")
    put("2023", moderate, "moderate", "2023-09-13")
    put("2023", nov, "severe", "2023-11-04")
    put("2026", y26_sev, "severe", "2026-09-17")
    put("2026", y26_mod, "moderate", "2026-09-17")
    print("unmatched official names:", misses)
    out = {
        "sources": {
            "2023": "GO RD 449 TNR 2023 (13.09.2023), Annexures I-II, translated copy in NGT OA 196/2024 reply by R2; "
                    "order of 04.11.2023 (7 taluks, Deccan Chronicle). 22 taluks added 12.10.2023 are not named publicly.",
            "2026": "Order of 17.09.2026, 23 taluks (Deccan Chronicle). 101 first-phase taluks (27.08.2026) not named publicly.",
        },
        "complete": {"2023": False, "2026": False},
        "note": "Taluks not listed are NOT known to be drought-free: in 2023, 22 of the unlisted taluks were declared in "
                "October; in 2026, 101 first-phase taluks are unnamed. Use listed taluks as positives only.",
        "years": {y: {str(i): v for i, v in d.items()} for y, d in lab.items()},
    }
    OUT.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    for y, d in lab.items():
        levels = [v["level"] for v in d.values()]
        print(f"{y}: {len(d)} of our taluks labelled ({levels.count('severe')} severe, {levels.count('moderate')} moderate)")


if __name__ == "__main__":
    main()
