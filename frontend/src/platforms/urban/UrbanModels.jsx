// M5 demand & tankers, M6 leak detection cards for the Urban platform.
import { useState } from 'react'
import { Bar, BarChart, CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useLoad } from '../../shared/hooks'
import { useTr } from '../../shared/lang'
import { platform } from '../../shared/platforms'
import { ErrorBox, Loading, Stat } from '../../shared/ui'
import { urbanApi } from './api'

const COLOR = platform('urban').color

/** M5: Bengaluru demand, piped supply, borewell draw and tanker need (estimated, physically based). */
export function DemandCard({ asOf, onWard }) {
  const tr = useTr()
  const { data: d, error } = useLoad(() => urbanApi.demand(asOf), [asOf])
  if (error) return <ErrorBox error={error} />
  if (!d) return <Loading what="demand" />
  const b = d.bengaluru
  return (
    <div className="ps-card" data-tour="demand">
      <h2>{tr('Bengaluru water demand & tankers', 'ಬೆಂಗಳೂರು ನೀರಿನ ಬೇಡಿಕೆ ಮತ್ತು ಟ್ಯಾಂಕರ್‌ಗಳು')}</h2>
      <div className="muted small">{tr('Estimated from ward population (135 L/person/day), commercial load, Cauvery pipe coverage and supply reliability; next months adjust for seasonal heat.',
        'ವಾರ್ಡ್ ಜನಸಂಖ್ಯೆ (135 ಲೀ/ವ್ಯಕ್ತಿ/ದಿನ), ವಾಣಿಜ್ಯ ಬಳಕೆ, ಕಾವೇರಿ ಸಂಪರ್ಕ ಮತ್ತು ಪೂರೈಕೆ ವಿಶ್ವಾಸಾರ್ಹತೆಯಿಂದ ಅಂದಾಜು; ಮುಂದಿನ ತಿಂಗಳುಗಳಿಗೆ ಬಿಸಿಲಿನ ಹೊಂದಾಣಿಕೆ.')}</div>
      <div className="ps-stats">
        <Stat label={tr('Demand', 'ಬೇಡಿಕೆ')} value={b.demand_mld} unit="MLD" />
        <Stat label={tr('Cauvery piped', 'ಕಾವೇರಿ ಕೊಳವೆ')} value={b.piped_mld} unit="MLD" />
        <Stat label={tr('From borewells', 'ಕೊಳವೆಬಾವಿಗಳಿಂದ')} value={b.borewell_mld} unit="MLD" />
        <Stat label={tr('Tanker need', 'ಟ್ಯಾಂಕರ್ ಅಗತ್ಯ')} value={b.tanker_mld} unit="MLD" tone={b.tanker_mld > 0 ? 'bad' : ''}
          sub={tr(`${b.wards_needing_tankers} wards · up to ${b.tanker_trips_per_day.toLocaleString()} trips/day (6,000 L)`,
            `${b.wards_needing_tankers} ವಾರ್ಡ್‌ಗಳು · ದಿನಕ್ಕೆ ${b.tanker_trips_per_day.toLocaleString()} ವರೆಗೆ ಟ್ರಿಪ್`)} />
      </div>
      <h3>{tr('Next 6 months: demand vs piped supply (MLD)', 'ಮುಂದಿನ 6 ತಿಂಗಳು: ಬೇಡಿಕೆ vs ಕೊಳವೆ ಪೂರೈಕೆ (MLD)')}</h3>
      <div style={{ height: 150 }}>
        <ResponsiveContainer>
          <BarChart data={b.next_6_months} margin={{ top: 6, right: 8, left: -10, bottom: 0 }}>
            <CartesianGrid stroke="#eef1f5" vertical={false} />
            <XAxis dataKey="month" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} />
            <Tooltip />
            <Bar dataKey="piped_mld" stackId="a" name={tr('piped', 'ಕೊಳವೆ')} fill={COLOR} isAnimationActive={false} />
            <Bar dataKey="gap_mld" stackId="a" name={tr('gap (borewells / tankers)', 'ಅಂತರ (ಕೊಳವೆಬಾವಿ / ಟ್ಯಾಂಕರ್)')} fill="#ec835a" isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      {b.top_tanker_wards.length > 0 && (
        <>
          <h3>{tr('Wards that need tankers most', 'ಹೆಚ್ಚು ಟ್ಯಾಂಕರ್ ಬೇಕಾದ ವಾರ್ಡ್‌ಗಳು')}</h3>
          <table className="ps-table">
            <thead><tr><th>{tr('Ward', 'ವಾರ್ಡ್')}</th><th>{tr('Tanker MLD', 'ಟ್ಯಾಂಕರ್ MLD')}</th><th>{tr('Trips/day', 'ಟ್ರಿಪ್/ದಿನ')}</th></tr></thead>
            <tbody>
              {b.top_tanker_wards.slice(0, 8).map((w) => (
                <tr key={w.idx} onClick={() => onWard?.(w.idx)}><td><b>{w.name}</b></td><td>{w.tanker_mld}</td><td>{w.tanker_trips_per_day.toLocaleString()}</td></tr>
              ))}
            </tbody>
          </table>
        </>
      )}
      <div className="muted small" style={{ marginTop: 6 }}>{tr('Tanker need assumes borewells fail in wards at or near shortage (an upper bound). Population, pipe coverage and supply are estimates.',
        'ಕೊರತೆಯ ವಾರ್ಡ್‌ಗಳಲ್ಲಿ ಕೊಳವೆಬಾವಿ ವಿಫಲವಾಗುತ್ತವೆ ಎಂಬ ಊಹೆ (ಗರಿಷ್ಠ ಅಂದಾಜು). ಜನಸಂಖ್ಯೆ, ಸಂಪರ್ಕ ಮತ್ತು ಪೂರೈಕೆ ಅಂದಾಜುಗಳು.')}</div>
    </div>
  )
}

/** M6: leak detection on meter data. Demo on synthetic meters (truth known) + check your own CSV. */
export function LeakCard() {
  const tr = useTr()
  const { data: d, error } = useLoad(() => urbanApi.leaksDemo(), [])
  const [mine, setMine] = useState(null)
  const [err, setErr] = useState(null)
  async function upload(e) {
    const f = e.target.files?.[0]
    if (!f) return
    setErr(null)
    try { setMine(await urbanApi.leaksCheck(await f.text())) } catch (x) { setErr(x.message) }
  }
  function sample() {
    const rows = ['timestamp,litres']
    for (let day = 1; day <= 21; day++) for (let h = 0; h < 24; h++) {
      const base = [7, 8, 19, 20].includes(h) ? 45 : h >= 6 && h <= 22 ? 12 : 1
      rows.push(`2026-01-${String(day).padStart(2, '0')} ${String(h).padStart(2, '0')}:00,${base + (day >= 12 ? 18 : 0)}`)
    }
    const url = URL.createObjectURL(new Blob([rows.join('\n')], { type: 'text/csv' }))
    const a = document.createElement('a'); a.href = url; a.download = 'sample_meter_with_leak.csv'; a.click()
  }
  if (error) return <ErrorBox error={error} />
  if (!d) return <Loading what="leak detector" />
  const ex = d.examples.find((x) => x.leak)
  return (
    <div className="ps-card" data-tour="leaks">
      <h2>{tr('Leak & abnormal-use detection', 'ಸೋರಿಕೆ ಮತ್ತು ಅಸಾಮಾನ್ಯ ಬಳಕೆ ಪತ್ತೆ')}</h2>
      <div className="ps-mock"><b>{tr('Synthetic test data', 'ಕೃತಕ ಪರೀಕ್ಷಾ ದತ್ತಾಂಶ')}</b> · {tr(`No public household meter data exists, so the detector is tested on ${d.meters} simulated meters (${d.days} days, hourly) with ${d.planted_leaks} planted leaks and night-time sump filling.`,
        `ಸಾರ್ವಜನಿಕ ಮೀಟರ್ ದತ್ತಾಂಶ ಇಲ್ಲ; ${d.meters} ಕೃತಕ ಮೀಟರ್‌ಗಳ ಮೇಲೆ (${d.planted_leaks} ಸೋರಿಕೆಗಳು) ಪರೀಕ್ಷೆ.`)}</div>
      <div className="ps-stats">
        <Stat label={tr('Leaks found', 'ಪತ್ತೆಯಾದ ಸೋರಿಕೆ')} value={`${d.leaks.correct}/${d.planted_leaks}`}
          sub={tr(`${Math.round(d.leaks.precision * 100)}% of alerts correct · missed only tiny drips (${d.leaks.missed_rates_lph.map((x) => x + ' L/h').join(', ') || 'none'})`,
            `${Math.round(d.leaks.precision * 100)}% ಎಚ್ಚರಿಕೆ ಸರಿ · ಸಣ್ಣ ತೊಟ್ಟಿಕ್ಕುವಿಕೆ ಮಾತ್ರ ತಪ್ಪಿದೆ`)} />
        <Stat label={tr('Heavy-use days flagged', 'ಅಸಾಮಾನ್ಯ ಬಳಕೆ ದಿನಗಳು')} value={`${d.abnormal_days.heavy_days_caught}/${d.abnormal_days.planted_heavy_days}`}
          sub={tr(`${Math.round(d.abnormal_days.flags_explained * 100)}% of flags explained by planted events`, `${Math.round(d.abnormal_days.flags_explained * 100)}% ಎಚ್ಚರಿಕೆಗಳು ವಿವರಿಸಲ್ಪಟ್ಟಿವೆ`)} />
      </div>
      {ex && (
        <>
          <h3>{tr(`Example: meter ${ex.meter}, night-time minimum flow (L/h)`, `ಉದಾಹರಣೆ: ಮೀಟರ್ ${ex.meter}, ರಾತ್ರಿಯ ಕನಿಷ್ಠ ಹರಿವು (ಲೀ/ಗಂ)`)}</h3>
          <div style={{ height: 130 }}>
            <ResponsiveContainer>
              <LineChart data={ex.night_min_lph.map((v, i) => ({ day: i + 1, v }))} margin={{ top: 6, right: 8, left: -18, bottom: 0 }}>
                <CartesianGrid stroke="#eef1f5" vertical={false} />
                <XAxis dataKey="day" tick={{ fontSize: 10 }} />
                <YAxis tick={{ fontSize: 10 }} />
                <Tooltip />
                {ex.detected_day != null && <ReferenceLine x={ex.detected_day + 1} stroke="#d03b3b" label={{ value: tr('alert', 'ಎಚ್ಚರಿಕೆ'), fontSize: 10, fill: '#d03b3b' }} />}
                <Line dataKey="v" stroke={COLOR} dot={false} isAnimationActive={false} name="L/h" />
              </LineChart>
            </ResponsiveContainer>
          </div>
          <div className="muted small">{tr('A leak keeps water flowing at night: the night minimum jumps and stays up.', 'ಸೋರಿಕೆ ಇದ್ದರೆ ರಾತ್ರಿಯೂ ನೀರು ಹರಿಯುತ್ತದೆ: ರಾತ್ರಿಯ ಕನಿಷ್ಠ ಹರಿವು ಏರಿ ಹಾಗೇ ಉಳಿಯುತ್ತದೆ.')}</div>
        </>
      )}
      <h3>{tr('Check your own meter', 'ನಿಮ್ಮ ಮೀಟರ್ ಪರಿಶೀಲಿಸಿ')}</h3>
      <div className="ps-upload">
        <input type="file" accept=".csv,text/csv" onChange={upload} />
        <button className="ps-link-btn" onClick={sample}>{tr('Download a sample CSV', 'ಮಾದರಿ CSV ಡೌನ್‌ಲೋಡ್')}</button>
      </div>
      <div className="muted small">{tr('CSV columns: timestamp (YYYY-MM-DD HH:MM), litres (per hour).', 'CSV ಕಾಲಮ್‌ಗಳು: timestamp, litres (ಗಂಟೆಗೆ).')}</div>
      {err && <div className="ps-error">{err}</div>}
      {mine && (
        <div className={`ps-note ${mine.leak_suspected ? 'bad' : ''}`}>
          {mine.leak_suspected
            ? tr(`Possible leak from ${mine.leak_from}. ${mine.advice}`, `${mine.leak_from} ರಿಂದ ಸೋರಿಕೆ ಸಾಧ್ಯತೆ. ಶೌಚಾಲಯ, ಟ್ಯಾಂಕ್ ಫ್ಲೋಟ್ ವಾಲ್ವ್, ನಲ್ಲಿಗಳನ್ನು ಪರಿಶೀಲಿಸಿ.`)
            : tr(`No leak pattern in ${mine.days} days of readings.`, `${mine.days} ದಿನಗಳ ದತ್ತಾಂಶದಲ್ಲಿ ಸೋರಿಕೆ ಮಾದರಿ ಇಲ್ಲ.`)}
        </div>
      )}
    </div>
  )
}
