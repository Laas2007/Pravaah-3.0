import { useState } from 'react'
import { RISK_COLOR, RISK_ICON, addDays, fmtDate, rangeText } from './i18n'

export const DRIVER_ICON = {
  rain_deficit: '🌧️', borewell_dependence: '🛠️', population_density: '🏘️',
  commercial_load: '🏢', cauvery_deficit: '🏞️', paved_surface: '🧱',
}
const ACTION_ICONS = ['🪣', '🕳️', '🚰', '♻️', '🔧', '📞']

export function WardSearch({ wards, onSelect, t }) {
  const [q, setQ] = useState('')
  const matches = q.length < 2 ? [] : wards.filter((w) => w.name.toLowerCase().includes(q.toLowerCase())).slice(0, 6)
  return (
    <div className="search">
      <span className="search-icon">🔎</span>
      <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.searchPh} aria-label={t.findArea} />
      {matches.length > 0 && (
        <ul className="search-results">
          {matches.map((w) => (
            <li key={w.idx}>
              <button onClick={() => { onSelect(w.idx); setQ('') }}>
                <span className="dot" style={{ background: RISK_COLOR[w.risk] }} />
                {w.name} <span className="muted">· ward {w.ward_no}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

function Gauge({ pct, label }) {
  const r = 46, c = Math.PI * r
  const color = pct < 30 ? RISK_COLOR.critical : pct < 45 ? RISK_COLOR.high : pct < 60 ? RISK_COLOR.medium : '#2a78d6'
  return (
    <div className="gauge">
      <svg viewBox="0 0 120 70" width="132">
        <path d="M14 62 A46 46 0 0 1 106 62" fill="none" stroke="#e7ecf3" strokeWidth="12" strokeLinecap="round" />
        <path d="M14 62 A46 46 0 0 1 106 62" fill="none" stroke={color} strokeWidth="12" strokeLinecap="round"
          strokeDasharray={`${(pct / 100) * c} ${c}`} />
        <text x="60" y="58" textAnchor="middle" fontSize="20" fontWeight="700" fill="#0b2545">{Math.round(pct)}%</text>
      </svg>
      <div className="gauge-label">💧 {label}</div>
    </div>
  )
}

export function Countdown({ ward, t, lang, riskLabels }) {
  const r = rangeText(ward)
  return (
    <div className="countdown" style={{ '--risk': RISK_COLOR[ward.risk] }} data-tour="countdown">
      <div className="cd-main">
        <span className="risk-pill" style={{ background: RISK_COLOR[ward.risk] }}>
          {RISK_ICON[ward.risk]} {riskLabels[ward.risk][lang]} {t.risk}
        </span>
        {ward.days_mid === 0 ? (
          <div className="cd-big now">{t.already}</div>
        ) : r ? (
          <>
            <div className="cd-label">{t.shortageIn}</div>
            <div className="cd-big">{r}<span>{t.days}</span></div>
            <div className="cd-date">📅 {t.around} {fmtDate(addDays(ward.as_of, ward.days_low), lang)}{ward.days_high <= 365 ? ` – ${fmtDate(addDays(ward.as_of, ward.days_high), lang)}` : ''}</div>
          </>
        ) : (
          <div className="cd-big ok">✅ {t.noShortage}</div>
        )}
      </div>
      <Gauge pct={ward.groundwater_pct} label={t.groundwater} />
    </div>
  )
}

export function WhyList({ drivers, labels, t, lang }) {
  const useDays = drivers.some((d) => d.days > 0)
  const items = drivers.map((d) => ({ ...d, v: useDays ? d.days : d.level_pts })).filter((d) => d.v > 0).slice(0, 4)
  if (!items.length) return <p className="muted">{lang === 'kn' ? 'ಯಾವುದೇ ಪ್ರಮುಖ ಅಪಾಯಕಾರಿ ಅಂಶವಿಲ್ಲ.' : 'No single factor stands out for this ward.'}</p>
  const max = Math.max(...items.map((d) => Math.min(d.v, 365)))
  return (
    <div className="why" data-tour="why">
      {items.map((d, i) => (
        <div key={d.key} className={`why-item ${d.prevents ? 'main' : ''}`}>
          <div className="why-icon">{DRIVER_ICON[d.key]}</div>
          <div className="why-body">
            <div className="why-label">{labels[d.key]?.[lang] ?? d.label}</div>
            <div className="why-bar"><div style={{ width: `${(Math.min(d.v, 365) / max) * 100}%` }} /></div>
            <div className="why-value">
              {i === 0 && d.prevents && <b className="tag-main">{lang === 'kn' ? 'ಮುಖ್ಯ ಕಾರಣ' : 'MAIN CAUSE'}</b>}
              {useDays ? (d.prevents ? t.preventsYear : `${d.v} ${t.daysSooner}`) : `${t.lowersLevel} ${d.v} ${t.pts}`}
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}

export default function CitizenView({ wards, detail, onSelect, t, lang, meta, openChat }) {
  return (
    <div className="panel-inner">
      <WardSearch wards={wards} onSelect={onSelect} t={t} />
      {!detail ? (
        <div className="empty">
          <div className="empty-icon">📍</div>
          <p>{t.clickMap}</p>
          <div className="quick-picks">
            {['Whitefield', 'Mahadevapura', 'Puttenahalli - Sarakki Lake', 'Malleswaram'].map((n) => {
              const w = wards.find((x) => x.name === n)
              return w ? <button key={n} onClick={() => onSelect(w.idx)}><span className="dot" style={{ background: RISK_COLOR[w.risk] }} />{n}</button> : null
            })}
          </div>
        </div>
      ) : (
        <>
          <div className="area-head">
            <div className="muted small">{t.yourArea} · ward {detail.ward_no}</div>
            <h2>{detail.name}</h2>
          </div>
          <Countdown ward={detail} t={t} lang={lang} riskLabels={meta.risk_labels} />
          <h3>{t.why}</h3>
          <p className="muted small">{t.whyHint}</p>
          <WhyList drivers={detail.drivers} labels={meta.driver_labels} t={t} lang={lang} />
          <h3>{t.whatToDo}</h3>
          <div className="actions">
            {detail.actions.map((a, i) => (
              <div key={a.en} className="action"><span>{ACTION_ICONS[i % ACTION_ICONS.length]}</span>{a[lang]}</div>
            ))}
          </div>
          <button className="ask-btn" onClick={openChat}>💬 {t.askAbout(detail.name)}</button>
        </>
      )}
    </div>
  )
}
