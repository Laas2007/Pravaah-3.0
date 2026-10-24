import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, ReferenceLine, CartesianGrid } from 'recharts'
import { core } from '../api'
import { useLoad } from './hooks'
import { ErrorBox, Loading, RiskBadge, Stat, m, pct } from './ui'

/** Real-data summary for one taluk: rain vs normal, groundwater now + history. Reused by several platforms. */
export default function TalukDetail({ idx, asOf, onClose, color = '#2a78d6' }) {
  const { data: t, error } = useLoad(() => core.taluk(idx, asOf), [idx, asOf])
  if (error) return <ErrorBox error={error} />
  if (!t) return <Loading what="taluk" />
  const ind = t.indicators
  const hist = t.groundwater_history.filter((h) => h.depth != null)
  return (
    <div className="ps-card">
      <div className="ps-card-head">
        <div><h2>{t.name}</h2><div className="muted small">{t.district} district · {t.area_km2} km²</div></div>
        <RiskBadge risk={t.risk} />
        {onClose && <button className="ps-x" onClick={onClose} aria-label="Close">✕</button>}
      </div>
      <div className="ps-stats">
        <Stat label="Rain, last 12 months" value={Math.round(ind.rain_365d_mm)} unit="mm" sub={`${pct(ind.rain_365d_dev_pct)} vs normal`}
          tone={ind.rain_365d_dev_pct < -20 ? 'bad' : ''} />
        <Stat label="Rain, last 3 months" value={Math.round(ind.rain_90d_mm)} unit="mm" sub={`${pct(ind.rain_90d_dev_pct)} vs normal`}
          tone={ind.rain_90d_dev_pct < -30 ? 'bad' : ''} />
        <Stat label="Groundwater depth" value={ind.gw_depth_m?.toFixed(1)} unit="m" sub={`${m(ind.gw_anom_m)} vs normal · ${ind.gw_month || 'no reading'}`}
          tone={ind.gw_anom_m > 1 ? 'bad' : ''} />
      </div>
      <h3>Groundwater depth, monthly wells (m below ground)</h3>
      <div style={{ height: 180 }}>
        <ResponsiveContainer>
          <LineChart data={hist} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#eef1f5" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={23} />
            <YAxis reversed tick={{ fontSize: 10 }} />
            <Tooltip formatter={(v) => [`${v} m`, 'depth']} />
            <ReferenceLine x={asOf.slice(0, 7)} stroke="#999" strokeDasharray="3 3" />
            <Line dataKey="depth" stroke={color} dot={false} strokeWidth={2} isAnimationActive={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <div className="muted small">Lower on the chart = deeper water = worse. Source: NWDP well readings.</div>
    </div>
  )
}
