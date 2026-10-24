// Urban Population. TODO list: backend/usecases/urban.py
// The full Bengaluru ward model lives in ./BengaluruApp.jsx (route /urban/bengaluru).
import { Link } from 'react-router-dom'
import { Area, CartesianGrid, ComposedChart, Line, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { RISK_COLOR } from '../../i18n'
import Icon from '../../shared/Icon'
import KarnatakaMap from '../../shared/KarnatakaMap'
import PlatformShell from '../../shared/PlatformShell'
import PlatformChat from '../../shared/PlatformChat'
import TalukDetail from '../../shared/TalukDetail'
import TimeMachine from '../../shared/TimeMachine'
import { useAsOf, useLoad, usePlaceSel, useTaluk } from '../../shared/hooks'
import { useTr } from '../../shared/lang'
import { WardCard, daysText, fetchWards, getWardGeo, wardOverlay } from '../../shared/wards'
import { platform } from '../../shared/platforms'
import { ErrorBox, Loading, MockBanner, ProvisionalNote, RiskBadge, Stat, m, pct } from '../../shared/ui'
import { urbanApi } from './api'
import { core } from '../../api'
import { useLayerMap } from '../../shared/layers'
import StateSummary from '../../shared/StateSummary'
import { DemandCard, LeakCard } from './UrbanModels'

const COLOR = platform('urban').color

export default function UrbanPlatform() {
  const tr = useTr()
  const [asOf, setAsOf, meta] = useAsOf()
  const { taluk: sel, ward: wsel, selectTaluk: setSel, selectWard: setWard } = usePlaceSel()
  const taluk = useTaluk(sel)
  const res = useLoad(() => (asOf ? urbanApi.cities(asOf) : Promise.resolve(null)), [asOf])
  const cities = res.data?.cities || []
  const wardGeo = useLoad(getWardGeo, []).data
  const wards = useLoad(() => (asOf ? fetchWards(asOf) : Promise.resolve(null)), [asOf]).data
  const lang = tr.lang === 'kn' ? '&lang=kn' : ''
  const ind = useLoad(() => (asOf ? core.indicators(asOf) : Promise.resolve(null)), [asOf]).data
  const lm = useLayerMap({ layers: ['risk', 'heat', 'groundwater', 'rain12'], fallback: 'risk', rows: ind ? ind.taluks : [] })

  const map = (
    <KarnatakaMap selected={sel} onSelect={setSel} colorOf={lm.colorOf} labelOf={lm.labelOf} indexMode={lm.index}
      ui={<>{lm.switcher}{lm.title}{lm.legend}</>}
      overlay={wardOverlay(wardGeo, wards, wsel, setWard, lm.wardColor)}
      points={cities.filter((c) => c.lat && !c.live_ward_model).map((c) => ({
        key: c.city, lat: c.lat, lon: c.lon, color: RISK_COLOR[c.risk], radius: 8,
        label: `${c.city}: ${c.risk}`, onClick: () => setSel(c.taluk_idx),
      }))} />
  )

  return (
    <PlatformShell which="urban" asOf={asOf} setAsOf={setAsOf} meta={meta} map={map}>
      <Link to={`/urban/bengaluru?as_of=${asOf || ''}${lang}`} className="ps-hero-link">
        <span></span>
        <div><b>{tr('Bengaluru ward-level model', 'ಬೆಂಗಳೂರು ವಾರ್ಡ್ ಮಟ್ಟದ ಮಾದರಿ')}</b>
          <div className="small">{tr('243 wards · days-until-shortage · why · interventions · 2024 Time Machine · EN/ಕನ್ನಡ chatbot',
            '243 ವಾರ್ಡ್‌ಗಳು · ಕೊರತೆಗೆ ದಿನಗಳು · ಕಾರಣ · ಪರಿಹಾರ · 2024 ಟೈಮ್ ಮೆಷಿನ್ · ಚಾಟ್‌ಬಾಟ್')}</div></div>
        <Icon name="arrow" size={18} />
      </Link>
      {wsel != null && wards && <WardCard ward={wards.wards[wsel]} asOf={wards.as_of} onClose={() => setWard(null)} />}
      {sel != null && <TalukDetail idx={sel} asOf={asOf} color={COLOR} onClose={() => setSel(null)} />}
      {wards && <WardSummary wards={wards} onSelect={setWard} />}
      {asOf && <CauveryOutlook asOf={asOf} />}
      {asOf && <DemandCard asOf={asOf} onWard={setWard} />}
      <LeakCard />
      <h2>{tr('Cities across Karnataka', 'ಕರ್ನಾಟಕದ ನಗರಗಳು')}</h2>
      <ProvisionalNote model={res.data?.model} />
      <MockBanner>{tr('Population and supply (MLD) are rough estimates until city data is added.', 'ಜನಸಂಖ್ಯೆ ಮತ್ತು ಪೂರೈಕೆ (MLD) ಸ್ಥೂಲ ಅಂದಾಜುಗಳು.')}</MockBanner>
      {res.error && <ErrorBox error={res.error} />}
      {!res.data ? <Loading what="cities" /> : (
        <table className="ps-table">
          <thead><tr><th>{tr('City', 'ನಗರ')}</th><th>{tr('Risk', 'ಅಪಾಯ')}</th><th>{tr('Rain 12 m', '12 ತಿಂ. ಮಳೆ')}</th><th>{tr('Groundwater', 'ಅಂತರ್ಜಲ')}</th><th>{tr('Supply', 'ಪೂರೈಕೆ')}</th></tr></thead>
          <tbody>
            {cities.map((c) => (
              <tr key={c.city} onClick={() => setSel(c.taluk_idx)}>
                <td><b>{c.city}</b><div className="muted small">{tr(`${c.population_lakh} lakh people`, `${c.population_lakh} ಲಕ್ಷ ಜನ`)}</div></td>
                <td><RiskBadge risk={c.risk} /></td><td>{pct(c.rain_365d_dev_pct)}</td><td>{m(c.gw_anom_m)}</td><td>{c.supply_mld} MLD</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
      {asOf && sel == null && <TimeMachine asOf={asOf} color={COLOR} />}
      <PlatformChat platform="urban" asOf={asOf} taluk={taluk} ward={wsel != null && wards ? wards.wards[wsel] : null} />
    </PlatformShell>
  )
}

/** Bengaluru at ward level: counts and the most urgent wards (click to open). */
function WardSummary({ wards, onSelect }) {
  const tr = useTr()
  const order = { critical: 0, high: 1, medium: 2, low: 3 }
  const items = [...wards.wards].sort((a, b) => order[a.risk] - order[b.risk] || a.days_mid - b.days_mid || a.groundwater_pct - b.groundwater_pct)
    .map((w) => ({ key: w.idx, idx: w.idx, name: w.name, sub: tr(`ward ${w.ward_no}`, `ವಾರ್ಡ್ ${w.ward_no}`), risk: w.risk,
      right: w.days_mid === 0 ? tr('now', 'ಈಗ') : w.days_mid > 365 ? '365+ d' : `${w.days_low}–${w.days_high > 365 ? '365+' : w.days_high} d` }))
  return (
    <div data-tour="wards">
      <StateSummary kicker={tr('Bengaluru · 243 wards', 'ಬೆಂಗಳೂರು · 243 ವಾರ್ಡ್‌ಗಳು')} asOf={wards.as_of} items={items}
        text={tr(<>wards are expected to run short of water <b>within 90 days</b> (ward-level water balance on IMD rain). Use "Bengaluru wards" on the map to zoom in.</>,
          <>ವಾರ್ಡ್‌ಗಳಲ್ಲಿ <b>90 ದಿನಗಳೊಳಗೆ</b> ನೀರಿನ ಕೊರತೆ ನಿರೀಕ್ಷೆ (IMD ಮಳೆಯ ಮೇಲೆ ವಾರ್ಡ್ ಮಟ್ಟದ ಜಲ ಸಮತೋಲನ).</>)}
        urgentTitle={tr('Most urgent wards', 'ಅತ್ಯಂತ ತುರ್ತು ವಾರ್ಡ್‌ಗಳು')} onPick={(x) => onSelect(x.idx)} />
    </div>
  )
}

/** Storage in KRS + Kabini + Harangi + Hemavathy, which feed Bengaluru's Cauvery piped supply. */
function CauveryOutlook({ asOf }) {
  const tr = useTr()
  const { data: c, error } = useLoad(() => urbanApi.cauvery(asOf), [asOf])
  if (error) return <ErrorBox error={error} />
  if (!c) return <Loading what="Cauvery storage" />
  const vs = c.normal_tmc ? (c.storage_tmc / c.normal_tmc - 1) * 100 : null
  const f = c.forecast
  const last = f?.points[f.points.length - 1]
  const maxLow = f ? Math.max(...f.points.map((p) => p.p_low)) : 0
  // real time axis (ms) so the 6-month forecast gets its true width next to the past year
  const ts = (d) => new Date(d + 'T00:00:00Z').getTime()
  const cut = ts(asOf) - 365 * 864e5
  const past = c.series.filter((r) => ts(r.date) >= cut).map((r) => ({ ...r, t: ts(r.date) }))
  const lastPast = past[past.length - 1]
  const fut = f ? f.points.map((p) => ({ t: ts(p.date), band: [p.p10, p.p90], mid: p.p50, actual: p.actual ?? undefined })) : []
  if (f && lastPast) fut.unshift({ t: lastPast.t, band: [lastPast.storage_tmc, lastPast.storage_tmc], mid: lastPast.storage_tmc })
  const data = [...past, ...fut]
  const fmt = (t) => new Date(t).toISOString().slice(0, 7)
  return (
    <div className="ps-card" data-tour="cauvery">
      <h2>{tr('Cauvery supply outlook', 'ಕಾವೇರಿ ಪೂರೈಕೆ ಮುನ್ನೋಟ')}</h2>
      <div className="muted small">{tr('KRS, Kabini, Harangi, Hemavathy: the dams behind Bengaluru\'s piped water. Real daily data (NWDP).',
        'ಕೆಆರ್‌ಎಸ್, ಕಬಿನಿ, ಹಾರಂಗಿ, ಹೇಮಾವತಿ: ಬೆಂಗಳೂರಿನ ಕೊಳವೆ ನೀರಿನ ಜಲಾಶಯಗಳು. ನೈಜ ದೈನಂದಿನ ದತ್ತಾಂಶ (NWDP).')}</div>
      <div className="ps-stats">
        <Stat label={tr('Storage now', 'ಈಗಿನ ಸಂಗ್ರಹ')} value={c.storage_tmc} unit="TMC" sub={tr(`of ${c.capacity_tmc} TMC`, `${c.capacity_tmc} TMC ಯಲ್ಲಿ`)} />
        <Stat label={tr('vs normal for this day', 'ಈ ದಿನದ ವಾಡಿಕೆಗೆ ಹೋಲಿಸಿ')} value={pct(vs)} sub={tr(`normal ${c.normal_tmc} TMC`, `ವಾಡಿಕೆ ${c.normal_tmc} TMC`)} tone={vs < -20 ? 'bad' : ''} />
        {f && <Stat label={tr('In 6 months (likely)', '6 ತಿಂಗಳಲ್ಲಿ (ಸಂಭಾವ್ಯ)')} value={last.p50} unit="TMC"
          sub={tr(`range ${last.p10}–${last.p90} TMC`, `ವ್ಯಾಪ್ತಿ ${last.p10}–${last.p90} TMC`)} tone={last.p50 < f.low_threshold_tmc * 1.5 ? 'bad' : ''} />}
        {f && <Stat label={tr('Supply outlook', 'ಪೂರೈಕೆ ಮುನ್ನೋಟ')}
          value={f.months_of_supply != null ? tr(`${f.months_of_supply} months`, `${f.months_of_supply} ತಿಂಗಳು`) : tr('6+ months', '6+ ತಿಂಗಳು')}
          sub={tr(`until storage falls below ${f.low_threshold_tmc} TMC (15%) on the likely path · ${Math.round(maxLow * 100)}% chance within 6 months`,
            `ಸಂಗ್ರಹ ${f.low_threshold_tmc} TMC (15%) ಕ್ಕಿಂತ ಕೆಳಗೆ ಇಳಿಯುವವರೆಗೆ · 6 ತಿಂಗಳಲ್ಲಿ ${Math.round(maxLow * 100)}% ಸಾಧ್ಯತೆ`)} />}
      </div>
      <div style={{ height: 190 }}>
        <ResponsiveContainer>
          <ComposedChart data={data} margin={{ top: 6, right: 8, left: -14, bottom: 0 }}>
            <CartesianGrid stroke="#eef1f5" vertical={false} />
            <XAxis dataKey="t" type="number" scale="time" domain={['dataMin', 'dataMax']} tickFormatter={fmt} tick={{ fontSize: 10 }} tickCount={7} />
            <YAxis tick={{ fontSize: 10 }} domain={[0, c.capacity_tmc]} />
            <Tooltip labelFormatter={(t) => new Date(t).toISOString().slice(0, 10)} formatter={(v) => (Array.isArray(v) ? `${v[0]}–${v[1]} TMC` : `${v} TMC`)} />
            <ReferenceLine x={ts(asOf)} stroke="#9aa6b5" />
            {f && <ReferenceLine y={f.low_threshold_tmc} stroke="#d03b3b" strokeDasharray="4 3" />}
            <Line dataKey="normal_tmc" name={tr('normal', 'ವಾಡಿಕೆ')} stroke="#9aa6b5" strokeDasharray="4 3" dot={false} isAnimationActive={false} />
            <Area dataKey="storage_tmc" name={tr('storage', 'ಸಂಗ್ರಹ')} stroke={COLOR} fill={COLOR} fillOpacity={0.18} strokeWidth={2} isAnimationActive={false} />
            <Area dataKey="band" name={tr('forecast range', 'ಮುನ್ಸೂಚನೆ ವ್ಯಾಪ್ತಿ')} stroke="none" fill="#ec835a" fillOpacity={0.2} isAnimationActive={false} />
            <Line dataKey="mid" name={tr('forecast', 'ಮುನ್ಸೂಚನೆ')} stroke="#ec835a" strokeDasharray="5 3" strokeWidth={2} dot={false} isAnimationActive={false} />
            <Line dataKey="actual" name={tr('what happened', 'ನಿಜವಾಗಿ')} stroke="#0b1b2e" dot={{ r: 3 }} strokeWidth={0} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      {f && <div className="muted small">{tr(`M4 forecast (${f.mode === 'production' ? 'latest model' : 'model trained only to 2021, so this replay is a genuine test'}): orange = next 6 months, dots = actual storage when already known. Policy releases (e.g. to Tamil Nadu) are not predictable from rain.`,
        `M4 ಮುನ್ಸೂಚನೆ: ಕಿತ್ತಳೆ = ಮುಂದಿನ 6 ತಿಂಗಳು, ಚುಕ್ಕೆ = ನಿಜವಾದ ಸಂಗ್ರಹ. ನೀತಿ ಬಿಡುಗಡೆಗಳನ್ನು (ಉದಾ. ತಮಿಳುನಾಡಿಗೆ) ಮಳೆಯಿಂದ ಊಹಿಸಲಾಗದು.`)}</div>}
    </div>
  )
}
