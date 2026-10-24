import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { core } from '../api'
import { useLoad } from './hooks'
import { ErrorBox, Loading, RiskBadge, Stat, m, pct } from './ui'

const daysText = (d) => (d == null ? '–' : d === 0 ? 'now' : d >= 366 ? '6+ months' : `${Math.round(d)} days`)

/** Real-data summary + M2 groundwater forecast for one taluk. Reused by all platforms. */
export default function TalukDetail({ idx, asOf, onClose, color = '#2a78d6' }) {
  const { data: t, error } = useLoad(() => core.taluk(idx, asOf), [idx, asOf])
  if (error) return <ErrorBox error={error} />
  if (!t) return <Loading what="taluk" />
  const ind = t.indicators
  const fc = t.forecast
  return (
    <div className="ps-card">
      <div className="ps-card-head">
        <div><h2>{t.name}</h2><div className="muted small">{t.district} district · {t.area_km2} km²</div></div>
        <RiskBadge risk={t.risk} />
        {onClose && <button className="ps-x" onClick={onClose} aria-label="Close">✕</button>}
      </div>

      {fc ? <Forecast fc={fc} hist={t.groundwater_history} color={color} /> : (
        <div className="ps-note">No monitoring wells report here recently, so risk uses the provisional index (rain + groundwater anomaly).</div>
      )}

      <div className="ps-stats">
        <Stat label="Rain, last 12 months" value={Math.round(ind.rain_365d_mm)} unit="mm" sub={`${pct(ind.rain_365d_dev_pct)} vs normal`}
          tone={ind.rain_365d_dev_pct < -20 ? 'bad' : ''} />
        <Stat label="Rain, last 3 months" value={Math.round(ind.rain_90d_mm)} unit="mm" sub={`${pct(ind.rain_90d_dev_pct)} vs normal`}
          tone={ind.rain_90d_dev_pct < -30 ? 'bad' : ''} />
        <Stat label="Groundwater depth" value={ind.gw_depth_m?.toFixed(1)} unit="m" sub={`${m(ind.gw_anom_m)} vs normal · ${ind.gw_month || 'no reading'}`}
          tone={ind.gw_anom_m > 1 ? 'bad' : ''} />
      </div>
    </div>
  )
}

function Forecast({ fc, hist, color }) {
  // last 24 months of observed anomaly + the 6-month forecast band
  const past = hist.filter((h) => h.anom != null).slice(-24).map((h) => ({ month: h.month, observed: h.anom }))
  const last = past[past.length - 1]
  const future = fc.path.map((p) => ({ month: p.month, mid: p.p50, band: [p.p10, p.p90] }))
  if (last) future.unshift({ month: last.month, mid: last.observed, band: [last.observed, last.observed] })
  const data = [...past.slice(0, -1), ...future]
  const maxM = Math.max(...fc.drivers.map((d) => Math.abs(d.metres)), 0.5)
  return (
    <>
      <div className="ps-forecast">
        <div className="ps-forecast-big">{daysText(fc.days_mid)}</div>
        <div>
          <b>until groundwater reaches stress level</b>
          <div className="small muted">likely range {daysText(fc.days_low)} – {daysText(fc.days_high)} · ML forecast from {fc.origin_month} well readings</div>
        </div>
      </div>
      <h3>Groundwater vs normal: past 2 years + next 6 months (m deeper than normal)</h3>
      <div style={{ height: 190 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#eef1f5" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={5} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip formatter={(v) => (Array.isArray(v) ? `${v[0]} to ${v[1]} m` : `${v} m`)} />
            <ReferenceLine y={fc.threshold_m} stroke="#d03b3b" strokeDasharray="4 3"
              label={{ value: 'stress', fontSize: 10, fill: '#d03b3b', position: 'insideTopLeft' }} />
            <ReferenceLine y={0} stroke="#9aa6b5" />
            <Area dataKey="band" stroke="none" fill={color} fillOpacity={0.18} isAnimationActive={false} name="10–90% range" />
            <Line dataKey="mid" stroke={color} strokeDasharray="5 3" dot={false} strokeWidth={2} isAnimationActive={false} name="forecast" />
            <Line dataKey="observed" stroke={color} dot={false} strokeWidth={2} isAnimationActive={false} name="observed" />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="muted small">Up = deeper water = worse. Solid = well readings, dashed = forecast, shaded = likely range across past years' rain.</div>
      {fc.drivers.length > 0 && (
        <>
          <h3>Why: effect on groundwater 3 months from now</h3>
          <div className="ps-why">
            {fc.drivers.map((d) => (
              <div key={d.key} className="ps-why-row">
                <span>{d.label}</span>
                <div className="ps-why-bar"><i style={{ width: `${(Math.abs(d.metres) / maxM) * 100}%`, background: d.metres > 0 ? '#d03b3b' : '#0ca30c' }} /></div>
                <b>{Math.abs(d.metres) < 0.05 ? 'no effect' : d.metres > 0 ? `${d.metres.toFixed(1)} m deeper` : `${(-d.metres).toFixed(1)} m shallower`}</b>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}
