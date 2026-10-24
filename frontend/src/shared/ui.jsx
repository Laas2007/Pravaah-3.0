import { RISK_COLOR } from '../i18n'
import { RISK_TEXT, useTr } from './lang'

export function RiskBadge({ risk }) {
  const tr = useTr()
  if (!risk) return <span className="ps-badge muted">{tr('no data', 'ದತ್ತಾಂಶ ಇಲ್ಲ')}</span>
  return <span className="ps-badge" style={{ background: RISK_COLOR[risk] }}>{tr(RISK_TEXT[risk].en, RISK_TEXT[risk].kn)}</span>
}

const TAG = { real: ['Real', 'ನೈಜ'], estimated: ['Estimated', 'ಅಂದಾಜು'], simulated: ['Simulated', 'ಅನುಕರಣೆ'] }

/** Small label saying whether a number is real, estimated or simulated data. */
export function DataTag({ k }) {
  const tr = useTr()
  return <span className={`data-tag ${k}`}>{tr(...TAG[k])}</span>
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
  const tr = useTr()
  return <div className="ps-mock"><b>{tr('Placeholder data', 'ತಾತ್ಕಾಲಿಕ ದತ್ತಾಂಶ')}</b> · {children}</div>
}

/** Explains where the risk level comes from (ML forecast or the provisional index). */
export function ProvisionalNote({ model }) {
  const tr = useTr()
  if (model && model.startsWith('m2')) {
    return (
      <div className="ps-note">
        {tr(<>Risk = <b>ML groundwater forecast</b> from 2,664 real monitoring wells. Critical: at stress now or likely within
          90 days · High: likely within 6 months · Medium (watch): possible within 6 months in a dry year.</>,
        <>ಅಪಾಯ = 2,664 ನೈಜ ಮೇಲ್ವಿಚಾರಣಾ ಬಾವಿಗಳಿಂದ <b>ML ಅಂತರ್ಜಲ ಮುನ್ಸೂಚನೆ</b>. ಗಂಭೀರ: ಈಗಲೇ ಒತ್ತಡದಲ್ಲಿ ಅಥವಾ 90 ದಿನಗಳಲ್ಲಿ
          ಸಾಧ್ಯತೆ · ಹೆಚ್ಚು: 6 ತಿಂಗಳೊಳಗೆ ಸಾಧ್ಯತೆ · ಮಧ್ಯಮ (ಎಚ್ಚರಿಕೆ): ಒಣ ವರ್ಷದಲ್ಲಿ 6 ತಿಂಗಳೊಳಗೆ ಸಂಭವ.</>)}{' '}
        <a href="/#model">{tr('How accurate is it?', 'ಎಷ್ಟು ನಿಖರ?')}</a>
      </div>
    )
  }
  return (
    <div className="ps-note">
      {tr(<>Risk = provisional index from <b>real</b> rainfall (IMD) and groundwater wells (NWDP).</>,
        <>ಅಪಾಯ = <b>ನೈಜ</b> ಮಳೆ (IMD) ಮತ್ತು ಅಂತರ್ಜಲ ಬಾವಿಗಳ (NWDP) ತಾತ್ಕಾಲಿಕ ಸೂಚ್ಯಂಕ.</>)}
    </div>
  )
}

export const pct = (v) => (v == null ? '–' : `${v > 0 ? '+' : ''}${Math.round(v)}%`)
export const m = (v) => (v == null ? '–' : `${v > 0 ? '+' : ''}${v.toFixed(1)} m`)

export function Loading({ what = 'data' }) {
  const tr = useTr()
  return <div className="ps-loading">{tr(`Loading ${what}…`, 'ಲೋಡ್ ಆಗುತ್ತಿದೆ…')}</div>
}

export function ErrorBox({ error }) {
  return <div className="ps-error">{error}<br /><small>Is the backend running? <code>cd backend &amp;&amp; uvicorn main:app --port 8000</code></small></div>
}
