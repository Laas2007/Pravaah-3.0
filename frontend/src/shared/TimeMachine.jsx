import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Scatter, Tooltip, XAxis, YAxis } from 'recharts'
import { req } from '../api'
import { useLoad } from './hooks'
import { useTr } from './lang'

/** Time Machine: the forecast made on asOf vs what the wells actually showed afterwards (statewide; + one taluk). */
export default function TimeMachine({ asOf, idx, color = '#2a78d6' }) {
  const tr = useTr()
  const { data: b } = useLoad(() => req(`/api/core/backtest?as_of=${asOf}${idx != null ? `&idx=${idx}` : ''}`), [asOf, idx])
  if (!b) return null
  if (!b.available) {
    return (
      <div className="ps-card ps-tm" data-tour="timemachine">
        <h2>{tr('Time Machine', 'ಟೈಮ್ ಮೆಷಿನ್')}</h2>
        <div className="muted small">{tr('Pick an earlier date to compare the forecast with what really happened.',
          'ಮುನ್ಸೂಚನೆಯನ್ನು ನಿಜವಾಗಿ ನಡೆದುದರೊಂದಿಗೆ ಹೋಲಿಸಲು ಹಿಂದಿನ ದಿನಾಂಕ ಆಯ್ಕೆಮಾಡಿ.')}</div>
      </div>
    )
  }
  const last = b.by_horizon[b.by_horizon.length - 1]
  const s = b.stress
  const oos = b.mode.startsWith('out-of-sample')
  const t = b.taluk
  const data = t?.path.filter((p) => p.p50 != null).map((p) => ({ month: p.month, band: [p.p10, p.p90], mid: p.p50, actual: p.actual }))
  return (
    <div className="ps-card ps-tm" data-tour="timemachine">
      <div className="ps-card-head">
        <div><h2>{tr('Time Machine: forecast vs what happened', 'ಟೈಮ್ ಮೆಷಿನ್: ಮುನ್ಸೂಚನೆ vs ನಿಜವಾಗಿ ನಡೆದದ್ದು')}</h2>
          <div className="muted small">{tr(`Forecast made from ${b.origin_month} readings, checked against the wells up to ${last.month}`,
            `${b.origin_month} ರ ದತ್ತಾಂಶದಿಂದ ಮುನ್ಸೂಚನೆ, ${last.month} ರವರೆಗಿನ ಬಾವಿ ದತ್ತಾಂಶದೊಂದಿಗೆ ಪರಿಶೀಲನೆ`)}</div></div>
        <span className={`ps-tm-mode ${oos ? 'oos' : ''}`}>{oos ? tr('never saw these years', 'ಈ ವರ್ಷಗಳನ್ನು ನೋಡದ ಮಾದರಿ') : tr('in-sample', 'ತರಬೇತಿ ಅವಧಿ')}</span>
      </div>

      {data && data.length > 0 && (
        <>
          <h3>{tr('This taluk: forecast range vs actual (m deeper than normal)', 'ಈ ತಾಲೂಕು: ಮುನ್ಸೂಚನೆ ವ್ಯಾಪ್ತಿ vs ನಿಜ (ವಾಡಿಕೆಗಿಂತ ಮೀ. ಆಳ)')}</h3>
          <div style={{ height: 170 }}>
            <ResponsiveContainer>
              <ComposedChart data={data} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#eef1f5" vertical={false} />
                <XAxis dataKey="month" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip formatter={(v) => (Array.isArray(v) ? `${v[0]} to ${v[1]} m` : `${v} m`)} />
                {t.threshold_m != null && <ReferenceLine y={t.threshold_m} stroke="#d03b3b" strokeDasharray="4 3" />}
                <Area dataKey="band" stroke="none" fill={color} fillOpacity={0.18} isAnimationActive={false} name={tr('forecast range', 'ಮುನ್ಸೂಚನೆ ವ್ಯಾಪ್ತಿ')} />
                <Line dataKey="mid" stroke={color} strokeDasharray="5 3" dot={false} isAnimationActive={false} name={tr('forecast', 'ಮುನ್ಸೂಚನೆ')} />
                <Scatter dataKey="actual" fill="#0b1b2e" isAnimationActive={false} name={tr('actual (wells)', 'ನಿಜ (ಬಾವಿಗಳು)')} />
              </ComposedChart>
            </ResponsiveContainer>
          </div>
          <div className="muted small">{tr('Shaded = forecast range, dashed = forecast, dots = what the wells actually showed.',
            'ಛಾಯೆ = ಮುನ್ಸೂಚನೆ ವ್ಯಾಪ್ತಿ, ಗೆರೆ = ಮುನ್ಸೂಚನೆ, ಚುಕ್ಕೆ = ಬಾವಿಗಳು ನಿಜವಾಗಿ ತೋರಿಸಿದ್ದು.')}</div>
        </>
      )}

      <h3>{tr('All Karnataka from this date', 'ಈ ದಿನಾಂಕದಿಂದ ಇಡೀ ಕರ್ನಾಟಕ')}</h3>
      <div className="ps-stats">
        <div className="ps-stat"><div className="ps-stat-label">{tr(`Error after ${last.h} months`, `${last.h} ತಿಂಗಳ ನಂತರ ದೋಷ`)}</div>
          <div className="ps-stat-value">{last.mae_model}<span>m</span></div>
          <div className="ps-stat-sub">{tr(`vs ${last.mae_no_change} m assuming "no change"`, `"ಬದಲಾವಣೆ ಇಲ್ಲ" ಎಂದು ಊಹಿಸಿದರೆ ${last.mae_no_change} ಮೀ.`)}</div></div>
        <div className="ps-stat"><div className="ps-stat-label">{tr('Inside the forecast range', 'ಮುನ್ಸೂಚನೆ ವ್ಯಾಪ್ತಿಯೊಳಗೆ')}</div>
          <div className="ps-stat-value">{Math.round(last.covered * 100)}%</div>
          <div className="ps-stat-sub">{tr(`of ${last.taluks} taluks`, `${last.taluks} ತಾಲೂಕುಗಳಲ್ಲಿ`)}</div></div>
        {s && (
          <div className="ps-stat"><div className="ps-stat-label">{tr(`Taluks at stress in ${s.month}`, `${s.month} ರಲ್ಲಿ ಒತ್ತಡದ ತಾಲೂಕುಗಳು`)}</div>
            <div className="ps-stat-value">{s.actual}</div>
            <div className="ps-stat-sub">{tr(`watch list caught ${s.watch_caught} (of ${s.watch_flagged} flagged) · warning caught ${s.warning_caught} (of ${s.warning_flagged})`,
              `ಎಚ್ಚರಿಕೆ ಪಟ್ಟಿ ${s.watch_caught} ಹಿಡಿದಿದೆ (${s.watch_flagged} ಗುರುತಿಸಿದ್ದರಲ್ಲಿ) · ತೀವ್ರ ಎಚ್ಚರಿಕೆ ${s.warning_caught} (${s.warning_flagged} ರಲ್ಲಿ)`)}</div></div>
        )}
      </div>
    </div>
  )
}
