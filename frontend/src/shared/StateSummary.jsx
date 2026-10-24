// Bengaluru-style hero card for the taluk platforms: big count, risk distribution bar, most urgent places.
import { RISK_COLOR, RISK_ORDER, fmtDate } from '../i18n'
import { RISK_TEXT, useTr } from './lang'

/** items: [{key, name, sub, risk, right}] (already sorted most urgent first); text: sentence after the big number. */
export default function StateSummary({ kicker, asOf, items, text, urgentTitle, onPick, atRisk = ['critical', 'high'] }) {
  const tr = useTr()
  const n = items.filter((x) => atRisk.includes(x.risk)).length
  const total = items.length || 1
  return (
    <>
      <div className="hero-card" data-tour="summary">
        <div className="hero-kicker">{kicker} · {fmtDate(asOf, tr.lang)}</div>
        <div className="hero-number">{n}<span>/{items.length}</span></div>
        <div className="hero-text">{text}</div>
        <div className="dist-bar" role="img" aria-label="By risk level">
          {RISK_ORDER.map((r) => {
            const c = items.filter((x) => x.risk === r).length
            return c ? <div key={r} style={{ width: `${(c / total) * 100}%`, background: RISK_COLOR[r] }} title={`${r}: ${c}`} /> : null
          })}
        </div>
        <div className="dist-legend">
          {RISK_ORDER.map((r) => (
            <span key={r}><i style={{ background: RISK_COLOR[r] }} />{tr(RISK_TEXT[r].en, RISK_TEXT[r].kn)} <b>{items.filter((x) => x.risk === r).length}</b></span>
          ))}
        </div>
      </div>
      {urgentTitle && (
        <>
          <h3>{urgentTitle}</h3>
          <div className="urgent">
            {items.slice(0, 6).map((x) => (
              <button key={x.key} className="urgent-row" onClick={() => onPick?.(x)}>
                <span className="dot" style={{ background: RISK_COLOR[x.risk] }} />
                <span className="urgent-name">{x.name}<span className="muted small"> · {x.sub}</span></span>
                <span className="urgent-days">{x.right}</span>
                <span className="chev">›</span>
              </button>
            ))}
          </div>
        </>
      )}
    </>
  )
}

/** Taluk items for StateSummary from /api/core/indicators rows, most urgent first. */
export function talukItems(rows, tr) {
  const order = { critical: 0, high: 1, medium: 2, low: 3 }
  return [...rows].filter(Boolean).sort((a, b) =>
    order[a.risk] - order[b.risk] || (a.days_mid ?? 999) - (b.days_mid ?? 999) || (b.stress ?? 0) - (a.stress ?? 0)
  ).map((r) => ({
    key: r.idx, idx: r.idx, name: r.name, sub: r.district, risk: r.risk,
    right: r.days_mid == null ? '–' : r.days_mid === 0 ? tr('now', 'ಈಗ')
      : r.days_mid <= 183 ? tr(`${Math.round(r.days_mid)} d`, `${Math.round(r.days_mid)} ದಿ`)
        : r.days_low != null && r.days_low <= 183 ? tr(`${Math.round(r.days_low)} d if dry`, `ಒಣಗಿದರೆ ${Math.round(r.days_low)} ದಿ`) : '6+ mo',
  }))
}
