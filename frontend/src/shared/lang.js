import { useSearchParams } from 'react-router-dom'

// Language lives in the URL (?lang=kn) so it survives switching platforms and opening the Bengaluru ward app.
export function useLang() {
  const [params, setParams] = useSearchParams()
  const lang = params.get('lang') === 'kn' ? 'kn' : 'en'
  const setLang = (l) => setParams((p) => { if (l === 'kn') p.set('lang', 'kn'); else p.delete('lang'); return p }, { replace: true })
  return [lang, setLang]
}

/** tr('English text', 'ಕನ್ನಡ ಪಠ್ಯ') -> the text for the current language (falls back to English). */
export function useTr() {
  const [lang] = useLang()
  const tr = (en, kn) => (lang === 'kn' && kn ? kn : en)
  tr.lang = lang
  return tr
}

export const RISK_TEXT = {
  critical: { en: 'critical', kn: 'ಗಂಭೀರ' },
  high: { en: 'high', kn: 'ಹೆಚ್ಚು' },
  medium: { en: 'medium', kn: 'ಮಧ್ಯಮ' },
  low: { en: 'low', kn: 'ಕಡಿಮೆ' },
}

export const DRIVER_TEXT = {
  rain_deficit: { en: 'Less rain than normal in recent months', kn: 'ಇತ್ತೀಚಿನ ತಿಂಗಳುಗಳಲ್ಲಿ ವಾಡಿಕೆಗಿಂತ ಕಡಿಮೆ ಮಳೆ' },
  groundwater_already_low: { en: 'Groundwater already deeper than normal', kn: 'ಅಂತರ್ಜಲ ಈಗಾಗಲೇ ವಾಡಿಕೆಗಿಂತ ಆಳದಲ್ಲಿದೆ' },
  heat: { en: 'Hotter / drier air than normal (high evaporation)', kn: 'ವಾಡಿಕೆಗಿಂತ ಹೆಚ್ಚು ಬಿಸಿ / ಒಣ ಗಾಳಿ (ಹೆಚ್ಚು ಆವಿಯಾಗುವಿಕೆ)' },
}

// Story-date presets (labels come from /api/core/meta in English)
export const PRESET_KN = {
  'Latest data': 'ಇತ್ತೀಚಿನ ದತ್ತಾಂಶ',
  '1 Aug 2023 (monsoon failing)': '1 ಆಗಸ್ಟ್ 2023 (ಮುಂಗಾರು ವಿಫಲ)',
  '1 Mar 2024 (crisis peak)': '1 ಮಾರ್ಚ್ 2024 (ಬಿಕ್ಕಟ್ಟಿನ ಉತ್ತುಂಗ)',
  '1 Aug 2022 (wet year)': '1 ಆಗಸ್ಟ್ 2022 (ಹೆಚ್ಚು ಮಳೆಯ ವರ್ಷ)',
}
