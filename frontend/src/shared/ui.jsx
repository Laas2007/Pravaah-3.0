import { RISK_COLOR } from '../i18n'

export function RiskBadge({ risk }) {
  if (!risk) return <span className="ps-badge muted">no data</span>
  return <span className="ps-badge" style={{ background: RISK_COLOR[risk] }}>{risk}</span>
}

export function Stat({ label, value, unit, sub, tone }) {
  return (
    <div className={`ps-stat ${tone || ''}`}>
      <div className="ps-stat-label">{label}</div>
      <div className="ps-stat-value">{value ?? '–'}{unit && <span>{unit}</span>}</div>
      {sub && <div className="ps-stat-sub">{sub}</div>}
    </div>
  )
}

/** Shown wherever a section still uses placeholder data. */
export function MockBanner({ children }) {
  return <div className="ps-mock">🧪 <b>Placeholder data</b> · {children}</div>
}

/** Shown wherever risk comes from the provisional index rather than a trained model. */
export function ProvisionalNote() {
  return (
    <div className="ps-note">
      Risk = provisional index from <b>real</b> rainfall (IMD) and groundwater wells (NWDP).
      It will be replaced by the trained ML models.
    </div>
  )
}

export const pct = (v) => (v == null ? '–' : `${v > 0 ? '+' : ''}${Math.round(v)}%`)
export const m = (v) => (v == null ? '–' : `${v > 0 ? '+' : ''}${v.toFixed(1)} m`)

export function Loading({ what = 'data' }) {
  return <div className="ps-loading">⏳ Loading {what}…</div>
}

export function ErrorBox({ error }) {
  return <div className="ps-error">⚠️ {error}<br /><small>Is the backend running? <code>cd backend &amp;&amp; uvicorn main:app --port 8000</code></small></div>
}
