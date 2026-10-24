import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { core } from '../api'
import { useLoad } from './hooks'
import { DRIVER_TEXT, useTr } from './lang'
import TimeMachine from './TimeMachine'
import { talukHeadline, talukReasons } from './explain'
import { ErrorBox, Loading, RiskBadge, Stat, m, pct } from './ui'

/** Real-data summary + M2 groundwater forecast (+ Time Machine) for one taluk. Reused by all platforms. */
export default function TalukDetail({ idx, asOf, onClose, color = '#2a78d6' }) {
  const tr = useTr()
  const { data: t, error } = useLoad(() => core.taluk(idx, asOf), [idx, asOf])
  if (error) return <ErrorBox error={error} />
  if (!t) return <Loading what="taluk" />
  const ind = t.indicators
  const fc = t.forecast
  return (
    <>
      <div className="ps-card">
        <div className="ps-card-head">
          <div><h2>{t.name}</h2><div className="muted small">{tr(`${t.district} district`, `${t.district} ಜಿಲ್ಲೆ`)} · {t.area_km2} km²</div></div>
          <RiskBadge risk={t.risk} />
          {onClose && <button className="ps-x" onClick={onClose} aria-label="Close">✕</button>}
        </div>

        {fc ? <Forecast fc={fc} risk={t.risk} hist={t.groundwater_history} color={color} /> : (
          <div className="ps-note">{tr('No monitoring wells report here recently, so risk uses the provisional index (rain + groundwater anomaly).',
            'ಇಲ್ಲಿ ಇತ್ತೀಚೆಗೆ ಮೇಲ್ವಿಚಾರಣಾ ಬಾವಿ ದತ್ತಾಂಶ ಇಲ್ಲ; ಅಪಾಯ ತಾತ್ಕಾಲಿಕ ಸೂಚ್ಯಂಕದಿಂದ (ಮಳೆ + ಅಂತರ್ಜಲ ವ್ಯತ್ಯಾಸ).')}</div>
        )}

        <div className="ps-stats">
          <Stat label={tr('Rain, last 12 months', 'ಕಳೆದ 12 ತಿಂಗಳ ಮಳೆ')} value={Math.round(ind.rain_365d_mm)} unit="mm"
            sub={tr(`${pct(ind.rain_365d_dev_pct)} vs normal`, `ವಾಡಿಕೆಗಿಂತ ${pct(ind.rain_365d_dev_pct)}`)} tone={ind.rain_365d_dev_pct < -20 ? 'bad' : ''} />
          <Stat label={tr('Rain, last 3 months', 'ಕಳೆದ 3 ತಿಂಗಳ ಮಳೆ')} value={Math.round(ind.rain_90d_mm)} unit="mm"
            sub={tr(`${pct(ind.rain_90d_dev_pct)} vs normal`, `ವಾಡಿಕೆಗಿಂತ ${pct(ind.rain_90d_dev_pct)}`)} tone={ind.rain_90d_dev_pct < -30 ? 'bad' : ''} />
          <Stat label={tr('Groundwater depth', 'ಅಂತರ್ಜಲ ಆಳ')} value={ind.gw_depth_m?.toFixed(1)} unit="m"
            sub={`${tr(`${m(ind.gw_anom_m)} vs normal`, `ವಾಡಿಕೆಗಿಂತ ${m(ind.gw_anom_m)}`)} · ${ind.gw_month || tr('no reading', 'ದತ್ತಾಂಶ ಇಲ್ಲ')}`}
            tone={ind.gw_anom_m > 1 ? 'bad' : ''} />
        </div>
      </div>
      <TimeMachine asOf={asOf} idx={idx} color={color} />
    </>
  )
}

function Forecast({ fc, risk, hist, color }) {
  const tr = useTr()
  const daysText = (d) => (d == null ? '–' : d === 0 ? tr('now', 'ಈಗಲೇ') : d >= 366 ? tr('6+ months', '6+ ತಿಂಗಳು') : tr(`${Math.round(d)} days`, `${Math.round(d)} ದಿನ`))
  // last 24 months of observed anomaly + the 6-month forecast band
  const past = hist.filter((h) => h.anom != null).slice(-24).map((h) => ({ month: h.month, observed: h.anom }))
  const last = past[past.length - 1]
  const future = fc.path.map((p) => ({ month: p.month, mid: p.p50, band: [p.p10, p.p90] }))
  if (last) future.unshift({ month: last.month, mid: last.observed, band: [last.observed, last.observed] })
  const data = [...past.slice(0, -1), ...future]
  const maxM = Math.max(...fc.drivers.map((d) => Math.abs(d.metres)), 0.5)
  const head = talukHeadline(fc, tr)
  return (
    <>
      <div className={`ps-forecast tone-${risk}`} data-tour="forecast">
        <div className="ps-forecast-big">{head.big}</div>
        <div>
          <b>{head.label}</b>
          <div className="small muted">{tr(`range ${daysText(fc.days_low)} (dry year) – ${daysText(fc.days_high)} (wet year) · ML forecast from ${fc.origin_month} well readings`,
            `ವ್ಯಾಪ್ತಿ ${daysText(fc.days_low)} (ಒಣ ವರ್ಷ) – ${daysText(fc.days_high)} (ಮಳೆಯ ವರ್ಷ) · ${fc.origin_month} ಬಾವಿ ದತ್ತಾಂಶದಿಂದ ML ಮುನ್ಸೂಚನೆ`)}</div>
        </div>
      </div>
      <div className="ps-reasons">
        <b>{tr('Why this number?', 'ಈ ಸಂಖ್ಯೆ ಏಕೆ?')}</b>
        <ul>{talukReasons(fc, risk, tr).map((r, i) => <li key={i}>{r}</li>)}</ul>
      </div>
      <h3>{tr('Groundwater vs normal: past 2 years + next 6 months (m deeper than normal)', 'ಅಂತರ್ಜಲ vs ವಾಡಿಕೆ: ಕಳೆದ 2 ವರ್ಷ + ಮುಂದಿನ 6 ತಿಂಗಳು (ವಾಡಿಕೆಗಿಂತ ಮೀ. ಆಳ)')}</h3>
      <div style={{ height: 190 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
            <CartesianGrid stroke="#eef1f5" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 10 }} interval={5} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip formatter={(v) => (Array.isArray(v) ? `${v[0]} to ${v[1]} m` : `${v} m`)} />
            <ReferenceLine y={fc.threshold_m} stroke="#d03b3b" strokeDasharray="4 3"
              label={{ value: tr('stress', 'ಒತ್ತಡ'), fontSize: 10, fill: '#d03b3b', position: 'insideTopLeft' }} />
            <ReferenceLine y={0} stroke="#9aa6b5" />
            <Area dataKey="band" stroke="none" fill={color} fillOpacity={0.18} isAnimationActive={false} name={tr('10–90% range', '10–90% ವ್ಯಾಪ್ತಿ')} />
            <Line dataKey="mid" stroke={color} strokeDasharray="5 3" dot={false} strokeWidth={2} isAnimationActive={false} name={tr('forecast', 'ಮುನ್ಸೂಚನೆ')} />
            <Line dataKey="observed" stroke={color} dot={false} strokeWidth={2} isAnimationActive={false} name={tr('observed', 'ಗಮನಿಸಿದ್ದು')} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <div className="muted small">{tr('Up = deeper water = worse. Solid = well readings, dashed = forecast, shaded = likely range across past years\' rain.',
        'ಮೇಲೆ = ಆಳದ ನೀರು = ಕೆಟ್ಟದು. ಗಟ್ಟಿ ಗೆರೆ = ಬಾವಿ ದತ್ತಾಂಶ, ಚುಕ್ಕೆ ಗೆರೆ = ಮುನ್ಸೂಚನೆ, ಛಾಯೆ = ಹಿಂದಿನ ವರ್ಷಗಳ ಮಳೆಯ ಆಧಾರದ ವ್ಯಾಪ್ತಿ.')}</div>
      {fc.drivers.length > 0 && (
        <>
          <h3>{tr('Why: effect on groundwater 3 months from now', 'ಏಕೆ: 3 ತಿಂಗಳ ನಂತರದ ಅಂತರ್ಜಲದ ಮೇಲೆ ಪರಿಣಾಮ')}</h3>
          <div className="ps-why">
            {fc.drivers.map((d) => (
              <div key={d.key} className="ps-why-row">
                <span>{tr(DRIVER_TEXT[d.key]?.en || d.label, DRIVER_TEXT[d.key]?.kn)}</span>
                <div className="ps-why-bar"><i style={{ width: `${(Math.abs(d.metres) / maxM) * 100}%`, background: d.metres > 0 ? '#d03b3b' : '#0ca30c' }} /></div>
                <b>{Math.abs(d.metres) < 0.05 ? tr('no effect', 'ಪರಿಣಾಮ ಇಲ್ಲ')
                  : d.metres > 0 ? tr(`${d.metres.toFixed(1)} m deeper`, `${d.metres.toFixed(1)} ಮೀ. ಆಳ`)
                    : tr(`${(-d.metres).toFixed(1)} m shallower`, `${(-d.metres).toFixed(1)} ಮೀ. ಮೇಲೆ`)}</b>
              </div>
            ))}
          </div>
        </>
      )}
    </>
  )
}
