"""Bilingual (English / Kannada) labels and advice, keyed by model driver."""

RISK = {
    "critical": {"en": "Critical", "kn": "ಗಂಭೀರ"},
    "high": {"en": "High", "kn": "ಹೆಚ್ಚು"},
    "medium": {"en": "Medium", "kn": "ಮಧ್ಯಮ"},
    "low": {"en": "Low", "kn": "ಕಡಿಮೆ"},
}

DRIVER = {
    "rain_deficit": {
        "en": "Less rain than normal over the past 12 months",
        "kn": "ಕಳೆದ 12 ತಿಂಗಳಲ್ಲಿ ವಾಡಿಕೆಗಿಂತ ಕಡಿಮೆ ಮಳೆ",
    },
    "borewell_dependence": {
        "en": "Heavy dependence on borewells (limited Cauvery pipe supply)",
        "kn": "ಕೊಳವೆಬಾವಿಗಳ ಮೇಲೆ ಹೆಚ್ಚಿನ ಅವಲಂಬನೆ (ಕಾವೇರಿ ಕೊಳವೆ ನೀರಿನ ಸಂಪರ್ಕ ಕಡಿಮೆ)",
    },
    "population_density": {
        "en": "High population density and household demand",
        "kn": "ಹೆಚ್ಚಿನ ಜನಸಾಂದ್ರತೆ ಮತ್ತು ಮನೆಬಳಕೆಯ ನೀರಿನ ಬೇಡಿಕೆ",
    },
    "commercial_load": {
        "en": "Water use by IT parks, industry and commercial buildings",
        "kn": "ಐಟಿ ಪಾರ್ಕ್‌ಗಳು, ಕೈಗಾರಿಕೆಗಳು ಮತ್ತು ವಾಣಿಜ್ಯ ಕಟ್ಟಡಗಳ ನೀರಿನ ಬಳಕೆ",
    },
    "cauvery_deficit": {
        "en": "Poor rain in the Cauvery catchment, reducing piped supply",
        "kn": "ಕಾವೇರಿ ಜಲಾನಯನ ಪ್ರದೇಶದಲ್ಲಿ ಮಳೆ ಕೊರತೆ, ಕೊಳವೆ ನೀರು ಪೂರೈಕೆ ಕಡಿತ",
    },
    "paved_surface": {
        "en": "Concrete and paved land stopping rain from soaking in",
        "kn": "ಕಾಂಕ್ರೀಟ್ ಮೇಲ್ಮೈಗಳಿಂದ ಮಳೆನೀರು ಭೂಮಿಗೆ ಇಂಗುವುದು ಕಡಿಮೆ",
    },
}

# Citizen actions, most relevant first for each driver.
ACTIONS = {
    "rain_deficit": [
        {"en": "Install or clean a rooftop rainwater harvesting system before the next rains.",
         "kn": "ಮುಂದಿನ ಮಳೆಗೆ ಮುನ್ನ ಮೇಲ್ಛಾವಣಿ ಮಳೆನೀರು ಸಂಗ್ರಹ ವ್ಯವಸ್ಥೆ ಅಳವಡಿಸಿ ಅಥವಾ ಸ್ವಚ್ಛಗೊಳಿಸಿ."},
        {"en": "Build a recharge pit or recharge well to feed rain into the ground.",
         "kn": "ಮಳೆನೀರು ಭೂಮಿಗೆ ಇಂಗಲು ಇಂಗುಗುಂಡಿ ಅಥವಾ ಮರುಪೂರಣ ಬಾವಿ ನಿರ್ಮಿಸಿ."},
    ],
    "borewell_dependence": [
        {"en": "Apply for a BWSSB Cauvery connection if your street has a new pipeline.",
         "kn": "ನಿಮ್ಮ ರಸ್ತೆಯಲ್ಲಿ ಹೊಸ ಪೈಪ್‌ಲೈನ್ ಇದ್ದರೆ BWSSB ಕಾವೇರಿ ಸಂಪರ್ಕಕ್ಕೆ ಅರ್ಜಿ ಸಲ್ಲಿಸಿ."},
        {"en": "Store water and plan tanker bookings early in the dry season (Feb to May).",
         "kn": "ಬೇಸಿಗೆಯಲ್ಲಿ (ಫೆಬ್ರವರಿ–ಮೇ) ಮುಂಚಿತವಾಗಿ ನೀರು ಸಂಗ್ರಹಿಸಿ ಮತ್ತು ಟ್ಯಾಂಕರ್ ವ್ಯವಸ್ಥೆ ಯೋಜಿಸಿ."},
    ],
    "population_density": [
        {"en": "Fit aerators and low-flow fixtures: they cut household use by 20–30%.",
         "kn": "ನಲ್ಲಿಗಳಿಗೆ ಏರೇಟರ್ ಅಳವಡಿಸಿ: ಮನೆಬಳಕೆಯ ನೀರು 20–30% ಉಳಿತಾಯ."},
        {"en": "Fix leaking taps and overflowing sumps and tanks.",
         "kn": "ಸೋರುವ ನಲ್ಲಿಗಳು ಮತ್ತು ತುಂಬಿ ಹರಿಯುವ ಸಂಪ್/ಟ್ಯಾಂಕ್‌ಗಳನ್ನು ಸರಿಪಡಿಸಿ."},
    ],
    "commercial_load": [
        {"en": "Ask your apartment or office to reuse treated STP water for flushing and gardens.",
         "kn": "ನಿಮ್ಮ ಅಪಾರ್ಟ್‌ಮೆಂಟ್/ಕಚೇರಿಯಲ್ಲಿ ಶುದ್ಧೀಕರಿಸಿದ STP ನೀರನ್ನು ಶೌಚಾಲಯ ಮತ್ತು ತೋಟಕ್ಕೆ ಮರುಬಳಕೆ ಮಾಡಲು ಕೇಳಿ."},
    ],
    "cauvery_deficit": [
        {"en": "Expect reduced piped supply hours: keep sumps filled and avoid washing vehicles with drinking water.",
         "kn": "ಕೊಳವೆ ನೀರು ಪೂರೈಕೆ ಸಮಯ ಕಡಿಮೆಯಾಗಬಹುದು: ಸಂಪ್ ತುಂಬಿಸಿಡಿ, ಕುಡಿಯುವ ನೀರಿನಿಂದ ವಾಹನ ತೊಳೆಯಬೇಡಿ."},
    ],
    "paved_surface": [
        {"en": "Replace paved areas around your home with permeable tiles or soil and plants.",
         "kn": "ಮನೆಯ ಸುತ್ತಲಿನ ಕಾಂಕ್ರೀಟ್ ಬದಲು ನೀರು ಇಂಗುವ ಟೈಲ್ಸ್ ಅಥವಾ ಮಣ್ಣು ಮತ್ತು ಗಿಡಗಳನ್ನು ಬಳಸಿ."},
    ],
}

GENERAL_ACTIONS = [
    {"en": "Reuse RO reject and kitchen rinse water for mopping and plants.",
     "kn": "RO ತ್ಯಾಜ್ಯ ನೀರು ಮತ್ತು ಅಡುಗೆಮನೆ ತೊಳೆದ ನೀರನ್ನು ನೆಲ ಒರೆಸಲು ಮತ್ತು ಗಿಡಗಳಿಗೆ ಮರುಬಳಸಿ."},
    {"en": "Report leaks and illegal water use to the BWSSB helpline (1916).",
     "kn": "ಸೋರಿಕೆ ಮತ್ತು ಅಕ್ರಮ ನೀರು ಬಳಕೆಯನ್ನು BWSSB ಸಹಾಯವಾಣಿ (1916) ಗೆ ತಿಳಿಸಿ."},
]


def actions_for(drivers, n=4):
    out, seen = [], set()
    for d in drivers:
        if d["days"] <= 0 and d["level_pts"] <= 0:
            continue
        for a in ACTIONS.get(d["key"], []):
            if a["en"] not in seen:
                out.append(a)
                seen.add(a["en"])
    for a in GENERAL_ACTIONS:
        if a["en"] not in seen:
            out.append(a)
    return out[:n]
