import { Link, NavLink, useSearchParams } from 'react-router-dom'
import { PLATFORMS, platform } from './platforms'
import { RISK_COLOR, RISK_ORDER } from '../i18n'

/** Common frame for every platform: header with platform switcher, date bar, map + side panel. */
export default function PlatformShell({ which, asOf, setAsOf, meta, map, children }) {
  const p = platform(which)
  const [params] = useSearchParams()
  const qs = params.toString() ? `?${params}` : ''
  return (
    <div className="ps" style={{ '--pc': p.color }}>
      <div className="ps-header">
        <Link to={`/${qs}`} className="ps-brand">
          <span className="ps-logo">💧</span>
          <span><b>Pravaah</b><small>Karnataka</small></span>
        </Link>
        <div className="ps-title"><span>{p.icon}</span>{p.en}</div>
        <nav className="ps-nav">
          {PLATFORMS.map((x) => (
            <NavLink key={x.key} to={`${x.path}${qs}`} title={x.en} className={({ isActive }) => (isActive ? 'on' : '')}>
              {x.icon}
            </NavLink>
          ))}
        </nav>
      </div>
      {setAsOf && <DateBar asOf={asOf} setAsOf={setAsOf} meta={meta} />}
      <div className="ps-main">
        {map && <section className="ps-map-col">{map}</section>}
        <aside className="ps-panel">{children}</aside>
      </div>
    </div>
  )
}

export function DateBar({ asOf, setAsOf, meta }) {
  if (!meta || !asOf) return <div className="ps-datebar" />
  return (
    <div className="ps-datebar">
      <label>📅 As of
        <input type="date" value={asOf} min={meta.min_as_of} max={meta.climate_until}
          onChange={(e) => e.target.value && setAsOf(e.target.value)} />
      </label>
      <div className="ps-presets">
        {meta.story_dates.map((s) => (
          <button key={s.date} className={s.date === asOf ? 'on' : ''} onClick={() => setAsOf(s.date)}>{s.label}</button>
        ))}
      </div>
      <span className="ps-datebar-note">Only data available on this date is used</span>
    </div>
  )
}

export function RiskLegend() {
  return (
    <>
      {RISK_ORDER.map((r) => <span key={r}><i style={{ background: RISK_COLOR[r] }} />{r}</span>)}
    </>
  )
}
