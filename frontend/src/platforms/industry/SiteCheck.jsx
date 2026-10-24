// Factory site water-feasibility check: pick a point + water need -> verdict, score and every statistic behind it.
import { useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useLoad } from '../../shared/hooks'
import { useTr } from '../../shared/lang'
import { ErrorBox, Loading, Stat } from '../../shared/ui'
import { industryApi } from './api'
import Icon from '../../shared/Icon'
import './industry.css'

// Example KIADB industrial areas (approximate centres) to try the check quickly
export const SITE_EXAMPLES = [
  { name: 'Narasapura (Kolar)', lat: 13.14, lon: 78.05 },
  { name: 'Hebbal (Mysuru)', lat: 12.36, lon: 76.6 },
  { name: 'Belur (Dharwad)', lat: 15.47, lon: 74.94 },
  { name: 'Vasanthanarasapura (Tumakuru)', lat: 13.39, lon: 77.06 },
  { name: 'Kolhar (Bidar)', lat: 17.9, lon: 77.53 },
  { name: 'Baikampady (Mangaluru)', lat: 12.95, lon: 74.82 },
]
export const VERDICT = {
  feasible: { color: '#0ca30c', text: ['Feasible', 'ಕಾರ್ಯಸಾಧ್ಯ'] },
  conditional: { color: '#fab219', text: ['Feasible with conditions', 'ಷರತ್ತುಗಳೊಂದಿಗೆ ಕಾರ್ಯಸಾಧ್ಯ'] },
  risky: { color: '#d9661f', text: ['Risky', 'ಅಪಾಯಕಾರಿ'] },
  not_recommended: { color: '#d03b3b', text: ['Not recommended', 'ಶಿಫಾರಸು ಮಾಡುವುದಿಲ್ಲ'] },
}
const CAT = {
  safe: ['Safe', 'ಸುರಕ್ಷಿತ'], semi_critical: ['Semi-critical', 'ಅರೆ-ಗಂಭೀರ'],
  critical: ['Critical', 'ಗಂಭೀರ'], over_exploited: ['Over-exploited', 'ಅತಿ ಬಳಕೆ'],
}
const scoreColor = (s) => (s >= 70 ? '#0ca30c' : s >= 45 ? '#fab219' : s >= 25 ? '#ec6b1c' : '#d03b3b')

/** Site lives in the URL (?site=lat,lon&kld=&gw=&ha=) so a check can be shared or opened from a demo link. */
export function useSite() {
  const [params, setParams] = useSearchParams()
  const s = params.get('site')
  const [lat, lon] = s ? s.split(',').map(Number) : [null, null]
  const site = s && Number.isFinite(lat) && Number.isFinite(lon) ? { lat, lon } : null
  const req = { kld: Number(params.get('kld')) || null, gw: params.get('gw') != null ? Number(params.get('gw')) : null,
    ha: Number(params.get('ha')) || null }
  const set = (patch) => setParams((p) => {
    Object.entries(patch).forEach(([k, v]) => (v == null || v === '' ? p.delete(k) : p.set(k, v)))
    return p
  }, { replace: true })
  return { site, req, set }
}

export default function SiteCheck({ asOf, picking, setPicking }) {
  const tr = useTr()
  const { site, req, set } = useSite()
  const [form, setForm] = useState({ kld: req.kld ?? 1000, auto: req.gw == null, gw: req.gw != null ? Math.round(req.gw * 100) : 50, ha: req.ha ?? '' })
  const [lat, setLat] = useState(site ? site.lat.toFixed(4) : '')
  const [lon, setLon] = useState(site ? site.lon.toFixed(4) : '')
  const [lastSite, setLastSite] = useState(site)
  if (site && (site.lat !== lastSite?.lat || site.lon !== lastSite?.lon)) {   // point picked on the map
    setLastSite(site)
    setLat(site.lat.toFixed(4))
    setLon(site.lon.toFixed(4))
  }
  const run = site && req.kld
  const res = useLoad(() => (run && asOf ? industryApi.feasibility({ ...site, kld: req.kld, gw: req.gw, ha: req.ha, asOf }) : Promise.resolve(null)),
    [run, site?.lat, site?.lon, req.kld, req.gw, req.ha, asOf])

  const submit = (e) => {
    e.preventDefault()
    const la = Number(lat), lo = Number(lon)
    if (!Number.isFinite(la) || !Number.isFinite(lo) || !form.kld) return
    set({ site: `${la.toFixed(4)},${lo.toFixed(4)}`, kld: form.kld, gw: form.auto ? null : form.gw / 100, ha: form.ha || null })
    setPicking(false)
  }
  const kld = Number(form.kld) || 0

  return (
    <div className="ps-card industry-site" data-tour="site">
      <h2>{tr('Can a factory get its water here?', 'ಇಲ್ಲಿ ಕಾರ್ಖಾನೆಗೆ ನೀರು ಸಿಗುತ್ತದೆಯೇ?')}</h2>
      <div className="muted small">{tr('Pick a location anywhere in Karnataka and enter the factory\'s daily water need. You get a verdict with every statistic behind it.',
        'ಕರ್ನಾಟಕದಲ್ಲಿ ಸ್ಥಳ ಆಯ್ಕೆಮಾಡಿ ಮತ್ತು ಕಾರ್ಖಾನೆಯ ದೈನಂದಿನ ನೀರಿನ ಅಗತ್ಯ ನಮೂದಿಸಿ. ತೀರ್ಮಾನ ಮತ್ತು ಎಲ್ಲಾ ಅಂಕಿಅಂಶಗಳು ಸಿಗುತ್ತವೆ.')}</div>
      <form className="industry-form" onSubmit={submit}>
        <label className="industry-wide">{tr('Location', 'ಸ್ಥಳ')}
          <div className="industry-row">
            <input value={lat} onChange={(e) => setLat(e.target.value)} placeholder={tr('latitude', 'ಅಕ್ಷಾಂಶ')} inputMode="decimal" />
            <input value={lon} onChange={(e) => setLon(e.target.value)} placeholder={tr('longitude', 'ರೇಖಾಂಶ')} inputMode="decimal" />
            <button type="button" className={`industry-pick ${picking ? 'on' : ''}`} onClick={() => setPicking(!picking)}>
              {picking ? tr('Click the map…', 'ನಕ್ಷೆ ಕ್ಲಿಕ್ ಮಾಡಿ…') : tr('Pick on map', 'ನಕ್ಷೆಯಲ್ಲಿ ಆಯ್ಕೆ')}</button>
          </div>
          <div className="industry-chips">
            {SITE_EXAMPLES.map((x) => (
              <button type="button" key={x.name} onClick={() => { setLat(String(x.lat)); setLon(String(x.lon)) }}>{x.name}</button>
            ))}
          </div>
        </label>
        <label>{tr('Water need (kL per day)', 'ನೀರಿನ ಅಗತ್ಯ (ದಿನಕ್ಕೆ kL)')}
          <input type="number" min="1" step="any" value={form.kld} onChange={(e) => setForm({ ...form, kld: e.target.value })} />
          <span className="muted small">{tr(`= ${(kld / 1000).toFixed(2)} MLD · ${Math.round(kld * 365 / 1000).toLocaleString()} ML a year · like ${(kld / 20).toFixed(1)} ha of KIADB land`,
            `= ${(kld / 1000).toFixed(2)} MLD · ವರ್ಷಕ್ಕೆ ${Math.round(kld * 365 / 1000).toLocaleString()} ML`)}</span>
        </label>
        <label>{tr('Site area (ha, optional)', 'ಸ್ಥಳದ ವಿಸ್ತೀರ್ಣ (ಹೆ., ಐಚ್ಛಿಕ)')}
          <input type="number" min="0" step="any" value={form.ha} onChange={(e) => setForm({ ...form, ha: e.target.value })} />
          <span className="muted small">{tr('for rainwater harvesting', 'ಮಳೆನೀರು ಕೊಯ್ಲಿಗಾಗಿ')}</span>
        </label>
        <label className="industry-wide">{tr('Share from groundwater (borewells)', 'ಅಂತರ್ಜಲದ ಪಾಲು (ಕೊಳವೆಬಾವಿ)')}
          <div className="industry-row">
            <label className="industry-check"><input type="checkbox" checked={form.auto} onChange={(e) => setForm({ ...form, auto: e.target.checked })} />
              {tr('Typical for the district', 'ಜಿಲ್ಲೆಯ ಸಾಮಾನ್ಯ')}</label>
            {!form.auto && <><input type="range" min="0" max="100" step="5" value={form.gw} onChange={(e) => setForm({ ...form, gw: Number(e.target.value) })} />
              <b>{form.gw}%</b></>}
          </div>
        </label>
        <button className="industry-go" type="submit" disabled={!lat || !lon || !kld}>{tr('Check feasibility', 'ಕಾರ್ಯಸಾಧ್ಯತೆ ಪರಿಶೀಲಿಸಿ')}</button>
      </form>
      {res.error && <ErrorBox error={res.error} />}
      {run && !res.data && !res.error && <Loading what="site report" />}
      {res.data && <Report d={res.data} onClear={() => set({ site: null, kld: null, gw: null, ha: null })} />}
    </div>
  )
}

function Report({ d, onClear }) {
  const tr = useTr()
  const v = VERDICT[d.verdict]
  const g = d.groundwater, o = g.official, w = g.wells, s = d.surface, r = d.rain, dm = d.demand
  const trendTxt = w.trend_m_per_year == null ? tr('not enough readings', 'ಸಾಕಷ್ಟು ದತ್ತಾಂಶ ಇಲ್ಲ')
    : w.trend_m_per_year > 0 ? tr(`falling ${w.trend_m_per_year} m/yr`, `ವರ್ಷಕ್ಕೆ ${w.trend_m_per_year} ಮೀ ಕುಸಿತ`)
      : tr(`rising ${Math.abs(w.trend_m_per_year)} m/yr`, `ವರ್ಷಕ್ಕೆ ${Math.abs(w.trend_m_per_year)} ಮೀ ಏರಿಕೆ`)
  return (
    <div className="industry-report">
      <div className="industry-verdict" style={{ borderColor: v.color }}>
        <div className="industry-score" style={{ background: v.color }}>{d.score}<small>/100</small></div>
        <div>
          <div className="industry-verdict-text" style={{ color: v.color }}>{tr(...v.text)}</div>
          <div><b>{d.taluk}</b> · {d.district} · {d.lat.toFixed(3)}, {d.lon.toFixed(3)}</div>
          <div className="muted small">{tr(`${dm.kld.toLocaleString()} kL/day: ${Math.round(dm.groundwater_share * 100)}% groundwater${dm.groundwater_share_default ? ' (district typical)' : ''}, ${Math.round((1 - dm.groundwater_share) * 100)}% surface · as of ${d.as_of}`,
            `${dm.kld.toLocaleString()} kL/ದಿನ: ${Math.round(dm.groundwater_share * 100)}% ಅಂತರ್ಜಲ · ${d.as_of}`)}</div>
        </div>
        <button className="industry-close" onClick={onClear} aria-label={tr('Clear', 'ತೆರವು')}><Icon name="close" size={18} /></button>
      </div>
      {d.gates.map((x) => <div key={x} className="ps-note industry-gate">{x}</div>)}

      <h3>{tr('Why this verdict?', 'ಈ ತೀರ್ಮಾನ ಏಕೆ?')}</h3>
      <div className="ps-why">
        {d.components.map((c) => (
          <div key={c.key} className="industry-comp">
            <div className="ps-why-row">
              <span>{c.label}</span>
              <div className="ps-why-bar"><i style={{ width: `${c.score}%`, background: scoreColor(c.score) }} /></div>
              <b>{c.score}</b>
            </div>
            <div className="muted small">{c.why} · {tr(`weight ${Math.round(c.weight * 100) / 100}`, `ತೂಕ ${Math.round(c.weight * 100) / 100}`)}</div>
          </div>
        ))}
      </div>
      <div className="muted small">{tr(`Score = weighted average (groundwater items weigh the groundwater share, reservoir the surface share, rain 0.5). ≥70 feasible · 45–69 with conditions · 25–44 risky · <25 not recommended. Expected days with a supply shortfall in the next 6 months for this mix: ${d.shortfall_days_6m}.`,
        `ಅಂಕ = ತೂಕದ ಸರಾಸರಿ. ≥70 ಕಾರ್ಯಸಾಧ್ಯ · 45–69 ಷರತ್ತು · 25–44 ಅಪಾಯ · <25 ಶಿಫಾರಸು ಇಲ್ಲ. ಮುಂದಿನ 6 ತಿಂಗಳಲ್ಲಿ ಕೊರತೆಯ ದಿನಗಳು: ${d.shortfall_days_6m}.`)}</div>

      <h3>{tr('Groundwater', 'ಅಂತರ್ಜಲ')}</h3>
      <div className="ps-stats">
        {o && <Stat label={tr('Official status (CGWB 2023)', 'ಅಧಿಕೃತ ಸ್ಥಿತಿ (CGWB 2023)')} value={tr(...CAT[o.category])}
          tone={o.category === 'safe' ? '' : 'bad'} sub={tr(`${o.stage_pct}% of extractable water already pumped`, `ಹೊರತೆಗೆಯಬಹುದಾದ ನೀರಿನ ${o.stage_pct}% ಈಗಾಗಲೇ ಬಳಕೆ`)} />}
        {o && <Stat label={tr('Still available for new use', 'ಹೊಸ ಬಳಕೆಗೆ ಲಭ್ಯ')} value={o.future_mld} unit="MLD" tone={g.nothing_available ? 'bad' : ''}
          sub={g.nothing_available ? tr('nothing left officially', 'ಅಧಿಕೃತವಾಗಿ ಏನೂ ಉಳಿದಿಲ್ಲ')
            : tr(`your groundwater part = ${g.share_of_available_pct}% of it`, `ನಿಮ್ಮ ಪಾಲು = ${g.share_of_available_pct}%`)} />}
        {o && <Stat label={tr('Taluk pumping vs recharge', 'ತಾಲೂಕು ಬಳಕೆ vs ಮರುಪೂರಣ')} value={`${o.extraction_mld} / ${o.extractable_mld}`} unit="MLD"
          sub={tr(`${o.irrigation_share_pct}% for irrigation · industry ${o.industrial_mld} MLD`, `${o.irrigation_share_pct}% ನೀರಾವರಿ · ಕೈಗಾರಿಕೆ ${o.industrial_mld} MLD`)} />}
        <Stat label={tr('Forecast (M2)', 'ಮುನ್ಸೂಚನೆ (M2)')} value={g.days_mid == null ? '–' : g.days_mid >= 366 ? tr('6+ months', '6+ ತಿಂಗಳು') : `${Math.round(g.days_mid)} ${tr('days', 'ದಿನ')}`}
          sub={tr(`until stress (likely); dry year: ${g.days_low == null ? '–' : g.days_low >= 366 ? '6+ months' : Math.round(g.days_low) + ' days'}`, 'ಒತ್ತಡದವರೆಗೆ (ಸಂಭಾವ್ಯ)')} />
        <Stat label={tr(`Wells within ${w.radius_km} km`, `${w.radius_km} ಕಿಮೀ ಒಳಗಿನ ಬಾವಿಗಳು`)} value={w.count}
          sub={w.count ? tr(`water at ${w.depth_now_m} m (deepest ${w.deepest_now_m} m)`, `ನೀರು ${w.depth_now_m} ಮೀ ಆಳದಲ್ಲಿ`) : tr(`nearest ${w.nearest_km} km away`, `ಹತ್ತಿರದ್ದು ${w.nearest_km} ಕಿಮೀ`)} />
        {w.count > 0 && <Stat label={tr('Well trend', 'ಬಾವಿ ಪ್ರವೃತ್ತಿ')} value={trendTxt} tone={(w.trend_m_per_year || 0) > 0.3 ? 'bad' : ''}
          sub={tr(`${w.trend_years}${w.change_10y_m != null ? ` · ${w.change_10y_m > 0 ? '+' : ''}${w.change_10y_m} m over ${w.change_years}` : ''} (+ = deeper)`,
            `${w.trend_years}${w.change_10y_m != null ? ` · ${w.change_years}: ${w.change_10y_m} ಮೀ` : ''}`)} />}
      </div>
      {g.footprint_km2 != null && dm.groundwater_kld > 0 && <div className="muted small">{tr(`The groundwater part (${dm.groundwater_kld.toLocaleString()} kL/day) equals all the extractable recharge of ${g.footprint_km2} km² of this taluk (${d.taluk_area_km2} km² in total).`,
        `ಅಂತರ್ಜಲ ಪಾಲು ಈ ತಾಲೂಕಿನ ${g.footprint_km2} ಕಿಮೀ² ಮರುಪೂರಣಕ್ಕೆ ಸಮ.`)}</div>}

      <h3>{tr('Surface water', 'ಮೇಲ್ಮೈ ನೀರು')}</h3>
      {s ? (
        <div className="ps-stats">
          <Stat label={tr('Reservoir system', 'ಜಲಾಶಯ ವ್ಯವಸ್ಥೆ')} value={s.system} sub={s.dams.join(', ')} />
          <Stat label={tr('Storage now', 'ಈಗಿನ ಸಂಗ್ರಹ')} value={`${s.pct_full}%`} sub={`${s.storage_now_tmc} / ${s.capacity_tmc} TMC`} />
          <Stat label={tr('Chance of low storage (6 months, M4)', 'ಕಡಿಮೆ ಸಂಗ್ರಹ ಸಾಧ್ಯತೆ (M4)')} value={`${Math.round(s.p_low_6m * 100)}%`}
            tone={s.p_low_6m >= 0.25 ? 'bad' : ''} sub={tr('below 15% of capacity', 'ಸಾಮರ್ಥ್ಯದ 15% ಕ್ಕಿಂತ ಕಡಿಮೆ')} />
          <Stat label={tr('Your surface draw', 'ನಿಮ್ಮ ಮೇಲ್ಮೈ ಬಳಕೆ')} value={dm.surface_kld.toLocaleString()} unit="kL/day"
            sub={tr(`${s.demand_share_of_storage_pct}% of current storage per year; needs a WRD / KIADB allocation`, `ಪ್ರಸ್ತುತ ಸಂಗ್ರಹದ ${s.demand_share_of_storage_pct}% ವರ್ಷಕ್ಕೆ`)} />
        </div>
      ) : <div className="ps-note">{tr('No modelled reservoir system serves this district: surface water would come from tanks, a KIADB scheme or tankers.',
        'ಈ ಜಿಲ್ಲೆಗೆ ಮಾದರಿ ಜಲಾಶಯ ವ್ಯವಸ್ಥೆ ಇಲ್ಲ: ಕೆರೆಗಳು, KIADB ಯೋಜನೆ ಅಥವಾ ಟ್ಯಾಂಕರ್‌ಗಳು.')} {tr(`Minor-irrigation tanks in the taluk: ${d.context.tanks_in_taluk} (${d.context.tank_storage_mcm ?? 0} million m³).`, `ತಾಲೂಕಿನ ಕೆರೆಗಳು: ${d.context.tanks_in_taluk}.`)}</div>}

      <h3>{tr('Rain & climate', 'ಮಳೆ ಮತ್ತು ಹವಾಮಾನ')}</h3>
      <div className="ps-stats">
        <Stat label={tr('Normal yearly rain', 'ವಾಡಿಕೆ ವಾರ್ಷಿಕ ಮಳೆ')} value={r.normal_mm} unit="mm" sub={tr(`${r.normal_years}, varies ±${r.variability_pct}%`, `${r.normal_years}, ±${r.variability_pct}%`)} />
        <Stat label={tr('Last 12 months', 'ಕಳೆದ 12 ತಿಂಗಳು')} value={r.last_12m_mm} unit="mm" tone={r.last_12m_dev_pct <= -20 ? 'bad' : ''}
          sub={tr(`${r.last_12m_dev_pct > 0 ? '+' : ''}${r.last_12m_dev_pct}% vs normal`, `ವಾಡಿಕೆಗಿಂತ ${r.last_12m_dev_pct}%`)} />
        <Stat label={tr('Kharif droughts (M1 labels)', 'ಮುಂಗಾರು ಬರ (M1)')} value={`${r.drought.drought_years.length} / ${r.drought.years_checked}`}
          sub={r.drought.drought_years.length ? r.drought.drought_years.join(', ') : tr('none', 'ಇಲ್ಲ')} />
        <Stat label={tr('Evaporation demand (ET0)', 'ಆವಿಯಾಗುವಿಕೆ (ET0)')} value={r.et0_12m_mm} unit="mm/yr"
          sub={tr(`hottest day ${r.tmax_12m_c} °C (cooling-water loss)`, `ಅತಿ ಬಿಸಿ ದಿನ ${r.tmax_12m_c} °C`)} />
      </div>

      <h3>{tr('Cutting the fresh-water need', 'ತಾಜಾ ನೀರಿನ ಅಗತ್ಯ ಕಡಿತ')}</h3>
      <div className="ps-stats">
        <Stat label={tr('Recycle 70% of wastewater', 'ತ್ಯಾಜ್ಯನೀರಿನ 70% ಮರುಬಳಕೆ')} value={`−${d.offsets.reuse_kld.toLocaleString()}`} unit="kL/day" />
        {d.offsets.rainwater_kld != null && <Stat label={tr('Rainwater harvesting', 'ಮಳೆನೀರು ಕೊಯ್ಲು')} value={`−${d.offsets.rainwater_kld.toLocaleString()}`} unit="kL/day" sub={tr('yearly average', 'ವಾರ್ಷಿಕ ಸರಾಸರಿ')} />}
        <Stat label={tr('Fresh water still needed', 'ಇನ್ನೂ ಬೇಕಾದ ತಾಜಾ ನೀರು')} value={d.offsets.fresh_after_offsets_kld.toLocaleString()} unit="kL/day" />
        <Stat label={tr('Other KIADB industry in district', 'ಜಿಲ್ಲೆಯ ಇತರ KIADB ಕೈಗಾರಿಕೆ')} value={d.context.kiadb_demand_mld_district} unit="MLD"
          sub={tr(`${d.context.kiadb_areas_in_district} industrial areas (estimated use)`, `${d.context.kiadb_areas_in_district} ಕೈಗಾರಿಕಾ ಪ್ರದೇಶಗಳು`)} />
      </div>

      <h3>{tr('What to do', 'ಏನು ಮಾಡಬೇಕು')}</h3>
      <ul className="industry-recs">{d.recommendations.map((x) => <li key={x}>{x}</li>)}</ul>
      <div className="muted small">{tr(`Real data: ${d.sources.real.join(', ')}. Estimated: ${d.sources.estimated.join(', ')}. The score is a transparent rule set (there are no public records of factory water failures to train on). It is a screening check, not a permit: groundwater use needs CGWA/KGWA permission and surface water a WRD/KIADB allocation.`,
        `ನೈಜ ದತ್ತಾಂಶ: ${d.sources.real.join(', ')}. ಅಂದಾಜು: ${d.sources.estimated.join(', ')}. ಇದು ಪ್ರಾಥಮಿಕ ಪರಿಶೀಲನೆ, ಅನುಮತಿ ಅಲ್ಲ.`)}</div>
    </div>
  )
}
