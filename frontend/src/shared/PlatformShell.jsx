import { useEffect, useMemo, useState } from 'react'
import { Link, NavLink, useSearchParams } from 'react-router-dom'
import { PLATFORMS, platform } from './platforms'
import { RISK_COLOR, RISK_ORDER, fmtDate } from '../i18n'
import { PRESET_KN, RISK_TEXT, useLang, useTr } from './lang'
import Tour, { useTourStep } from './Tour'
import Icon from './Icon'

/** Common frame for every platform: header (platform switcher, language, tour), date bar + timeline, map + panel. */
export default function PlatformShell({ which, asOf, setAsOf, meta, map, children }) {
  const p = platform(which)
  const tr = useTr()
  const [params] = useSearchParams()
  const qs = params.toString() ? `?${params}` : ''
  const [step, setStep] = useTourStep()
  return (
    <div className={`ps lang-${tr.lang}`} style={{ '--pc': p.color }}>
      <div className="ps-header">
        <Link to={`/${qs}`} className="ps-brand">
          <span className="ps-logo"><Icon name="drop" size={20} stroke={2} /></span>
          <span><b>Pravaah</b><small>{tr('Karnataka', 'ಕರ್ನಾಟಕ')}</small></span>
        </Link>
        <div className="ps-title">{tr(p.en, p.kn)}</div>
        <nav className="ps-nav">
          {PLATFORMS.map((x) => (
            <NavLink key={x.key} to={`${x.path}${qs}`} title={tr(x.en, x.kn)} className={({ isActive }) => (isActive ? 'on' : '')}>
              <Icon name={x.icon} size={18} /><span>{tr(x.en, x.kn).split(' ')[0].replace(/[,&]/g, '')}</span>
            </NavLink>
          ))}
        </nav>
        <LangButton />
        <button className="ps-tour-btn" onClick={() => setStep(0)}>{tr('Guided tour', 'ಮಾರ್ಗದರ್ಶಿ ಪ್ರವಾಸ')}</button>
      </div>
      {setAsOf && <DateBar asOf={asOf} setAsOf={setAsOf} meta={meta} />}
      <div className="ps-main">
        {map && <section className="ps-map-col" data-tour="map">{map}</section>}
        <aside className="ps-panel">{children}</aside>
      </div>
      {step != null && <Tour step={step} setStep={setStep} />}
    </div>
  )
}

export function LangButton({ light }) {
  const [lang, setLang] = useLang()
  return (
    <button className={`ps-lang ${light ? 'light' : ''}`} data-tour="lang" onClick={() => setLang(lang === 'en' ? 'kn' : 'en')}
      aria-label={lang === 'en' ? 'Switch language to Kannada' : 'Switch language to English'}>
      <Icon name="globe" size={16} /> {lang === 'en' ? 'ಕನ್ನಡ' : 'English'}
    </button>
  )
}

const iso = (d) => d.toISOString().slice(0, 10)

/** Date picker, story presets and a weekly timeline with play (every position = forecast "as of" that date). */
export function DateBar({ asOf, setAsOf, meta }) {
  const tr = useTr()
  const [playing, setPlaying] = useState(false)
  const dates = useMemo(() => {
    if (!meta) return []
    const out = []
    const end = new Date(meta.climate_until + 'T00:00:00Z')
    const start = new Date(meta.min_as_of + 'T00:00:00Z')
    for (let d = new Date(end); d >= start; d.setUTCDate(d.getUTCDate() - 14)) out.unshift(iso(d))
    return out
  }, [meta])
  const idx = useMemo(() => { let b = 0; dates.forEach((d, i) => { if (d <= asOf) b = i }); return b }, [dates, asOf])

  useEffect(() => {
    if (!playing) return
    if (idx >= dates.length - 1) { setPlaying(false); return }
    const h = setTimeout(() => setAsOf(dates[idx + 1]), 700)
    return () => clearTimeout(h)
  }, [playing, idx, dates, setAsOf])

  if (!meta || !asOf) return <div className="ps-datebar" />
  const years = [...new Set(dates.map((d) => d.slice(0, 4)))]
  const pos = (y) => `${(Math.max(dates.findIndex((x) => x >= `${y}-01-01`), 0) / (dates.length - 1)) * 100}%`
  return (
    <div className="ps-datebar" data-tour="datebar">
      <label>{tr('As of', 'ದಿನಾಂಕ')}
        <input type="date" value={asOf} min={meta.min_as_of} max={meta.climate_until}
          onChange={(e) => e.target.value && setAsOf(e.target.value)} />
      </label>
      <div className="ps-presets">
        {meta.story_dates.map((s) => (
          <button key={s.date} className={s.date === asOf ? 'on' : ''} onClick={() => setAsOf(s.date)}>
            {tr(s.label, PRESET_KN[s.label])}
          </button>
        ))}
      </div>
      <div className="ps-timeline">
        <button className="ps-play" onClick={() => setPlaying(!playing)} aria-label={playing ? 'Pause' : 'Play'}><Icon name={playing ? 'pause' : 'play'} size={16} /></button>
        <div className="ps-track">
          <input type="range" min={0} max={dates.length - 1} value={idx} aria-label="Forecast date"
            onChange={(e) => { setPlaying(false); setAsOf(dates[+e.target.value]) }} />
          <div className="ps-ticks">{years.filter((y) => +y % 2 === 0).map((y) => <span key={y} style={{ left: pos(y) }}>{y}</span>)}</div>
        </div>
        <span className="ps-tl-date">{fmtDate(asOf, tr.lang)}</span>
      </div>
      <span className="ps-datebar-note">{tr('Only data available on this date is used', 'ಈ ದಿನಾಂಕದವರೆಗಿನ ದತ್ತಾಂಶ ಮಾತ್ರ ಬಳಸಲಾಗಿದೆ')}</span>
    </div>
  )
}

export function RiskLegend() {
  const tr = useTr()
  return (
    <>
      {RISK_ORDER.map((r) => <span key={r}><i style={{ background: RISK_COLOR[r] }} />{tr(RISK_TEXT[r].en, RISK_TEXT[r].kn)}</span>)}
    </>
  )
}
