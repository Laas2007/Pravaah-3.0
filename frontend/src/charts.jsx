import {
  Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from 'recharts'
import { RISK_COLOR, fmtDate } from './i18n'

const AXIS = { stroke: '#898781', fontSize: 11 }
const SERIES = '#2a78d6'

// Groundwater: simulated past level, forecast median + 10–90% band, and (in backtests) what actually followed.
export function GroundwaterChart({ ts, asOf, lang }) {
  const rows = [
    ...ts.past.map((p) => ({ date: p.date, level: p.level })),
    ...ts.future.map((f) => ({ date: f.date, mid: f.mid, band: [f.lo, f.hi] })),
  ]
  const actual = Object.fromEntries(ts.actual_after.map((a) => [a.date, a.level]))
  rows.forEach((r) => { if (actual[r.date] !== undefined) r.actual = actual[r.date] })
  const last = rows.findIndex((r) => r.mid !== undefined)
  if (last > 0) rows[last - 1].mid = rows[last - 1].level
  const hasActual = ts.actual_after.length > 0

  return (
    <div>
      <ResponsiveContainer width="100%" height={210}>
        <ComposedChart data={rows} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="#ecebe7" vertical={false} />
          <XAxis dataKey="date" tick={AXIS} tickFormatter={(d) => d.slice(0, 7)} minTickGap={40} stroke="#d6d5d0" />
          <YAxis domain={[0, 100]} tick={AXIS} stroke="#d6d5d0" unit="%" />
          <Tooltip
            formatter={(v, n) => [Array.isArray(v) ? `${v[0]}–${v[1]}%` : `${v}%`, n]}
            labelFormatter={(d) => fmtDate(d, lang)}
          />
          <Area dataKey="band" name="Forecast range (10–90%)" fill={SERIES} fillOpacity={0.15} stroke="none" isAnimationActive={false} />
          <Line dataKey="level" name="Groundwater (simulated)" stroke="#52514e" strokeWidth={2} dot={false} isAnimationActive={false} />
          <Line dataKey="mid" name="Forecast (median)" stroke={SERIES} strokeWidth={2} strokeDasharray="5 3" dot={false} isAnimationActive={false} />
          {hasActual && <Line dataKey="actual" name="What happened next" stroke="#0b0b0b" strokeWidth={1.5} dot={false} isAnimationActive={false} />}
          <ReferenceLine y={ts.shortage_level} stroke={RISK_COLOR.critical} strokeDasharray="4 4"
            label={{ value: 'Shortage threshold', fill: RISK_COLOR.critical, fontSize: 10, position: 'insideBottomLeft' }} />
          <ReferenceLine x={asOf} stroke="#898781" label={{ value: 'as of', fill: '#898781', fontSize: 10, position: 'insideTopRight' }} />
        </ComposedChart>
      </ResponsiveContainer>
      <div className="chart-legend">
        <span><i style={{ background: '#52514e' }} />Simulated level</span>
        <span><i style={{ background: SERIES }} />Forecast median</span>
        <span><i style={{ background: SERIES, opacity: 0.25, height: 8 }} />Forecast range</span>
        {hasActual && <span><i style={{ background: '#0b0b0b' }} />What happened next</span>}
      </div>
    </div>
  )
}

// Horizontal bars: how many days sooner each driver brings the shortage.
export function DriverBars({ drivers, labels, t, lang }) {
  const useDays = drivers.some((d) => d.days > 0)
  const items = drivers
    .map((d) => ({ ...d, v: useDays ? d.days : d.level_pts }))
    .filter((d) => d.v > 0)
    .slice(0, 4)
  if (!items.length) return <p className="muted small">No single factor stands out for this ward.</p>
  const max = Math.max(...items.map((d) => Math.min(d.v, 365)))
  return (
    <div className="bars">
      {items.map((d) => (
        <div key={d.key} className="bar-row" title={labels[d.key]?.en}>
          <div className="bar-label">{labels[d.key]?.[lang] ?? d.label}</div>
          <div className="bar-track">
            <div className="bar-fill" style={{ width: `${(Math.min(d.v, 365) / max) * 100}%` }} />
          </div>
          <div className="bar-value">
            {useDays ? (d.prevents ? t.preventsYear : `${d.v} ${t.daysSooner}`) : `${t.lowersLevel} ${d.v} ${t.pts}`}
          </div>
        </div>
      ))}
    </div>
  )
}
