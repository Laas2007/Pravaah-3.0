import { req } from '../api'
import { useLoad } from './hooks'

/** "How good is the model?" — validation numbers straight from models/gw_m2_card.json. */
export default function ModelCard() {
  const card = useLoad(() => req('/api/core/model-card'), []).data
  const m2 = card?.m2
  if (!m2) return null
  const t = m2.validation.taluk_level
  const ev = m2.warning_tiers?.events?.[0]
  return (
    <div className="ps-modelcard" id="model">
      <h2>How good is the model?</h2>
      <p>
        <b>M2 groundwater forecast</b> learns from real monthly readings at 2,698 government monitoring wells.
        It's tested only on years it never saw (trained up to 2021, tested 2022–2026).
      </p>
      <div className="ps-stats">
        <div className="ps-stat"><div className="ps-stat-label">Forecast error, all 2022–26</div>
          <div className="ps-stat-value">{t.mae_model_m}<span>m</span></div>
          <div className="ps-stat-sub">vs {t.mae_no_change_m} m if you assume "no change"</div></div>
        <div className="ps-stat"><div className="ps-stat-label">Honest uncertainty</div>
          <div className="ps-stat-value">{Math.round(t.coverage_10_90 * 100)}%</div>
          <div className="ps-stat-sub">of real outcomes fell inside the shown 10–90% range (target 80%)</div></div>
        {ev && (
          <div className="ps-stat"><div className="ps-stat-label">2023 drought, from {ev.origin} data</div>
            <div className="ps-stat-value">{ev.watch_pessimistic.correct}/{ev.actual_in_stress}</div>
            <div className="ps-stat-sub">
              stress taluks in {ev.target} were on the watch list (but {ev.watch_pessimistic.flagged} taluks were flagged).
              The stricter warning tier caught {ev.warning_likely.correct}/{ev.actual_in_stress}.
            </div></div>
        )}
      </div>
      <div className="muted small">
        Limitation: it ranks taluks well (correlation {m2.event_2023.spearman}) but under-predicts extremes, so treat
        "watch" as an early alert, not a certainty. Drought classifier (M1): {card.m1.status}.
      </div>
    </div>
  )
}
