import { Link } from 'react-router-dom'
import { req } from '../api'
import { RISK_COLOR } from '../i18n'
import { useTr } from './lang'
import { RiskBadge } from './ui'

// Bengaluru's 243 BBMP wards (ward-level model, backend/model.py) as an overlay for the Karnataka map.
let wardGeoP
export const getWardGeo = () => (wardGeoP ??= req('/api/wards.geojson'))
export const fetchWards = (asOf) => req(`/api/urban/wards?as_of=${asOf}`)

export const daysText = (d, tr = (en) => en) =>
  (d == null ? '–' : d === 0 ? tr('now', 'ಈಗಲೇ') : d > 365 ? tr('1 year+', '1 ವರ್ಷ+') : tr(`${d} days`, `${d} ದಿನ`))

/** Build the `overlay` prop for KarnatakaMap from /api/urban/wards data. */
export function wardOverlay(geo, wards, selected, onSelect) {
  if (!geo || !wards) return null
  const byIdx = Object.fromEntries(wards.wards.map((w) => [w.idx, w]))
  return {
    geo, selected, onSelect,
    colorOf: (i) => byIdx[i] && RISK_COLOR[byIdx[i].risk],
    labelOf: (i) => byIdx[i] && `Ward: shortage in ${daysText(byIdx[i].days_low)}–${daysText(byIdx[i].days_high)}`,
  }
}

/** Ward summary for the side panel. */
export function WardCard({ ward, asOf, onClose }) {
  const tr = useTr()
  if (!ward) return null
  const dt = (d) => daysText(d, tr)
  const lang = tr.lang === 'kn' ? '&lang=kn' : ''
  return (
    <div className="ps-card">
      <div className="ps-card-head">
        <div><h2>{ward.name}</h2><div className="muted small">{tr(`Bengaluru ward ${ward.ward_no} · ward-level model`, `ಬೆಂಗಳೂರು ವಾರ್ಡ್ ${ward.ward_no} · ವಾರ್ಡ್ ಮಟ್ಟದ ಮಾದರಿ`)}</div></div>
        <RiskBadge risk={ward.risk} />
        {onClose && <button className="ps-x" onClick={onClose} aria-label="Close">✕</button>}
      </div>
      <div className="ps-forecast">
        <div className="ps-forecast-big">{dt(ward.days_mid)}</div>
        <div>
          <b>{tr('until this ward\'s groundwater runs short', 'ಈ ವಾರ್ಡ್‌ನ ಅಂತರ್ಜಲ ಕೊರತೆಯಾಗಲು')}</b>
          <div className="small muted">{tr(`likely range ${dt(ward.days_low)} – ${dt(ward.days_high)} · groundwater at ${ward.groundwater_pct}% of usable storage`,
            `ಸಂಭಾವ್ಯ ವ್ಯಾಪ್ತಿ ${dt(ward.days_low)} – ${dt(ward.days_high)} · ಅಂತರ್ಜಲ ಬಳಸಬಹುದಾದ ಸಂಗ್ರಹದ ${ward.groundwater_pct}%`)}</div>
        </div>
      </div>
      <Link className="ps-hero-link" to={`/urban/bengaluru?ward=${encodeURIComponent(ward.name)}&as_of=${asOf}&view=area${lang}`}>
        <span>🔎</span><div><b>{tr('Open full ward view', 'ಪೂರ್ಣ ವಾರ್ಡ್ ವಿವರ ತೆರೆಯಿರಿ')}</b>
          <div className="small">{tr('why, actions, history, interventions, chatbot', 'ಏಕೆ, ಕ್ರಮಗಳು, ಇತಿಹಾಸ, ಪರಿಹಾರ ಯೋಜನೆ, ಚಾಟ್‌ಬಾಟ್')}</div></div><span>→</span>
      </Link>
    </div>
  )
}
