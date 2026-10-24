// M1 kharif drought early warning for one taluk: alert level, probability, trigger evidence, drivers, official status.
import { useLoad } from '../../shared/hooks'
import { useTr } from '../../shared/lang'
import { ErrorBox, Loading } from '../../shared/ui'
import { agriApi } from './api'

export const DROUGHT_COLOR = { likely: '#d03b3b', watch: '#fab219', low: '#0ca30c' }
export const DROUGHT_TEXT = {
  likely: ['Drought likely', 'ಬರ ಸಾಧ್ಯತೆ ಹೆಚ್ಚು'],
  watch: ['Drought watch', 'ಬರ ಎಚ್ಚರಿಕೆ'],
  low: ['No drought alert', 'ಬರ ಎಚ್ಚರಿಕೆ ಇಲ್ಲ'],
}

export default function DroughtCard({ idx, asOf }) {
  const tr = useTr()
  const { data: d, error } = useLoad(() => agriApi.drought(asOf, idx), [idx, asOf])
  if (error) return <ErrorBox error={error} />
  if (!d) return <Loading what="drought early warning" />
  if (!d.in_season) {
    return (
      <div className="ps-card" data-tour="drought">
        <h2>🌵 {tr('Kharif drought early warning', 'ಮುಂಗಾರು ಬರ ಮುನ್ನೆಚ್ಚರಿಕೆ')}</h2>
        <div className="ps-note">{tr('Runs from 1 July to 30 September, during the kharif season. Pick a date in that window (e.g. "1 Aug 2023").',
          'ಮುಂಗಾರು ಋತುವಿನಲ್ಲಿ 1 ಜುಲೈ – 30 ಸೆಪ್ಟೆಂಬರ್ ನಡುವೆ ಕಾರ್ಯನಿರ್ವಹಿಸುತ್ತದೆ. ಆ ಅವಧಿಯ ದಿನಾಂಕ ಆಯ್ಕೆಮಾಡಿ.')}</div>
      </div>
    )
  }
  const t = d.taluks[0]
  const maxC = Math.max(...t.drivers.map((x) => Math.abs(x.change)), 0.05)
  const off = t.official
  return (
    <div className="ps-card" data-tour="drought">
      <div className="ps-card-head">
        <div><h2>🌵 {tr('Kharif drought early warning', 'ಮುಂಗಾರು ಬರ ಮುನ್ನೆಚ್ಚರಿಕೆ')}</h2>
          <div className="muted small">{tr(`M1 · forecast of how the season ends, from data up to ${d.as_of}`, `M1 · ${d.as_of} ರವರೆಗಿನ ದತ್ತಾಂಶದಿಂದ ಋತುವಿನ ಅಂತ್ಯದ ಮುನ್ಸೂಚನೆ`)}</div></div>
        <span className="ps-badge" style={{ background: DROUGHT_COLOR[t.level] }}>{tr(...DROUGHT_TEXT[t.level])}</span>
      </div>
      <div className={`ps-forecast tone-${t.level === 'likely' ? 'critical' : t.level === 'watch' ? 'medium' : 'low'}`}>
        <div className="ps-forecast-big">{Math.round(t.p_drought * 100)}%</div>
        <div><b>{tr('chance this kharif season ends in drought', 'ಈ ಮುಂಗಾರು ಋತು ಬರದಲ್ಲಿ ಮುಗಿಯುವ ಸಾಧ್ಯತೆ')}</b>
          <div className="small muted">{t.trigger
            ? tr('Drought Manual trigger already met (rain deficit or dry spell), so the taluk qualifies for a drought assessment.', 'ಬರ ಕೈಪಿಡಿಯ ಮಾನದಂಡ ಈಗಾಗಲೇ ಪೂರೈಸಿದೆ; ಬರ ಮೌಲ್ಯಮಾಪನಕ್ಕೆ ಅರ್ಹ.')
            : tr('Drought Manual trigger not met yet.', 'ಬರ ಕೈಪಿಡಿಯ ಮಾನದಂಡ ಇನ್ನೂ ಪೂರೈಸಿಲ್ಲ.')}</div></div>
      </div>
      <div className="ps-reasons">
        <b>{tr('Why this alert?', 'ಈ ಎಚ್ಚರಿಕೆ ಏಕೆ?')}</b>
        <ul>
          <li>{tr(`Rain since 1 June: ${t.rain_dev_season > 0 ? '+' : ''}${Math.round(t.rain_dev_season)}% vs normal (trigger: −20% or worse).`,
            `1 ಜೂನ್‌ನಿಂದ ಮಳೆ: ವಾಡಿಕೆಗಿಂತ ${Math.round(t.rain_dev_season)}% (ಮಾನದಂಡ: −20% ಅಥವಾ ಕಡಿಮೆ).`)}</li>
          <li>{tr(`Longest dry spell since 15 June: ${t.longest_dry_spell} days (trigger: 21+ days).`, `15 ಜೂನ್‌ನಿಂದ ದೀರ್ಘ ಒಣ ಅವಧಿ: ${t.longest_dry_spell} ದಿನ (ಮಾನದಂಡ: 21+).`)}</li>
          <li>{tr(`Soil-moisture adequacy for crops: ${Math.round(t.mai * 100)}% (Drought Manual: 75% or less is deficient).`,
            `ಬೆಳೆಗಳಿಗೆ ಮಣ್ಣಿನ ತೇವಾಂಶ ಸಮರ್ಪಕತೆ: ${Math.round(t.mai * 100)}% (75% ಅಥವಾ ಕಡಿಮೆ = ಕೊರತೆ).`)}</li>
          <li>{t.level === 'likely' ? tr('Trigger met and the model is at least 50% confident → drought likely.', 'ಮಾನದಂಡ ಪೂರೈಸಿದೆ ಮತ್ತು ಮಾದರಿ ≥ 50% ಖಚಿತ → ಬರ ಸಾಧ್ಯತೆ ಹೆಚ್ಚು.')
            : t.level === 'watch' ? tr('Trigger met but the model is under 50% confident → drought watch.', 'ಮಾನದಂಡ ಪೂರೈಸಿದೆ, ಮಾದರಿ < 50% → ಬರ ಎಚ್ಚರಿಕೆ.')
              : tr('Trigger not met → no alert yet.', 'ಮಾನದಂಡ ಪೂರೈಸಿಲ್ಲ → ಎಚ್ಚರಿಕೆ ಇಲ್ಲ.')}</li>
        </ul>
      </div>
      <h3>{tr('What raises the drought chance (change in probability)', 'ಬರ ಸಾಧ್ಯತೆ ಹೆಚ್ಚಿಸುವ ಅಂಶಗಳು')}</h3>
      <div className="ps-why">
        {t.drivers.map((x) => (
          <div key={x.key} className="ps-why-row">
            <span>{tr(x.label, x.label_kn)}</span>
            <div className="ps-why-bar"><i style={{ width: `${(Math.abs(x.change) / maxC) * 100}%`, background: x.change > 0 ? '#d03b3b' : '#0ca30c' }} /></div>
            <b>{Math.abs(x.change) < 0.01 ? tr('no effect', 'ಪರಿಣಾಮ ಇಲ್ಲ') : `${x.change > 0 ? '+' : '−'}${Math.round(Math.abs(x.change) * 100)} pts`}</b>
          </div>
        ))}
      </div>
      <div className="ps-note" style={{ marginTop: 10 }}>
        {off
          ? tr(`🏛️ Official: declared ${off.level} drought on ${off.phase} (as "${off.official_name}").`, `🏛️ ಅಧಿಕೃತ: ${off.phase} ರಂದು ${off.level === 'severe' ? 'ತೀವ್ರ' : 'ಸಾಮಾನ್ಯ'} ಬರ ಘೋಷಣೆ.`)
          : tr('🏛️ No official declaration known for this taluk this year (only some years’ lists are public).', '🏛️ ಈ ವರ್ಷ ಈ ತಾಲೂಕಿಗೆ ಅಧಿಕೃತ ಘೋಷಣೆ ತಿಳಿದಿಲ್ಲ.')}
      </div>
      <div className="muted small" style={{ marginTop: 6 }}>{tr('The official declaration also uses crop-loss surveys, which this model does not see; it cannot tell severe from moderate.',
        'ಅಧಿಕೃತ ಘೋಷಣೆ ಬೆಳೆ ನಷ್ಟ ಸಮೀಕ್ಷೆಯನ್ನೂ ಬಳಸುತ್ತದೆ; ಈ ಮಾದರಿ ತೀವ್ರ ಮತ್ತು ಸಾಮಾನ್ಯ ಬರವನ್ನು ಪ್ರತ್ಯೇಕಿಸದು.')}</div>
    </div>
  )
}
