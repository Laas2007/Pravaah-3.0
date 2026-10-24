"""Ward-aware chatbot (JalaMitra).

Uses Claude when API credentials are available; otherwise a built-in answer
engine composes detailed English/Kannada replies from the ward's prediction.
"""
import datetime as dt
import json
import os

import anthropic

from content import DRIVER, RISK, actions_for

MODEL = os.environ.get("CHAT_MODEL", "claude-haiku-4-5")

SYSTEM = """You are JalaMitra, the assistant inside Pravaah, a water scarcity prediction portal for Bengaluru, Karnataka.
You answer residents' and officials' questions about why water shortage is expected in their ward and what can be done.

How to answer:
- Reply in {language}. Use simple, everyday words a resident understands.
- Give complete, well-organised answers (roughly 120-220 words): a one-line direct answer first, then short
  sections with bullet points (for example "Why", "What you can do at home", "What your apartment/community can do",
  "What the city is doing"). Use plain text with line breaks and "•" bullets; do not use markdown symbols like ** or #.
- Ground every claim about the ward in the WARD DATA below and quote its numbers (days, dates, rainfall vs normal,
  borewell share, groundwater level). The "drivers" list is the model's explanation:
  "days" = how many days sooner the shortage arrives because of that factor (counterfactual analysis);
  "prevents": true means without that factor there would be no shortage within a year (a main cause).
- Days-to-shortage figures are model estimates from a groundwater balance model using real rainfall
  (IMD rain-gauge data) and estimated demand; say so if asked about accuracy. Do not invent numbers.
- Practical steps to draw on: rooftop rainwater harvesting, recharge pits/wells, aerators and low-flow fixtures,
  fixing leaks, reusing RO reject and STP-treated water, applying for a BWSSB Cauvery connection, booking tankers early,
  reporting leaks or misuse to the BWSSB helpline 1916, protecting and reviving local lakes.
- If the question is unrelated to water, politely steer back.

WARD DATA:
{ward}
"""


def _has_credentials():
    return bool(os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"))


def reply(ward: dict, as_of: str, lang: str, messages: list[dict]) -> dict:
    question = messages[-1]["content"]
    if _has_credentials():
        try:
            return {"text": _claude(ward, as_of, lang, messages), "source": "claude"}
        except anthropic.APIError:
            pass
    return {"text": Answer(ward, as_of, lang).respond(question), "source": "builtin"}


def _claude(ward, as_of, lang, messages):
    client = anthropic.Anthropic()
    context = {k: ward[k] for k in ("name", "risk", "days_low", "days_mid", "days_high", "groundwater_pct", "inputs", "drivers")}
    context["as_of"] = as_of
    resp = client.messages.create(
        model=MODEL,
        max_tokens=1500,
        system=SYSTEM.format(language="Kannada (ಕನ್ನಡ)" if lang == "kn" else "English",
                             ward=json.dumps(context, ensure_ascii=False, indent=1)),
        messages=[{"role": m["role"], "content": m["content"]} for m in messages[-12:]],
    )
    return "".join(b.text for b in resp.content if b.type == "text")


# ------------------------------------------------------------------ built-in answers

KN_MONTHS = ["ಜನವರಿ", "ಫೆಬ್ರವರಿ", "ಮಾರ್ಚ್", "ಏಪ್ರಿಲ್", "ಮೇ", "ಜೂನ್", "ಜುಲೈ", "ಆಗಸ್ಟ್", "ಸೆಪ್ಟೆಂಬರ್", "ಅಕ್ಟೋಬರ್", "ನವೆಂಬರ್", "ಡಿಸೆಂಬರ್"]

INTENTS = {
    "greet": ("hello", "hi ", "hey", "namaskara", "ನಮಸ್ಕಾರ", "ಹಲೋ"),
    "when": ("when", "how many days", "how long", "how soon", "date", "ಯಾವಾಗ", "ಎಷ್ಟು ದಿನ", "ದಿನಾಂಕ"),
    "why": ("why", "reason", "cause", "explain", "ಏಕೆ", "ಯಾಕೆ", "ಕಾರಣ"),
    "do": ("what can", "what should", "measure", "prevent", "save", "tip", "help", "reduce", "do ",
           "ಏನು ಮಾಡ", "ಕ್ರಮ", "ಉಳಿಸ", "ತಡೆ", "ಸಲಹೆ"),
    "rwh": ("rainwater", "harvest", "recharge", "pit", "ಮಳೆನೀರು", "ಇಂಗು", "ಮರುಪೂರಣ"),
    "tanker": ("tanker", "ಟ್ಯಾಂಕರ್"),
    "safe": ("safe", "risk", "danger", "should i worry", "status", "ಸುರಕ್ಷಿತ", "ಅಪಾಯ"),
    "how": ("accura", "how do you", "how does", "predict", "model", "data", "trust", "ನಿಖರ", "ಮುನ್ಸೂಚನೆ ಹೇಗೆ", "ದತ್ತಾಂಶ"),
    "ground": ("groundwater", "borewell", "bore well", "water table", "ಅಂತರ್ಜಲ", "ಕೊಳವೆಬಾವಿ"),
}


class Answer:
    def __init__(self, ward, as_of, lang):
        self.w = ward
        self.i = ward["inputs"]
        self.lang = lang
        self.kn = lang == "kn"
        self.as_of = dt.date.fromisoformat(as_of)

    # -- helpers
    def date(self, days):
        d = self.as_of + dt.timedelta(days=days)
        return f"{d.day} {KN_MONTHS[d.month - 1]} {d.year}" if self.kn else d.strftime("%-d %b %Y") if os.name != "nt" else d.strftime("%#d %b %Y")

    def rain_gap(self):
        n, a = self.i["rain_normal_mm"], self.i["rain_12m_mm"]
        return round((a - n) / n * 100) if n else 0

    def borewell_share(self):
        return round(100 - self.i["cauvery_coverage_pct"])

    def top_drivers(self, n=3):
        return [d for d in self.w["drivers"] if d["days"] > 0 or d["level_pts"] > 0][:n]

    # -- sections
    def headline(self):
        w, kn = self.w, self.kn
        risk = RISK[w["risk"]][self.lang]
        if w["days_mid"] == 0:
            return (f"⚠️ {w['name']} ನಲ್ಲಿ ಈಗಾಗಲೇ ನೀರಿನ ಕೊರತೆ ಇದೆ (ಅಪಾಯ: {risk}). ಅಂತರ್ಜಲ ಮಟ್ಟ ಕೇವಲ {w['groundwater_pct']}% ಇದ್ದು, ಕೊಳವೆಬಾವಿಗಳು ಬತ್ತುತ್ತಿವೆ."
                    if kn else f"⚠️ {w['name']} is already in water shortage (risk: {risk}). Groundwater is down to {w['groundwater_pct']}% of usable storage, so borewells are failing.")
        if w["days_low"] > 365:
            return (f"✅ {w['name']} ಸದ್ಯಕ್ಕೆ ಸುರಕ್ಷಿತ: ಮುಂದಿನ 12 ತಿಂಗಳಲ್ಲಿ ಕೊರತೆ ನಿರೀಕ್ಷೆ ಇಲ್ಲ (ಅಪಾಯ: {risk}). ಅಂತರ್ಜಲ ಮಟ್ಟ {w['groundwater_pct']}%."
                    if kn else f"✅ {w['name']} looks safe for now: no shortage is expected in the next 12 months (risk: {risk}). Groundwater is at {w['groundwater_pct']}% of usable storage.")
        hi = "365+" if w["days_high"] > 365 else str(w["days_high"])
        end = "" if w["days_high"] > 365 else (f" – {self.date(w['days_high'])}")
        return (f"📅 {w['name']} ನಲ್ಲಿ ಸುಮಾರು {w['days_low']}–{hi} ದಿನಗಳಲ್ಲಿ ({self.date(w['days_low'])}{end}) ನೀರಿನ ಕೊರತೆ ನಿರೀಕ್ಷಿಸಲಾಗಿದೆ. ಅಪಾಯ ಮಟ್ಟ: {risk}."
                if kn else f"📅 {w['name']} is expected to run short of water in about {w['days_low']}–{hi} days (around {self.date(w['days_low'])}{end}). Risk level: {risk}.")

    def when(self):
        out = [self.headline()]
        if self.kn:
            out.append("ಈ ಶ್ರೇಣಿ ಹೇಗೆ ಬಂತು:\n• ಕಳೆದ ವರ್ಷಗಳ 30 ವಿಭಿನ್ನ ಮಳೆ ಮತ್ತು ಬೇಡಿಕೆ ಸನ್ನಿವೇಶಗಳನ್ನು ಓಡಿಸಲಾಗಿದೆ.\n"
                       "• ಮುಂಚೆ ಮಳೆ ಬಂದರೆ ಕೊರತೆ ತಡವಾಗಬಹುದು; ಬಿಸಿಲು ಹೆಚ್ಚಾದರೆ ಬೇಗ ಬರಬಹುದು.\n"
                       "• ಸಾಮಾನ್ಯವಾಗಿ ಫೆಬ್ರವರಿ–ಮೇ ಬೇಸಿಗೆಯಲ್ಲಿ ಒತ್ತಡ ಹೆಚ್ಚು; ಜೂನ್ ಮಾನ್ಸೂನ್ ಬಳಿಕ ಮಟ್ಟ ಏರುತ್ತದೆ.")
        else:
            out.append("How we got this range:\n• The model replays 30 rainfall and demand scenarios taken from past years.\n"
                       "• Early pre-monsoon showers would push the date later; a hotter, drier spell would bring it sooner.\n"
                       "• Stress usually peaks in the dry months (Feb–May) and eases after the June monsoon.")
        return out

    def why(self):
        top = self.top_drivers()
        if not top:
            return ["ಈ ವಾರ್ಡ್‌ನಲ್ಲಿ ಯಾವುದೇ ಪ್ರಮುಖ ಅಪಾಯಕಾರಿ ಅಂಶ ಕಂಡುಬಂದಿಲ್ಲ: ಮಳೆ, ಕೊಳವೆ ನೀರು ಮತ್ತು ಬೇಡಿಕೆ ಸಮತೋಲನದಲ್ಲಿವೆ." if self.kn
                    else "No major risk factor stands out here: rainfall, piped supply and demand are reasonably balanced."]
        lines = []
        for d in top:
            lines.append("• " + self.explain_driver(d))
        head = "🔍 ಈ ಕೊರತೆಗೆ ಮುಖ್ಯ ಕಾರಣಗಳು:" if self.kn else "🔍 Why this is happening:"
        tail = (f"\nಒಟ್ಟಾರೆ: ಈ ವಾರ್ಡ್‌ನ ನೀರಿನ ಬೇಡಿಕೆ ದಿನಕ್ಕೆ ಸುಮಾರು {self.i['demand_mld']} ದಶಲಕ್ಷ ಲೀಟರ್ (MLD); ಅದರಲ್ಲಿ ಸುಮಾರು {self.borewell_share()}% ಅಂತರ್ಜಲದಿಂದ ಬರುತ್ತದೆ."
                if self.kn else f"\nIn short: this ward needs about {self.i['demand_mld']} million litres a day, and roughly {self.borewell_share()}% of it is pumped from the ground.")
        return [head + "\n" + "\n".join(lines) + tail]

    def explain_driver(self, d):
        i, kn, k = self.i, self.kn, d["key"]
        sooner = ("" if not d["days"] else
                  (" → ಇದಿಲ್ಲದಿದ್ದರೆ ಈ ವರ್ಷ ಕೊರತೆ ಇರುತ್ತಿರಲಿಲ್ಲ (ಮುಖ್ಯ ಕಾರಣ)." if kn else " → without it there would be no shortage this year (main cause).") if d.get("prevents")
                  else (f" → ಕೊರತೆಯನ್ನು ಸುಮಾರು {d['days']} ದಿನ ಮುಂಚಿತಗೊಳಿಸುತ್ತದೆ." if kn else f" → brings the shortage about {d['days']} days sooner."))
        gap = self.rain_gap()
        if k == "rain_deficit":
            txt = (f"ಕಳೆದ 12 ತಿಂಗಳಲ್ಲಿ {i['rain_12m_mm']} ಮಿಮೀ ಮಳೆ ಮಾತ್ರ (ವಾಡಿಕೆ {i['rain_normal_mm']} ಮಿಮೀ, {abs(gap)}% ಕಡಿಮೆ). ಕಡಿಮೆ ಮಳೆ ಎಂದರೆ ಅಂತರ್ಜಲ ಮರುಪೂರಣ ಕಡಿಮೆ."
                   if kn else f"Only {i['rain_12m_mm']} mm of rain fell in the last 12 months against a normal {i['rain_normal_mm']} mm ({abs(gap)}% {'below' if gap < 0 else 'above'} normal), so the ground was not refilled.")
        elif k == "borewell_dependence":
            txt = (f"ಕಾವೇರಿ ಕೊಳವೆ ನೀರು ಕೇವಲ {i['cauvery_coverage_pct']}% ಬೇಡಿಕೆ ಪೂರೈಸುತ್ತದೆ; ಉಳಿದ ಸುಮಾರು {self.borewell_share()}% ಕೊಳವೆಬಾವಿಗಳಿಂದ."
                   if kn else f"Cauvery pipes cover only about {i['cauvery_coverage_pct']}% of demand, so around {self.borewell_share()}% comes from borewells that drain the aquifer.")
        elif k == "commercial_load":
            txt = (f"ಐಟಿ ಪಾರ್ಕ್‌ಗಳು, ಕೈಗಾರಿಕೆಗಳು ಮತ್ತು ವಾಣಿಜ್ಯ ಕಟ್ಟಡಗಳು ದಿನಕ್ಕೆ ಸುಮಾರು {i['commercial_mld']} MLD ಹೆಚ್ಚುವರಿ ನೀರು ಬಳಸುತ್ತವೆ."
                   if kn else f"IT parks, industry and commercial buildings add roughly {i['commercial_mld']} million litres a day of extra demand.")
        elif k == "population_density":
            dens = round(i["population"] / max(i["area_km2"], 0.1))
            txt = (f"ಹೆಚ್ಚು ಜನಸಾಂದ್ರತೆ: ಪ್ರತಿ ಚ.ಕಿ.ಮೀ.ಗೆ ಸುಮಾರು {dens:,} ಜನರು, ಆದ್ದರಿಂದ ಪ್ರತಿ ಚದರ ಮೀಟರ್ ನೆಲದಿಂದ ಹೆಚ್ಚು ನೀರು ತೆಗೆಯಲಾಗುತ್ತದೆ."
                   if kn else f"Dense population: about {dens:,} people per km², so far more water is drawn from each patch of ground.")
        elif k == "cauvery_deficit":
            txt = (f"ಕಾವೇರಿ ಜಲಾನಯನ ಪ್ರದೇಶದಲ್ಲಿ ಮಳೆ ಕೊರತೆಯಿಂದ ಕೊಳವೆ ನೀರು ಪೂರೈಕೆ ಸುಮಾರು {i['cauvery_supply_pct']}% ಮಟ್ಟಕ್ಕೆ ಇಳಿದಿದೆ."
                   if kn else f"Poor rain in the Cauvery catchment (Kodagu, Wayanad) means piped supply is running at about {i['cauvery_supply_pct']}% of normal.")
        else:
            txt = ("ಕಾಂಕ್ರೀಟ್ ಮತ್ತು ಡಾಂಬರು ಮೇಲ್ಮೈಗಳು ಮಳೆನೀರು ಭೂಮಿಗೆ ಇಂಗದಂತೆ ತಡೆಯುತ್ತವೆ."
                   if kn else "Concrete and tarmac stop rain from soaking into the ground, so less of it recharges the aquifer.")
        return txt + sooner

    def todo(self):
        acts = actions_for(self.w["drivers"], n=4)
        home = "\n".join(f"• {a[self.lang]}" for a in acts)
        if self.kn:
            return [f"🏠 ಮನೆಯಲ್ಲಿ ನೀವು ಮಾಡಬಹುದಾದವು:\n{home}",
                    "🏢 ಅಪಾರ್ಟ್‌ಮೆಂಟ್/ಸಮುದಾಯ ಮಟ್ಟದಲ್ಲಿ:\n• ಸಾಮೂಹಿಕ ಮಳೆನೀರು ಸಂಗ್ರಹ ಮತ್ತು ಇಂಗುಬಾವಿಗಳು ನಿರ್ಮಿಸಿ.\n"
                    "• STP ಶುದ್ಧೀಕರಿಸಿದ ನೀರನ್ನು ತೋಟ ಮತ್ತು ಶೌಚಾಲಯಕ್ಕೆ ಬಳಸಿ.\n• ಪ್ರತಿ ಮನೆಗೆ ನೀರಿನ ಮೀಟರ್ ಅಳವಡಿಸಿ, ಬಳಕೆ ಹಂಚಿಕೊಳ್ಳಿ.",
                    "🏛️ ನಗರ ಮಟ್ಟದಲ್ಲಿ: ಕಾವೇರಿ ಪೈಪ್‌ಲೈನ್ ವಿಸ್ತರಣೆ, ಕೆರೆಗಳ ಪುನರುಜ್ಜೀವನ ಮತ್ತು ಮರುಪೂರಣ ಬಾವಿಗಳು. ಸೋರಿಕೆ ಕಂಡರೆ BWSSB ಸಹಾಯವಾಣಿ 1916 ಗೆ ತಿಳಿಸಿ."]
        return [f"🏠 What you can do at home:\n{home}",
                "🏢 What your apartment or community can do:\n• Build shared rainwater harvesting and recharge wells.\n"
                "• Reuse STP-treated water for gardens and flushing.\n• Meter each flat so everyone sees and cuts their own use.",
                "🏛️ What the city can do: extend Cauvery pipelines, revive local lakes and add recharge wells. Report leaks or misuse to the BWSSB helpline 1916."]

    def rwh(self):
        litres = round(0.8 * self.i["rain_normal_mm"] * 100 / 1000) * 1000
        if self.kn:
            return [f"🌧️ ಮಳೆನೀರು ಸಂಗ್ರಹ {self.w['name']} ನಲ್ಲಿ:\n• ಇಲ್ಲಿ ವರ್ಷಕ್ಕೆ ಸರಾಸರಿ {self.i['rain_normal_mm']} ಮಿಮೀ ಮಳೆ ಬೀಳುತ್ತದೆ; 100 ಚ.ಮೀ. ಮೇಲ್ಛಾವಣಿ ವರ್ಷಕ್ಕೆ ಸುಮಾರು {litres:,} ಲೀಟರ್ ಸಂಗ್ರಹಿಸಬಹುದು.\n"
                    "• ಛಾವಣಿಯ ನೀರನ್ನು ಫಿಲ್ಟರ್ ಮೂಲಕ ಸಂಪ್‌ಗೆ ಹರಿಸಿ; ಹೆಚ್ಚುವರಿ ನೀರನ್ನು ಇಂಗುಗುಂಡಿ ಅಥವಾ ಮರುಪೂರಣ ಬಾವಿಗೆ ಬಿಡಿ.\n"
                    "• ಮಳೆಗಾಲಕ್ಕೆ ಮುನ್ನ ಛಾವಣಿ, ಪೈಪ್ ಮತ್ತು ಫಿಲ್ಟರ್ ಸ್ವಚ್ಛಗೊಳಿಸಿ.\n"
                    "• ಬೆಂಗಳೂರಿನಲ್ಲಿ ಅನೇಕ ನಿವೇಶನಗಳಿಗೆ ಮಳೆನೀರು ಸಂಗ್ರಹ ಕಡ್ಡಾಯ; ವಿವರಗಳಿಗೆ BWSSB ಸಂಪರ್ಕಿಸಿ."]
        return [f"🌧️ Rainwater harvesting in {self.w['name']}:\n• This area gets about {self.i['rain_normal_mm']} mm of rain in a normal year, so a 100 m² roof can capture roughly {litres:,} litres a year.\n"
                "• Lead roof water through a simple filter into your sump; send the overflow to a recharge pit or recharge well.\n"
                "• Clean the roof, pipes and filter before each monsoon.\n"
                "• Rainwater harvesting is mandatory for many plot sizes in Bengaluru; BWSSB can advise on design."]

    def tanker(self):
        if self.kn:
            return ["🚚 ಟ್ಯಾಂಕರ್ ನೀರಿನ ಬಗ್ಗೆ:\n• ಕೊರತೆ ನಿರೀಕ್ಷಿತ ದಿನಾಂಕಕ್ಕೆ ಮುಂಚೆಯೇ ಟ್ಯಾಂಕರ್ ವ್ಯವಸ್ಥೆ ಮಾಡಿ; ಬೇಸಿಗೆಯಲ್ಲಿ ಬೇಡಿಕೆ ಮತ್ತು ಬೆಲೆ ಏರುತ್ತದೆ.\n"
                    "• ನೆರೆಹೊರೆಯವರೊಂದಿಗೆ ಸೇರಿ ಬುಕ್ ಮಾಡಿದರೆ ವೆಚ್ಚ ಕಡಿಮೆ.\n• ಸರ್ಕಾರ ನಿಗದಿಪಡಿಸಿದ ದರಕ್ಕಿಂತ ಹೆಚ್ಚು ಕೇಳಿದರೆ BWSSB 1916 ಗೆ ದೂರು ನೀಡಿ.",
                    self.headline()]
        return ["🚚 About tanker water:\n• Book before the expected shortage date; demand and prices jump in the dry months.\n"
                "• Pool bookings with neighbours or your apartment to cut the cost per household.\n"
                "• If a supplier charges above the government-notified rate, complain to the BWSSB helpline 1916.",
                self.headline()]

    def how(self):
        if self.kn:
            return ["🧠 ಈ ಮುನ್ಸೂಚನೆ ಹೇಗೆ ಮಾಡಲಾಗುತ್ತದೆ:\n• ನೈಜ ದೈನಂದಿನ ಮಳೆ ದತ್ತಾಂಶ (IMD ಮಳೆ ಮಾಪಕಗಳು, 2014–ಇಂದು) ಮತ್ತು ಕಾವೇರಿ ಜಲಾನಯನ ಮಳೆ.\n"
                    "• ಪ್ರತಿ ವಾರ್ಡ್‌ಗೆ ಜಲ ಸಮತೋಲನ: ಮಳೆ ಮರುಪೂರಣ − ಕೊಳವೆಬಾವಿ ಬಳಕೆ + ಪೈಪ್ ಸೋರಿಕೆ, ಪ್ರತಿದಿನ.\n"
                    "• 30 ಮಳೆ ಸನ್ನಿವೇಶಗಳಿಂದ ದಿನಗಳ ಶ್ರೇಣಿ; ಪ್ರತಿ ಅಂಶವನ್ನು ತೆಗೆದು ಮತ್ತೆ ಓಡಿಸಿ ಕಾರಣಗಳನ್ನು ಕಂಡುಹಿಡಿಯಲಾಗುತ್ತದೆ.\n"
                    "• 2024 ಬಿಕ್ಕಟ್ಟಿನ ಮೇಲೆ ಪರೀಕ್ಷಿಸಲಾಗಿದೆ. ಬೇಡಿಕೆ ಮತ್ತು ಪೈಪ್ ವ್ಯಾಪ್ತಿ ಅಂದಾಜು ಮೌಲ್ಯಗಳು."]
        return ["🧠 How this forecast works:\n• Real daily rainfall (IMD rain-gauge grid, 2014–today) plus rain in the Cauvery catchment.\n"
                "• A daily water balance for every ward: rain recharge − borewell pumping + pipe seepage.\n"
                "• 30 rainfall scenarios give the days range; switching each factor off and re-running shows the reasons.\n"
                "• Tested against the 2024 crisis. Demand and pipe coverage are estimates, clearly labelled in the app."]

    def ground(self):
        w = self.w
        if self.kn:
            return [f"💧 {w['name']} ನಲ್ಲಿ ಅಂತರ್ಜಲ ಈಗ ಬಳಸಬಹುದಾದ ಸಂಗ್ರಹದ {w['groundwater_pct']}% ಇದೆ (30% ಕೆಳಗೆ ಹೋದರೆ ಕೊಳವೆಬಾವಿಗಳು ಬತ್ತತೊಡಗುತ್ತವೆ).\n"
                    f"• ಈ ವಾರ್ಡ್‌ನ ಸುಮಾರು {self.borewell_share()}% ನೀರು ಕೊಳವೆಬಾವಿಗಳಿಂದ.\n• ಮಳೆನೀರು ಇಂಗಿಸುವುದು ಮತ್ತು ಕೆರೆಗಳನ್ನು ಉಳಿಸುವುದು ಮಟ್ಟ ಏರಿಸುವ ಉತ್ತಮ ದಾರಿ."]
        return [f"💧 Groundwater in {w['name']} is at {w['groundwater_pct']}% of usable storage (below 30%, borewells start to fail).\n"
                f"• About {self.borewell_share()}% of this ward's water is pumped from borewells.\n"
                "• Recharging rainwater and protecting local lakes are the most effective ways to raise the level."]

    def greet(self):
        hello = (f"ನಮಸ್ಕಾರ! ನಾನು ಜಲಮಿತ್ರ. {self.w['name']} ನ ನೀರಿನ ಪರಿಸ್ಥಿತಿ ಬಗ್ಗೆ ಹೇಳುತ್ತೇನೆ." if self.kn
                 else f"Hello! I'm JalaMitra. Here's the water picture for {self.w['name']}.")
        more = ("ನೀವು ಕೇಳಬಹುದು: ಕೊರತೆ ಏಕೆ? ಯಾವಾಗ? ನಾನು ಏನು ಮಾಡಬಹುದು? ಮಳೆನೀರು ಸಂಗ್ರಹ ಹೇಗೆ?" if self.kn
                else "You can ask me: why is this happening, when will it start, what can I do, or how to harvest rainwater.")
        return [hello, self.headline(), more]

    # -- router
    def respond(self, question):
        q = " " + question.lower() + " "
        hits = [k for k, words in INTENTS.items() if any(wd in q for wd in words)]
        parts = []
        if "greet" in hits and len(hits) == 1:
            return "\n\n".join(self.greet())
        if "how" in hits:
            parts += self.how()
        if "rwh" in hits:
            parts += self.rwh()
        if "tanker" in hits:
            parts += self.tanker()
        if "ground" in hits and "why" not in hits:
            parts += self.ground()
        if "when" in hits or "safe" in hits:
            parts += self.when()
        if "why" in hits:
            if not parts:
                parts.append(self.headline())
            parts += self.why()
        if "do" in hits and "rwh" not in hits:
            parts += self.todo()
        if not parts:  # unclear question: give the full picture
            parts = [self.headline()] + self.why() + self.todo()
        return "\n\n".join(parts)


# ------------------------------------------------------------------ taluk chat (Karnataka platforms)

SYSTEM_TALUK = """You are JalaMitra, the assistant inside Pravaah, a water scarcity prediction portal for Karnataka.
The user is on the {platform} platform and asks about {name} taluk ({district} district).

How to answer:
- Reply in {language}. Use simple, everyday words. Give a one-line direct answer first, then short sections with "•"
  bullets (roughly 120-200 words). Plain text only, no markdown symbols like ** or #.
- Ground every claim in the TALUK DATA below and quote its numbers. "days_*" = days until the taluk's groundwater
  reaches its stress level (its worst-10% level of 2014-2021) from an ML model trained on 2,698 real monitoring wells;
  366 means not within the 6-month horizon. Driver "metres" = how much deeper groundwater will be in 3 months because
  of that factor. Rain comes from IMD rain gauges. Do not invent numbers; say the model under-predicts extremes if
  asked about accuracy.
- Tailor advice to the platform: farmers (crop choice, drip/sprinkler, mulching, farm ponds, tank desilting, recharge),
  residents (saving water, rainwater harvesting, tankers, leaks), industry (water audits, recycling/ZLD, storage,
  alternative sources, CGWA rules).
- If the question is unrelated to water, politely steer back.

TALUK DATA:
{data}
"""

TIPS = {
    "agri": {
        "en": ["Choose short-duration, low-water crops this season (ragi, jowar, pulses) over paddy or sugarcane",
               "Switch to drip or sprinkler irrigation and mulch the soil to cut evaporation",
               "Desilt village tanks and build farm ponds / recharge pits before the monsoon",
               "Irrigate in the early morning or evening, and only when the topsoil is dry"],
        "kn": ["ಈ ಋತುವಿನಲ್ಲಿ ಭತ್ತ/ಕಬ್ಬಿನ ಬದಲು ಕಡಿಮೆ ನೀರಿನ, ಅಲ್ಪಾವಧಿ ಬೆಳೆಗಳು (ರಾಗಿ, ಜೋಳ, ದ್ವಿದಳ ಧಾನ್ಯ)",
               "ಹನಿ ಅಥವಾ ತುಂತುರು ನೀರಾವರಿ ಬಳಸಿ, ಮಣ್ಣಿಗೆ ಹೊದಿಕೆ (ಮಲ್ಚಿಂಗ್) ಹಾಕಿ",
               "ಮುಂಗಾರಿಗೆ ಮುನ್ನ ಕೆರೆಗಳ ಹೂಳೆತ್ತಿ, ಕೃಷಿ ಹೊಂಡ / ಇಂಗು ಗುಂಡಿ ನಿರ್ಮಿಸಿ",
               "ಮುಂಜಾನೆ ಅಥವಾ ಸಂಜೆ ಮಾತ್ರ, ಮೇಲ್ಮಣ್ಣು ಒಣಗಿದಾಗ ನೀರು ಹಾಯಿಸಿ"]},
    "urban": {
        "en": ["Fix leaks and fit aerators / low-flow fixtures (saves 20-30%)",
               "Harvest rooftop rainwater and recharge borewells",
               "Reuse RO reject and treated water for flushing and gardens",
               "Book tankers early in dry months; report misuse"],
        "kn": ["ಸೋರಿಕೆ ಸರಿಪಡಿಸಿ, ಏರೇಟರ್ / ಕಡಿಮೆ ಹರಿವಿನ ನಲ್ಲಿ ಅಳವಡಿಸಿ (20-30% ಉಳಿತಾಯ)",
               "ಚಾವಣಿ ಮಳೆನೀರು ಸಂಗ್ರಹಿಸಿ ಕೊಳವೆಬಾವಿ ಮರುಪೂರಣ ಮಾಡಿ",
               "RO ತ್ಯಾಜ್ಯ ನೀರು ಮತ್ತು ಶುದ್ಧೀಕರಿಸಿದ ನೀರನ್ನು ಶೌಚಾಲಯ, ತೋಟಕ್ಕೆ ಮರುಬಳಸಿ",
               "ಬೇಸಿಗೆಯಲ್ಲಿ ಟ್ಯಾಂಕರ್ ಮುಂಚಿತವಾಗಿ ಕಾಯ್ದಿರಿಸಿ"]},
    "industry": {
        "en": ["Run a water audit and fix the top losses first",
               "Recycle process and STP water (aim for zero liquid discharge)",
               "Add on-site storage and rooftop harvesting before the dry months",
               "Diversify sources (treated wastewater, KIADB supply) and follow CGWA groundwater rules"],
        "kn": ["ನೀರಿನ ಲೆಕ್ಕಪರಿಶೋಧನೆ ಮಾಡಿ, ಹೆಚ್ಚು ನಷ್ಟವನ್ನು ಮೊದಲು ತಡೆಯಿರಿ",
               "ಪ್ರಕ್ರಿಯೆ ಮತ್ತು STP ನೀರನ್ನು ಮರುಬಳಸಿ (ಶೂನ್ಯ ದ್ರವ ವಿಸರ್ಜನೆ ಗುರಿ)",
               "ಬೇಸಿಗೆಗೆ ಮುನ್ನ ಸಂಗ್ರಹ ಸಾಮರ್ಥ್ಯ ಮತ್ತು ಚಾವಣಿ ಮಳೆನೀರು ಸಂಗ್ರಹ ಹೆಚ್ಚಿಸಿ",
               "ಮೂಲಗಳನ್ನು ವೈವಿಧ್ಯಗೊಳಿಸಿ ಮತ್ತು CGWA ಅಂತರ್ಜಲ ನಿಯಮ ಪಾಲಿಸಿ"]},
}
PLATFORM_NAME = {"agri": "Agriculture & Farmers", "urban": "Urban Population", "industry": "Industries & Businesses"}
DRIVER_KN = {"rain_deficit": "ಇತ್ತೀಚಿನ ತಿಂಗಳುಗಳಲ್ಲಿ ವಾಡಿಕೆಗಿಂತ ಕಡಿಮೆ ಮಳೆ",
             "groundwater_already_low": "ಅಂತರ್ಜಲ ಈಗಾಗಲೇ ವಾಡಿಕೆಗಿಂತ ಆಳದಲ್ಲಿದೆ",
             "heat": "ವಾಡಿಕೆಗಿಂತ ಹೆಚ್ಚು ಬಿಸಿ / ಒಣ ಗಾಳಿ"}


def reply_taluk(ctx: dict, as_of: str, lang: str, platform: str, messages: list[dict]) -> dict:
    if _has_credentials():
        try:
            client = anthropic.Anthropic()
            resp = client.messages.create(
                model=MODEL, max_tokens=1200,
                system=SYSTEM_TALUK.format(platform=PLATFORM_NAME.get(platform, platform), name=ctx["name"],
                                           district=ctx["district"],
                                           language="Kannada (ಕನ್ನಡ)" if lang == "kn" else "English",
                                           data=json.dumps({**ctx, "as_of": as_of}, ensure_ascii=False, indent=1)),
                messages=[{"role": m["role"], "content": m["content"]} for m in messages[-12:]])
            return {"text": "".join(b.text for b in resp.content if b.type == "text"), "source": "claude"}
        except anthropic.APIError:
            pass
    return {"text": TalukAnswer(ctx, lang, platform).respond(messages[-1]["content"]), "source": "builtin"}


class TalukAnswer:
    """Built-in EN/KN answers from a taluk's indicators and M2 forecast (used without an API key)."""

    def __init__(self, ctx, lang, platform):
        self.c, self.kn, self.p = ctx, lang == "kn", platform if platform in TIPS else "urban"

    def _days(self, d):
        if d is None:
            return "–"
        if d == 0:
            return "ಈಗಲೇ" if self.kn else "now"
        if d >= 366:
            return "6 ತಿಂಗಳಿಗೂ ಹೆಚ್ಚು" if self.kn else "more than 6 months"
        return f"{round(d)} ದಿನ" if self.kn else f"{round(d)} days"

    def headline(self):
        c, f = self.c, self.c.get("forecast")
        risk = RISK[c["risk"]]["kn" if self.kn else "en"]
        if not f:
            return (f"{c['name']} ತಾಲೂಕು: ಅಪಾಯ {risk} (ಮಳೆ ಮತ್ತು ಅಂತರ್ಜಲ ಆಧಾರಿತ ತಾತ್ಕಾಲಿಕ ಸೂಚ್ಯಂಕ)." if self.kn
                    else f"{c['name']} taluk: {risk} risk (provisional index from rain and groundwater; no recent well readings).")
        rng = f"{self._days(f['days_low'])} – {self._days(f['days_high'])}"
        if (f["days_mid"] or 0) >= 366 and (f["days_low"] or 366) < 366:   # watch tier: only the dry-year path
            if self.kn:
                return (f"📅 {c['name']} ತಾಲೂಕು: ಸಾಮಾನ್ಯ ವರ್ಷದಲ್ಲಿ 6 ತಿಂಗಳೊಳಗೆ ಅಂತರ್ಜಲ ಒತ್ತಡ ನಿರೀಕ್ಷೆ ಇಲ್ಲ, ಆದರೆ ಮುಂದಿನ ತಿಂಗಳುಗಳು "
                        f"ಒಣಗಿದ್ದರೆ ಸುಮಾರು {self._days(f['days_low'])} ದಿನಗಳಲ್ಲಿ ತಲುಪಬಹುದು. ಅಪಾಯ: {risk} (ಎಚ್ಚರಿಕೆ ಪಟ್ಟಿ).")
            return (f"📅 {c['name']} taluk: groundwater is not expected to reach its stress level within 6 months in a "
                    f"typical year, but if the coming months are dry it could in about {self._days(f['days_low'])}. "
                    f"Risk: {risk} (watch list).")
        if self.kn:
            return f"📅 {c['name']} ತಾಲೂಕಿನ ಅಂತರ್ಜಲ ಒತ್ತಡ ಮಟ್ಟ ತಲುಪಲು ಸುಮಾರು {self._days(f['days_mid'])} (ವ್ಯಾಪ್ತಿ {rng}). ಅಪಾಯ: {risk}."
        return (f"📅 {c['name']} taluk's groundwater is expected to reach its stress level in about "
                f"{self._days(f['days_mid'])} (likely range {rng}). Risk: {risk}.")

    def why(self):
        c, i = self.c, self.c["indicators"]
        lines = ["ಕಾರಣಗಳು:" if self.kn else "Why:"]
        if i.get("rain_365d_dev_pct") is not None:
            dev = round(i["rain_365d_dev_pct"])
            lines.append(f"• ಕಳೆದ 12 ತಿಂಗಳ ಮಳೆ {round(i['rain_365d_mm'])} ಮಿ.ಮೀ., ವಾಡಿಕೆಗಿಂತ {dev:+d}%" if self.kn
                         else f"• Rain over the last 12 months: {round(i['rain_365d_mm'])} mm, {dev:+d}% vs normal (IMD)")
        if i.get("gw_anom_m") is not None and i.get("gw_depth_m") is not None:
            lines.append(f"• ಅಂತರ್ಜಲ {i['gw_depth_m']:.1f} ಮೀ. ಆಳದಲ್ಲಿ, ವಾಡಿಕೆಗಿಂತ {i['gw_anom_m']:+.1f} ಮೀ." if self.kn
                         else f"• Groundwater is {i['gw_depth_m']:.1f} m below ground, {i['gw_anom_m']:+.1f} m vs normal (wells)")
        for d in (c.get("forecast") or {}).get("drivers", [])[:3]:
            if abs(d["metres"]) >= 0.05:
                lab = DRIVER_KN.get(d["key"], d["label"]) if self.kn else d["label"]
                lines.append(f"• {lab}: 3 ತಿಂಗಳಲ್ಲಿ {d['metres']:+.1f} ಮೀ." if self.kn else f"• {lab}: {d['metres']:+.1f} m in 3 months")
        return ["\n".join(lines)]

    def todo(self):
        tips = TIPS[self.p]["kn" if self.kn else "en"]
        return [("ನೀವು ಮಾಡಬಹುದಾದವು:\n" if self.kn else "What you can do:\n") + "\n".join(f"• {t}" for t in tips)]

    def how(self):
        if self.kn:
            return ["🧠 ಮುನ್ಸೂಚನೆ ಹೇಗೆ: 2,698 ಸರ್ಕಾರಿ ಮೇಲ್ವಿಚಾರಣಾ ಬಾವಿಗಳ ಮಾಸಿಕ ದತ್ತಾಂಶದಿಂದ ಕಲಿತ ML ಮಾದರಿ, IMD ಮಳೆ ಮಾಪಕ "
                    "ದತ್ತಾಂಶ ಮತ್ತು ಹಿಂದಿನ 8 ವರ್ಷಗಳ ಮಳೆಯನ್ನು ಸಂಭಾವ್ಯ ಭವಿಷ್ಯಗಳಾಗಿ ಬಳಸುತ್ತದೆ. 2022–26 ರ ಮೇಲೆ ಪರೀಕ್ಷಿಸಲಾಗಿದೆ; "
                    "ತೀವ್ರ ಸಂದರ್ಭಗಳನ್ನು ಸ್ವಲ್ಪ ಕಡಿಮೆ ಅಂದಾಜಿಸುತ್ತದೆ."]
        return ["🧠 How this works: an ML model learned from monthly readings at 2,698 government monitoring wells, uses "
                "IMD rain-gauge data, and replays the past 8 years' rain as possible futures to give a range. It was "
                "tested on 2022–26 (years it never saw) and tends to under-predict extremes."]

    def respond(self, question):
        q = " " + question.lower() + " "
        hits = [k for k, words in INTENTS.items() if any(wd in q for wd in words)]
        parts = []
        if "how" in hits:
            parts += self.how()
        if "when" in hits or "safe" in hits or "ground" in hits:
            parts.append(self.headline())
        if "why" in hits:
            if not parts:
                parts.append(self.headline())
            parts += self.why()
        if "do" in hits or "rwh" in hits or "tanker" in hits:
            parts += self.todo()
        if not parts:
            parts = [self.headline()] + self.why() + self.todo()
        return "\n\n".join(parts)
