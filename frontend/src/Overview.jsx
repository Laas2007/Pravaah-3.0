import { RISK_COLOR, RISK_ICON, RISK_ORDER, fmtDate, rangeText } from './i18n'

const STEPS = {
  en: [
    ['🌧️', 'Real data in', 'Daily rainfall (IMD rain gauges, 2014–today), Cauvery catchment rain, 243 BBMP ward boundaries'],
    ['⚖️', 'Water balance per ward', 'Recharge − borewell draw + pipe seepage, simulated every day for every ward'],
    ['📅', 'Forecast + reasons', '30 rainfall scenarios → a days-to-shortage range, and why it is happening'],
  ],
  kn: [
    ['🌧️', 'ನೈಜ ದತ್ತಾಂಶ', 'ದೈನಂದಿನ ಮಳೆ (IMD ಮಳೆ ಮಾಪಕಗಳು, 2014–ಇಂದು), ಕಾವೇರಿ ಜಲಾನಯನ ಮಳೆ, 243 BBMP ವಾರ್ಡ್ ಗಡಿಗಳು'],
    ['⚖️', 'ಪ್ರತಿ ವಾರ್ಡ್ ಜಲ ಸಮತೋಲನ', 'ಮರುಪೂರಣ − ಕೊಳವೆಬಾವಿ ಬಳಕೆ + ಪೈಪ್ ಸೋರಿಕೆ, ಪ್ರತಿದಿನ ಲೆಕ್ಕಾಚಾರ'],
    ['📅', 'ಮುನ್ಸೂಚನೆ + ಕಾರಣಗಳು', '30 ಮಳೆ ಸನ್ನಿವೇಶಗಳು → ಕೊರತೆಗೆ ದಿನಗಳ ಶ್ರೇಣಿ ಮತ್ತು ಕಾರಣ'],
  ],
}

export default function Overview({ wards, asOf, meta, lang, onSelect, goTo }) {
  const atRisk = wards.filter((w) => w.risk === 'critical' || w.risk === 'high')
  const people = atRisk.reduce((s, w) => s + w.inputs.population, 0)
  const urgent = [...wards].sort((a, b) => a.days_mid - b.days_mid || a.groundwater_pct - b.groundwater_pct).slice(0, 6)
  const total = wards.length || 1
  const kn = lang === 'kn'

  return (
    <div className="panel-inner">
      <div className="hero-card">
        <div className="hero-kicker">{kn ? 'ಬೆಂಗಳೂರು · ' : 'Bengaluru · as of '}{fmtDate(asOf, lang)}</div>
        <div className="hero-number">{atRisk.length}<span>/{wards.length}</span></div>
        <div className="hero-text">
          {kn ? <>ವಾರ್ಡ್‌ಗಳಲ್ಲಿ <b>90 ದಿನಗಳೊಳಗೆ</b> ನೀರಿನ ಕೊರತೆ ನಿರೀಕ್ಷೆ — ಸುಮಾರು <b>{(people / 1e5).toFixed(1)} ಲಕ್ಷ</b> ಜನರು</>
            : <>wards are expected to run short of water <b>within 90 days</b>, affecting about <b>{(people / 1e5).toFixed(1)} lakh</b> people</>}
        </div>
        <div className="dist-bar" role="img" aria-label="Wards by risk level">
          {RISK_ORDER.map((r) => {
            const n = wards.filter((w) => w.risk === r).length
            return n ? <div key={r} style={{ width: `${(n / total) * 100}%`, background: RISK_COLOR[r] }} title={`${r}: ${n}`} /> : null
          })}
        </div>
        <div className="dist-legend">
          {RISK_ORDER.map((r) => (
            <span key={r}><i style={{ background: RISK_COLOR[r] }} />{RISK_ICON[r]} {meta.risk_labels[r][lang]} <b>{wards.filter((w) => w.risk === r).length}</b></span>
          ))}
        </div>
      </div>

      <h3>{kn ? 'ಅತ್ಯಂತ ತುರ್ತು ವಾರ್ಡ್‌ಗಳು' : 'Most urgent wards'}</h3>
      <div className="urgent">
        {urgent.map((w) => (
          <button key={w.idx} className="urgent-row" onClick={() => { onSelect(w.idx); goTo('area') }}>
            <span className="dot" style={{ background: RISK_COLOR[w.risk] }} />
            <span className="urgent-name">{w.name}</span>
            <span className="urgent-days">{w.days_mid === 0 ? (kn ? 'ಈಗ' : 'now') : `${rangeText(w) ?? '365+'} ${kn ? 'ದಿನ' : 'd'}`}</span>
            <span className="chev">›</span>
          </button>
        ))}
      </div>

      <h3>{kn ? 'ಇದು ಹೇಗೆ ಕೆಲಸ ಮಾಡುತ್ತದೆ' : 'How it works'}</h3>
      <div className="how">
        {STEPS[lang].map(([icon, title, text], i) => (
          <div key={title} className="how-step">
            <div className="how-icon">{icon}</div>
            <div><b>{i + 1}. {title}</b><p>{text}</p></div>
          </div>
        ))}
      </div>

      <div className="feature-grid">
        <button onClick={() => goTo('area')}><span>📍</span><b>{kn ? 'ನನ್ನ ಪ್ರದೇಶ' : 'My Area'}</b><small>{kn ? 'ಸರಳ ಭಾಷೆಯಲ್ಲಿ ಅಪಾಯ' : 'Risk in plain words'}</small></button>
        <button onClick={() => goTo('official')}><span>🏛️</span><b>{kn ? 'ಅಧಿಕಾರಿಗಳು' : 'Officials'}</b><small>{kn ? 'ಶ್ರೇಣಿ, ಯೋಜನೆ' : 'Rankings & planning'}</small></button>
        <button onClick={() => goTo('backtest')}><span>⏪</span><b>{kn ? 'ಟೈಮ್ ಮೆಷಿನ್' : 'Time Machine'}</b><small>{kn ? '2024 ಬಿಕ್ಕಟ್ಟು ಪರೀಕ್ಷೆ' : 'Tested on the 2024 crisis'}</small></button>
      </div>
    </div>
  )
}
