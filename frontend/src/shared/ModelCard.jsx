import { req } from '../api'
import { useLoad } from './hooks'
import { useTr } from './lang'

/** One line per model with its honest test result. */
function ModelList({ card }) {
  const tr = useTr()
  const m4 = card.m4?.validation?.by_horizon
  const m4h = m4 && (m4['90'] || m4[90])
  const m1 = card.m1?.tests?.B_train_2015_2025_test_2026
  const m1c = card.m1?.tests?.C_official_2023_order_model_without_2023
  const rain = card.m3?.by_crop?.filter((r) => ['Urad', 'Gram', 'Jowar', 'Moong'].includes(r.crop) && r.spearman_loss_vs_yield < 0)
  return (
    <table className="ps-table" style={{ margin: '10px 0' }}>
      <thead><tr><th>{tr('Model', 'ಮಾದರಿ')}</th><th>{tr('Data', 'ದತ್ತಾಂಶ')}</th><th>{tr('How it was tested', 'ಪರೀಕ್ಷೆ')}</th></tr></thead>
      <tbody>
        <tr><td><b>M2</b> {tr('groundwater', 'ಅಂತರ್ಜಲ')}</td><td>🟢 {tr('2,698 wells', '2,698 ಬಾವಿಗಳು')}</td><td>{tr('2022–26 unseen years (above)', '2022–26 ನೋಡದ ವರ್ಷಗಳು (ಮೇಲೆ)')}</td></tr>
        {m1 && <tr><td><b>M1</b> {tr('kharif drought', 'ಮುಂಗಾರು ಬರ')}</td><td>🟢 {tr('IMD rain, ERA5, wells; official 2023 / 2026 orders', 'IMD ಮಳೆ, ERA5, ಬಾವಿಗಳು; ಅಧಿಕೃತ ಆದೇಶಗಳು')}</td>
          <td>{tr(`unseen 2026: AUC ${m1['09-15'].auc_model} vs ${m1['09-15'].auc_rain_deficit} rain-deficit rule (15 Sep); officially declared taluks alerted ${22 - m1['08-01'].official_listed_22.low}/22 by 1 Aug. 2023 order (model trained without 2023): ${m1c['09-01'].declared_severe.likely + m1c['09-01'].declared_severe.watch}/165 severe alerted by 1 Sep. Cannot tell severe from moderate.`,
            `ನೋಡದ 2026: AUC ${m1['09-15'].auc_model} vs ${m1['09-15'].auc_rain_deficit}; ಘೋಷಿತ ತಾಲೂಕುಗಳಲ್ಲಿ ${22 - m1['08-01'].official_listed_22.low}/22 ಗೆ 1 ಆಗಸ್ಟ್‌ನೊಳಗೆ ಎಚ್ಚರಿಕೆ`)}</td></tr>}
        {m4h && <tr><td><b>M4</b> {tr('reservoirs', 'ಜಲಾಶಯಗಳು')}</td><td>🟢 {tr('9 dams, daily', '9 ಜಲಾಶಯಗಳು, ದೈನಂದಿನ')}</td>
          <td>{tr(`90-day error ${m4h.model_pct_cap}% of capacity vs ${m4h.no_change_pct_cap}% "no change", ${m4h.seasonal_pct_cap}% seasonal; ${Math.round(m4h.coverage_10_90 * 100)}% inside range`,
            `90 ದಿನದ ದೋಷ ಸಾಮರ್ಥ್ಯದ ${m4h.model_pct_cap}% vs ${m4h.no_change_pct_cap}% "ಬದಲಾವಣೆ ಇಲ್ಲ"`)}</td></tr>}
        {card.m3 && <tr><td><b>M3</b> {tr('crop yield risk', 'ಬೆಳೆ ಇಳುವರಿ ಅಪಾಯ')}</td><td>🟢 {tr('IMD rain, ERA5 ET0 + FAO coefficients', 'IMD ಮಳೆ, ERA5 + FAO ಗುಣಾಂಕಗಳು')}</td>
          <td>{tr(`vs real 2024-25 DES yields: rainfed crops follow the model (${rain.map((r) => `${r.crop} ρ ${r.spearman_loss_vs_yield}`).join(', ')}); irrigated crops (rice, ragi, maize) don't`,
            `2024-25 DES ಇಳುವರಿಯೊಂದಿಗೆ: ಮಳೆಯಾಶ್ರಿತ ಬೆಳೆಗಳು ಹೊಂದುತ್ತವೆ; ನೀರಾವರಿ ಬೆಳೆಗಳು ಇಲ್ಲ`)}</td></tr>}
        <tr><td><b>M5</b> {tr('urban demand & tankers', 'ನಗರ ಬೇಡಿಕೆ ಮತ್ತು ಟ್ಯಾಂಕರ್')}</td><td>🟠 {tr('estimated', 'ಅಂದಾಜು')}</td><td>{tr('physically based; no metered demand exists to test on', 'ಭೌತಿಕ ಮಾದರಿ; ಪರೀಕ್ಷೆಗೆ ಮೀಟರ್ ದತ್ತಾಂಶ ಇಲ್ಲ')}</td></tr>
        <tr><td><b>M6</b> {tr('leak detection', 'ಸೋರಿಕೆ ಪತ್ತೆ')}</td><td>🔵 {tr('synthetic meters', 'ಕೃತಕ ಮೀಟರ್‌ಗಳು')}</td><td>{tr('planted leaks with known truth (Urban page)', 'ತಿಳಿದ ಸೋರಿಕೆಗಳೊಂದಿಗೆ (ನಗರ ಪುಟ)')}</td></tr>
        <tr><td><b>M7</b> {tr('industrial disruption', 'ಕೈಗಾರಿಕಾ ಅಡಚಣೆ')}</td><td>🟢 KIADB + M2 + M4 · 🟠 {tr('water norm', 'ನೀರಿನ ಮಾನದಂಡ')}</td><td>{tr('transparent score; no disruption records exist', 'ಪಾರದರ್ಶಕ ಅಂಕ; ದಾಖಲೆಗಳು ಇಲ್ಲ')}</td></tr>
      </tbody>
    </table>
  )
}

/** "How good is the model?" — validation numbers straight from models/gw_m2_card.json (+ Bengaluru ward check). */
export default function ModelCard() {
  const tr = useTr()
  const card = useLoad(() => req('/api/core/model-card'), []).data
  const m2 = card?.m2
  if (!m2) return null
  const t = m2.validation.taluk_level
  const ev = m2.warning_tiers?.events?.[0]
  const b = card.bengaluru_wards
  return (
    <div className="ps-modelcard" id="model">
      <h2>{tr('How good is the model?', 'ಮಾದರಿ ಎಷ್ಟು ಉತ್ತಮ?')}</h2>
      <p>{tr(<><b>M2 groundwater forecast</b> learns from real monthly readings at 2,698 government monitoring wells. It's
        tested only on years it never saw (trained up to 2021, tested 2022–2026). Try any past date in the Time Machine.</>,
      <><b>M2 ಅಂತರ್ಜಲ ಮುನ್ಸೂಚನೆ</b> 2,698 ಸರ್ಕಾರಿ ಮೇಲ್ವಿಚಾರಣಾ ಬಾವಿಗಳ ನೈಜ ಮಾಸಿಕ ದತ್ತಾಂಶದಿಂದ ಕಲಿಯುತ್ತದೆ. ಅದು ನೋಡದ
        ವರ್ಷಗಳ ಮೇಲೆ ಮಾತ್ರ ಪರೀಕ್ಷೆ (2021 ರವರೆಗೆ ತರಬೇತಿ, 2022–2026 ಪರೀಕ್ಷೆ). ಟೈಮ್ ಮೆಷಿನ್‌ನಲ್ಲಿ ಯಾವುದೇ ಹಿಂದಿನ ದಿನಾಂಕ ಪ್ರಯತ್ನಿಸಿ.</>)}</p>
      <div className="ps-stats">
        <div className="ps-stat"><div className="ps-stat-label">{tr('Forecast error, all 2022–26', 'ಮುನ್ಸೂಚನೆ ದೋಷ, 2022–26')}</div>
          <div className="ps-stat-value">{t.mae_model_m}<span>m</span></div>
          <div className="ps-stat-sub">{tr(`vs ${t.mae_no_change_m} m if you assume "no change"`, `"ಬದಲಾವಣೆ ಇಲ್ಲ" ಎಂದರೆ ${t.mae_no_change_m} ಮೀ.`)}</div></div>
        <div className="ps-stat"><div className="ps-stat-label">{tr('Honest uncertainty', 'ಪ್ರಾಮಾಣಿಕ ಅನಿಶ್ಚಿತತೆ')}</div>
          <div className="ps-stat-value">{Math.round(t.coverage_10_90 * 100)}%</div>
          <div className="ps-stat-sub">{tr('of real outcomes fell inside the shown 10–90% range (target 80%)', 'ನೈಜ ಫಲಿತಾಂಶಗಳು ತೋರಿಸಿದ 10–90% ವ್ಯಾಪ್ತಿಯೊಳಗೆ (ಗುರಿ 80%)')}</div></div>
        {ev && (
          <div className="ps-stat"><div className="ps-stat-label">{tr(`2023 drought, from ${ev.origin} data`, `2023 ಬರ, ${ev.origin} ದತ್ತಾಂಶದಿಂದ`)}</div>
            <div className="ps-stat-value">{ev.watch_pessimistic.correct}/{ev.actual_in_stress}</div>
            <div className="ps-stat-sub">{tr(`stress taluks in ${ev.target} were on the watch list (but ${ev.watch_pessimistic.flagged} taluks were flagged). The stricter warning tier caught ${ev.warning_likely.correct}/${ev.actual_in_stress}.`,
              `${ev.target} ರ ಒತ್ತಡದ ತಾಲೂಕುಗಳು ಎಚ್ಚರಿಕೆ ಪಟ್ಟಿಯಲ್ಲಿದ್ದವು (ಆದರೆ ${ev.watch_pessimistic.flagged} ತಾಲೂಕುಗಳನ್ನು ಗುರುತಿಸಲಾಗಿತ್ತು). ಕಟ್ಟುನಿಟ್ಟಾದ ಎಚ್ಚರಿಕೆ ${ev.warning_likely.correct}/${ev.actual_in_stress}.`)}</div></div>
        )}
      </div>
      <ModelList card={card} />
      {b?.wells_checked && (
        <p className="small">{tr(<><b>Bengaluru wards</b> use the ward-level water-balance model (pipe coverage, density, paving per ward) on
          {' '}{b.rain}. Its simulated groundwater was checked against {b.wells_checked} real wells with long records: correlation {b.r_2015_2021} in 2015–21, but only {b.r_2022_on} since 2022.</>,
        <><b>ಬೆಂಗಳೂರು ವಾರ್ಡ್‌ಗಳು</b> ವಾರ್ಡ್ ಮಟ್ಟದ ನೀರಿನ ಸಮತೋಲನ ಮಾದರಿ (ಕೊಳವೆ ಸಂಪರ್ಕ, ಜನಸಾಂದ್ರತೆ, ಕಾಂಕ್ರೀಟ್ ಮೇಲ್ಮೈ) ಮತ್ತು IMD ಮಳೆ
          ದತ್ತಾಂಶ ಬಳಸುತ್ತವೆ. {b.wells_checked} ನೈಜ ಬಾವಿಗಳೊಂದಿಗೆ ಹೋಲಿಕೆ: 2015–21 ರಲ್ಲಿ ಸಹಸಂಬಂಧ {b.r_2015_2021}, 2022 ರಿಂದ ಕೇವಲ {b.r_2022_on}.</>)}</p>
      )}
      <div className="muted small">{tr(`Limitation: it ranks taluks well (correlation ${m2.event_2023.spearman}) but under-predicts extremes, so treat "watch" as an early alert, not a certainty. Drought classifier (M1): ${card.m1.status}.`,
        `ಮಿತಿ: ತಾಲೂಕುಗಳನ್ನು ಚೆನ್ನಾಗಿ ಶ್ರೇಣೀಕರಿಸುತ್ತದೆ (ಸಹಸಂಬಂಧ ${m2.event_2023.spearman}) ಆದರೆ ತೀವ್ರ ಸಂದರ್ಭಗಳನ್ನು ಕಡಿಮೆ ಅಂದಾಜಿಸುತ್ತದೆ; "ಎಚ್ಚರಿಕೆ" ಮುಂಚಿನ ಸೂಚನೆ ಮಾತ್ರ. ಬರ ವರ್ಗೀಕರಣ (M1): ನೈಜ ಬರ ಘೋಷಣೆ ದತ್ತಾಂಶಕ್ಕಾಗಿ ಕಾಯುತ್ತಿದೆ.`)}</div>
    </div>
  )
}
