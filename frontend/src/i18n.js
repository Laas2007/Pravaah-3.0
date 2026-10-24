// UI strings. Driver labels, risk labels and actions come from the API (backend/content.py).
export const T = {
  en: {
    tagline: 'Ward-level water scarcity prediction · Bengaluru',
    citizen: 'Citizen',
    official: 'Official',
    backtest: 'Backtest',
    asOf: 'As of',
    findArea: 'Find your area',
    searchPh: 'Search your area, e.g. Whitefield',
    yourArea: 'Your area',
    risk: 'risk',
    shortageIn: 'Water shortage expected in',
    days: 'days',
    around: 'around',
    already: 'This area is already in water shortage',
    noShortage: 'No shortage expected in the next 12 months',
    why: 'Why?',
    whyHint: 'How many days sooner each factor brings the shortage (model counterfactuals)',
    whatToDo: 'What you can do',
    groundwater: 'Groundwater level',
    ofCapacity: 'of usable storage',
    clickMap: 'Click your area on the map or search above.',
    ask: 'Ask JalaMitra',
    chatPh: 'Ask why, or what you can do…',
    send: 'Send',
    chatHello: (n) => `Hi! Ask me about water in ${n}: why a shortage is coming, or what you can do.`,
    sugg: ['Why is there a shortage here?', 'What can I do to save water?', 'When will the shortage start?'],
    daysSooner: 'days sooner',
    preventsYear: 'main cause: without it, no shortage within a year',
    lowersLevel: 'lowers groundwater by',
    pts: 'pts',
    loading: 'Running model…',
    askAbout: (n) => `Ask JalaMitra about ${n}`,
    pickWard: 'pick a ward',
  },
  kn: {
    tagline: 'ವಾರ್ಡ್ ಮಟ್ಟದ ನೀರಿನ ಕೊರತೆ ಮುನ್ಸೂಚನೆ · ಬೆಂಗಳೂರು',
    citizen: 'ನಾಗರಿಕ',
    official: 'ಅಧಿಕಾರಿ',
    backtest: 'ಹಿಂಪರೀಕ್ಷೆ',
    asOf: 'ದಿನಾಂಕ',
    findArea: 'ನಿಮ್ಮ ಪ್ರದೇಶ ಹುಡುಕಿ',
    searchPh: 'ನಿಮ್ಮ ವಾರ್ಡ್ ಹೆಸರು, ಉದಾ. Whitefield',
    yourArea: 'ನಿಮ್ಮ ಪ್ರದೇಶ',
    risk: 'ಅಪಾಯ',
    shortageIn: 'ನೀರಿನ ಕೊರತೆ ನಿರೀಕ್ಷೆ',
    days: 'ದಿನಗಳಲ್ಲಿ',
    around: 'ಸುಮಾರು',
    already: 'ಈ ಪ್ರದೇಶದಲ್ಲಿ ಈಗಾಗಲೇ ನೀರಿನ ಕೊರತೆ ಇದೆ',
    noShortage: 'ಮುಂದಿನ 12 ತಿಂಗಳಲ್ಲಿ ಕೊರತೆ ನಿರೀಕ್ಷೆ ಇಲ್ಲ',
    why: 'ಏಕೆ?',
    whyHint: 'ಪ್ರತಿ ಅಂಶ ಕೊರತೆಯನ್ನು ಎಷ್ಟು ದಿನ ಮುಂಚಿತಗೊಳಿಸುತ್ತದೆ (ಮಾದರಿ ವಿಶ್ಲೇಷಣೆ)',
    whatToDo: 'ನೀವು ಮಾಡಬಹುದಾದವು',
    groundwater: 'ಅಂತರ್ಜಲ ಮಟ್ಟ',
    ofCapacity: 'ಬಳಸಬಹುದಾದ ಸಂಗ್ರಹದ',
    clickMap: 'ನಕ್ಷೆಯಲ್ಲಿ ನಿಮ್ಮ ಪ್ರದೇಶ ಕ್ಲಿಕ್ ಮಾಡಿ ಅಥವಾ ಮೇಲೆ ಹುಡುಕಿ.',
    ask: 'ಜಲಮಿತ್ರನನ್ನು ಕೇಳಿ',
    chatPh: 'ಏಕೆ ಅಥವಾ ಏನು ಮಾಡಬಹುದು ಎಂದು ಕೇಳಿ…',
    send: 'ಕಳುಹಿಸಿ',
    chatHello: (n) => `ನಮಸ್ಕಾರ! ${n} ನ ನೀರಿನ ಬಗ್ಗೆ ಕೇಳಿ: ಕೊರತೆ ಏಕೆ, ಅಥವಾ ನೀವು ಏನು ಮಾಡಬಹುದು.`,
    sugg: ['ಇಲ್ಲಿ ನೀರಿನ ಕೊರತೆ ಏಕೆ?', 'ನೀರು ಉಳಿಸಲು ನಾನು ಏನು ಮಾಡಬಹುದು?', 'ಕೊರತೆ ಯಾವಾಗ ಶುರುವಾಗುತ್ತದೆ?'],
    daysSooner: 'ದಿನ ಮುಂಚೆ',
    preventsYear: 'ಮುಖ್ಯ ಕಾರಣ: ಇದಿಲ್ಲದಿದ್ದರೆ ಒಂದು ವರ್ಷದೊಳಗೆ ಕೊರತೆ ಇಲ್ಲ',
    lowersLevel: 'ಅಂತರ್ಜಲ ಇಳಿಕೆ',
    pts: 'ಅಂಕ',
    loading: 'ಮಾದರಿ ಚಾಲನೆಯಲ್ಲಿದೆ…',
    askAbout: (n) => `${n} ಬಗ್ಗೆ ಜಲಮಿತ್ರನನ್ನು ಕೇಳಿ`,
    pickWard: 'ವಾರ್ಡ್ ಆಯ್ಕೆಮಾಡಿ',
  },
}

export const RISK_COLOR = { low: '#0ca30c', medium: '#fab219', high: '#ec835a', critical: '#d03b3b' }
export const RISK_ICON = { low: '●', medium: '▲', high: '◆', critical: '✖' }
export const RISK_ORDER = ['critical', 'high', 'medium', 'low']

export function addDays(iso, n) {
  const d = new Date(iso + 'T00:00:00')
  d.setDate(d.getDate() + n)
  return d
}

export function fmtDate(d, lang = 'en') {
  if (typeof d === 'string') d = new Date(d + 'T00:00:00')
  return d.toLocaleDateString(lang === 'kn' ? 'kn-IN' : 'en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function rangeText(w) {
  if (w.days_mid === 0) return null
  if (w.days_low > 365) return null
  return `${w.days_low}–${w.days_high > 365 ? '365+' : w.days_high}`
}
