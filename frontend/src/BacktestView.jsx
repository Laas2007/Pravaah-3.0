import { useEffect, useState } from 'react'
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { api } from './api'
import { RISK_COLOR, fmtDate } from './i18n'
import { GroundwaterChart } from './charts'

const STORY_WARDS = ['Whitefield', 'Mahadevapura', 'Marathahalli', 'Puttenahalli - Sarakki Lake', 'Bellanduru', 'Hagadur', 'Kadugodi']
const daysBetween = (a, b) => Math.round((new Date(b) - new Date(a)) / 86400000)

function Story({ bw, bt, detail }) {
  if (!bw) return null
  const ref = bt.reference
  if (!bw.flag_date) {
    return <div className="story"><b>{bw.name}</b> was never flagged high-risk in this window, and the simulation shows no shortage there.</div>
  }
  if (bw.flag_date === bt.dates[0] && bw.flag_pred_days?.[1] === 0) {
    return <div className="story"><b>{bw.name}</b> was already below the shortage line when the window opened ({fmtDate(bt.dates[0])}). The stress there is chronic.</div>
  }
  const lead = ref ? daysBetween(bw.flag_date, ref.date) : null
  return (
    <div className="story" data-tour="story">
      <div className="story-lead">
        <div className="lead-num">{lead}</div>
        <div className="lead-text">days of early warning<br /><span>before the crisis peaked (Mar 2024)</span></div>
      </div>
      <div className="story-steps">
        <div><span className="ss-date">{fmtDate(bw.flag_date)}</span><span>Model flags <b>{bw.name}</b> as high risk: shortage in <b>{bw.flag_pred_days[0]}–{bw.flag_pred_days[1]} days</b></span></div>
        {bw.sim_onset && <div><span className="ss-date">{fmtDate(bw.sim_onset)}</span><span>Groundwater crosses the shortage line</span></div>}
        {ref && <div><span className="ss-date">Early Mar 2024</span><span>Crisis peaks: borewells run dry, tanker shortages</span></div>}
      </div>
      {detail && detail.idx === bw.idx && detail.timeseries.actual_after.length > 0 && (
        <>
          <h3>Forecast on {fmtDate(detail.as_of)} vs what followed</h3>
          <GroundwaterChart ts={detail.timeseries} asOf={detail.as_of} lang="en" />
        </>
      )}
    </div>
  )
}

export default function BacktestView({ selected, onSelect, asOf, setAsOf, detail, wardsByName }) {
  const [bt, setBt] = useState(null)
  useEffect(() => { api.backtest().then(setBt) }, [])
  useEffect(() => {
    if (selected == null && wardsByName.Whitefield != null) onSelect(wardsByName.Whitefield)
  }, [selected, wardsByName, onSelect])

  if (!bt) return <div className="panel-inner"><p className="muted">Re-running the model for every week of Sep 2023 – Apr 2024 (first time only, ~10 s)…</p></div>

  const data = bt.dates.map((d, i) => ({ date: d, n: bt.high_or_critical_count[i] }))
  const bw = bt.wards.find((w) => w.idx === selected)
  const inWindow = asOf >= bt.dates[0] && asOf <= bt.dates[bt.dates.length - 1]

  return (
    <div className="panel-inner">
      <div className="tm-head">
        <div className="tm-kicker">Time Machine</div>
        <h2>Would we have seen the 2024 crisis coming?</h2>
        <p className="muted small">
          We rewind to past dates and run the model using <b>only data that existed on that day</b>. Its future-rain
          scenarios come only from earlier years. No peeking.
        </p>
        <div className="tm-buttons">
          <button className="primary" onClick={() => setAsOf('2023-12-01')}>Rewind to 1 Dec 2023</button>
          <button className="ghost" onClick={() => setAsOf('2024-03-01')}>Jump to the crisis</button>
        </div>
        <p className="muted small">Tip: press on the timeline under the map to watch the risk spread week by week.</p>
      </div>

      <div className="row-between">
        <h3>Ward story</h3>
        <select value={selected ?? ''} onChange={(e) => onSelect(+e.target.value)} aria-label="Ward">
          {STORY_WARDS.filter((n) => wardsByName[n] != null).map((n) => <option key={n} value={wardsByName[n]}>{n}</option>)}
          {bw && !STORY_WARDS.includes(bw.name) && <option value={bw.idx}>{bw.name}</option>}
        </select>
      </div>
      <Story bw={bw} bt={bt} detail={inWindow ? detail : null} />

      <h3>Wards at high or critical risk, week by week</h3>
      <ResponsiveContainer width="100%" height={170}>
        <LineChart data={data} margin={{ top: 14, right: 12, bottom: 0, left: -18 }}>
          <CartesianGrid stroke="#edf0f4" vertical={false} />
          <XAxis dataKey="date" tick={{ fontSize: 11, fill: '#7a8699' }} tickFormatter={(d) => d.slice(0, 7)} minTickGap={30} stroke="#dfe4ea" />
          <YAxis tick={{ fontSize: 11, fill: '#7a8699' }} stroke="#dfe4ea" />
          <Tooltip labelFormatter={(d) => fmtDate(d)} formatter={(v) => [`${v} wards`, 'High or critical']} />
          <Line dataKey="n" stroke={RISK_COLOR.high} strokeWidth={2.5} dot={false} isAnimationActive={false} />
          {bt.reference && <ReferenceLine x={bt.dates.find((d) => d >= bt.reference.date)} stroke={RISK_COLOR.critical} strokeDasharray="4 4"
            label={{ value: 'Crisis peak', fill: RISK_COLOR.critical, fontSize: 10, position: 'insideTopLeft' }} />}
          {inWindow && <ReferenceLine x={bt.dates.find((d) => d >= asOf)} stroke="#0b2545" strokeWidth={2} />}
        </LineChart>
      </ResponsiveContainer>
      <p className="muted small">Reference: {bt.reference?.label}.</p>
    </div>
  )
}
