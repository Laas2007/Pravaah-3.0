import { useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { GroundwaterChart } from './charts'
import { WhyList } from './CitizenView'
import { RISK_COLOR, RISK_ICON, rangeText } from './i18n'

const ZERO = { extra_piped: 0, rwh_boost: 0, demand_cut: 0, tanker_mld: 0 }
const show = (x) => (x.days_mid === 0 ? 'In shortage now' : x.days_low > 365 ? 'Safe for 1 yr+' : `${x.days_low}–${x.days_high > 365 ? '365+' : x.days_high} days`)

function Ranking({ wards, selected, onSelect }) {
  const [sort, setSort] = useState('days')
  const [all, setAll] = useState(false)
  const rows = useMemo(() => {
    const r = [...wards]
    if (sort === 'days') r.sort((a, b) => a.days_mid - b.days_mid || a.groundwater_pct - b.groundwater_pct)
    if (sort === 'gw') r.sort((a, b) => a.groundwater_pct - b.groundwater_pct)
    if (sort === 'bore') r.sort((a, b) => a.inputs.cauvery_coverage_pct - b.inputs.cauvery_coverage_pct)
    if (sort === 'people') r.sort((a, b) => b.inputs.population - a.inputs.population)
    return r
  }, [wards, sort])
  const shown = all ? rows : rows.slice(0, 15)
  return (
    <div>
      <div className="row-between">
        <p className="muted small">Click a ward to inspect it.</p>
        <select value={sort} onChange={(e) => setSort(e.target.value)} aria-label="Sort wards by">
          <option value="days">Soonest shortage</option>
          <option value="gw">Lowest groundwater</option>
          <option value="bore">Most borewell-dependent</option>
          <option value="people">Most people</option>
        </select>
      </div>
      <table className="rank">
        <thead>
          <tr><th>#</th><th>Ward</th><th>Shortage in</th><th className="num">GW</th><th className="num">Piped</th></tr>
        </thead>
        <tbody>
          {shown.map((w, i) => (
            <tr key={w.idx} className={w.idx === selected ? 'sel' : ''} onClick={() => onSelect(w.idx)}>
              <td className="muted">{i + 1}</td>
              <td><span className="dot" style={{ background: RISK_COLOR[w.risk] }} />{w.name}</td>
              <td>{w.days_mid === 0 ? <b style={{ color: RISK_COLOR.critical }}>now</b> : rangeText(w) ? `${rangeText(w)} d` : '—'}</td>
              <td className="num">{w.groundwater_pct}%</td>
              <td className="num">{w.inputs.cauvery_coverage_pct}%</td>
            </tr>
          ))}
        </tbody>
      </table>
      <button className="link" onClick={() => setAll(!all)}>{all ? 'Show top 15' : `Show all ${rows.length} wards`}</button>
    </div>
  )
}

function Planner({ detail, asOf, preset }) {
  const [iv, setIv] = useState(ZERO)
  const [res, setRes] = useState(null)
  useEffect(() => { setIv(preset || ZERO); setRes(null) }, [detail.idx, asOf, preset])
  useEffect(() => {
    if (Object.values(iv).every((v) => v === 0)) { setRes(null); return }
    const h = setTimeout(() => api.intervene({ as_of: asOf, idx: detail.idx, ...iv }).then(setRes), 200)
    return () => clearTimeout(h)
  }, [iv, detail.idx, asOf])

  const slider = (k, icon, label, max, step, fmt) => (
    <label className="slider" key={k}>
      <span className="sl-icon">{icon}</span>
      <span className="sl-label">{label}</span>
      <input type="range" min={0} max={max} step={step} value={iv[k]} onChange={(e) => setIv({ ...iv, [k]: +e.target.value })} />
      <b>{fmt(iv[k])}</b>
    </label>
  )
  const after = res?.after
  return (
    <div className="planner" data-tour="planner">
      <p className="muted small">Move the levers. The model re-runs all 30 rainfall scenarios for <b>{detail.name}</b>.</p>
      {slider('extra_piped', '🚰', 'Extend Cauvery pipe coverage', 0.6, 0.05, (v) => `+${Math.round(v * 100)}%`)}
      {slider('rwh_boost', '🪣', 'Rainwater harvesting & recharge wells', 2, 0.1, (v) => `+${Math.round(v * 100)}%`)}
      {slider('demand_cut', '🔧', 'Cut demand (aerators, STP reuse, rationing)', 0.4, 0.05, (v) => (v ? `−${Math.round(v * 100)}%` : "0%"))}
      {slider('tanker_mld', '🚚', 'Tanker water brought in', 5, 0.25, (v) => `${v} MLD`)}
      <div className="compare">
        <div className="cmp-box">
          <div className="cmp-label">Today's path</div>
          <div className="cmp-value" style={{ color: RISK_COLOR[detail.risk] }}>{show(detail)}</div>
          <div className="cmp-risk">{RISK_ICON[detail.risk]} {detail.risk}</div>
        </div>
        <div className="cmp-arrow">→</div>
        <div className={`cmp-box ${after ? 'on' : ''}`}>
          <div className="cmp-label">With interventions</div>
          {after ? (
            <>
              <div className="cmp-value" style={{ color: RISK_COLOR[after.risk] }}>{show(after)}</div>
              <div className="cmp-risk">{RISK_ICON[after.risk]} {after.risk}</div>
            </>
          ) : <div className="cmp-value muted">move a lever</div>}
        </div>
      </div>
    </div>
  )
}

export default function OfficialView({ wards, detail, onSelect, asOf, meta, t, tab, setTab, preset }) {
  const counts = ['critical', 'high', 'medium', 'low'].map((r) => [r, wards.filter((w) => w.risk === r).length])
  return (
    <div className="panel-inner">
      <div className="tiles">
        {counts.map(([r, n]) => (
          <div key={r} className="tile" style={{ '--c': RISK_COLOR[r] }}>
            <div className="tile-value">{n}</div>
            <div className="tile-label">{RISK_ICON[r]} {meta.risk_labels[r].en}</div>
          </div>
        ))}
      </div>
      <div className="subtabs">
        {[['rank', '📊 Rankings'], ['ward', '🔍 Deep dive'], ['plan', '🧪 Planner']].map(([k, l]) => (
          <button key={k} className={tab === k ? 'on' : ''} onClick={() => setTab(k)}>{l}</button>
        ))}
      </div>
      {tab === 'rank' && <Ranking wards={wards} selected={detail?.idx} onSelect={(i) => { onSelect(i); setTab('ward') }} />}
      {tab !== 'rank' && !detail && <p className="muted">Select a ward on the map or in Rankings.</p>}
      {tab === 'ward' && detail && (
        <div>
          <div className="row-between">
            <h2>{detail.name}</h2>
            <span className="risk-pill" style={{ background: RISK_COLOR[detail.risk] }}>{RISK_ICON[detail.risk]} {detail.risk}</span>
          </div>
          <div className="kpis">
            <div><b>{show(detail)}</b><span>until shortage</span></div>
            <div><b>#{detail.rank}</b><span>of {detail.of} wards</span></div>
            <div><b>{(detail.inputs.population / 1000).toFixed(0)}k</b><span>people (est.)</span></div>
          </div>
          <h3>Groundwater: history & forecast</h3>
          <GroundwaterChart ts={detail.timeseries} asOf={detail.as_of} lang="en" />
          <h3>Why (counterfactual attribution)</h3>
          <WhyList drivers={detail.drivers} labels={meta.driver_labels} t={t} lang="en" />
          <h3>Model inputs</h3>
          <table className="inputs">
            <tbody>
              <tr><td>Rainfall, last 12 months</td><td>{detail.inputs.rain_12m_mm} mm <span className="muted">(normal {detail.inputs.rain_normal_mm})</span></td><td><span className="tag real">real · ERA5</span></td></tr>
              <tr><td>Cauvery supply reliability</td><td>{detail.inputs.cauvery_supply_pct}%</td><td><span className="tag real">catchment rain</span></td></tr>
              <tr><td>Cauvery pipe coverage</td><td>{detail.inputs.cauvery_coverage_pct}%</td><td><span className="tag est">estimated</span></td></tr>
              <tr><td>Water demand</td><td>{detail.inputs.demand_mld} MLD</td><td><span className="tag est">estimated</span></td></tr>
              <tr><td>Ward area</td><td>{detail.inputs.area_km2} km²</td><td><span className="tag real">real · BBMP</span></td></tr>
            </tbody>
          </table>
          <button className="ask-btn" onClick={() => setTab('plan')}>🧪 Plan interventions for {detail.name} →</button>
        </div>
      )}
      {tab === 'plan' && detail && <Planner detail={detail} asOf={asOf} preset={preset} />}
    </div>
  )
}
