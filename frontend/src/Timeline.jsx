import { useEffect, useMemo, useState } from 'react'
import { fmtDate } from './i18n'

const iso = (d) => d.toISOString().slice(0, 10)

// Weekly scrubber over the whole data period. Every position re-runs the model "as of" that date.
export default function Timeline({ asOf, setAsOf, meta, lang }) {
  const [playing, setPlaying] = useState(false)
  const dates = useMemo(() => {
    const out = []
    const end = new Date(meta.data_until + 'T00:00:00Z')
    const start = new Date(meta.min_as_of + 'T00:00:00Z')
    for (let d = new Date(end); d >= start; d.setUTCDate(d.getUTCDate() - 7)) out.unshift(iso(d))
    return out
  }, [meta])

  const idx = useMemo(() => {
    let best = 0
    dates.forEach((d, i) => { if (d <= asOf) best = i })
    return best
  }, [dates, asOf])

  useEffect(() => {
    if (!playing) return
    if (idx >= dates.length - 1) { setPlaying(false); return }
    const h = setTimeout(() => setAsOf(dates[idx + 1]), 650)
    return () => clearTimeout(h)
  }, [playing, idx, dates, setAsOf])

  const pos = (d) => `${(dates.findIndex((x) => x >= d) / (dates.length - 1)) * 100}%`
  const years = [...new Set(dates.map((d) => d.slice(0, 4)))].filter((y) => dates.some((d) => d.startsWith(y + '-01')))
  const crisis = meta.crisis_2024.date

  return (
    <div className="timeline" data-tour="timeline">
      <button className="play" onClick={() => setPlaying(!playing)} aria-label={playing ? 'Pause' : 'Play'}>
        {playing ? '❚❚' : '▶'}
      </button>
      <div className="tl-date">
        <div className="tl-label">{lang === 'kn' ? 'ಮುನ್ಸೂಚನೆ ದಿನಾಂಕ' : 'Forecast as of'}</div>
        <div className="tl-value">{fmtDate(asOf, lang)}</div>
      </div>
      <div className="tl-track">
        <input type="range" min={0} max={dates.length - 1} value={idx}
          onChange={(e) => { setPlaying(false); setAsOf(dates[+e.target.value]) }} aria-label="Forecast date" />
        <div className="tl-ticks">
          {years.map((y) => <span key={y} style={{ left: pos(`${y}-01-01`) }}>{y}</span>)}
        </div>
        <button className="tl-crisis" style={{ left: pos(crisis) }} onClick={() => setAsOf('2023-12-01')} title="Jump to just before the 2024 crisis">
          ⚠ {lang === 'kn' ? '2024 ಬಿಕ್ಕಟ್ಟು' : '2024 crisis'}
        </button>
      </div>
      <button className="tl-today" onClick={() => setAsOf(meta.data_until)}>{lang === 'kn' ? 'ಇಂದು' : 'Latest'}</button>
    </div>
  )
}
