// 🏙️ Urban Population. TODO list: backend/usecases/urban.py
// The full Bengaluru ward model lives in ./BengaluruApp.jsx (route /urban/bengaluru).
import { Link } from 'react-router-dom'
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { RISK_COLOR } from '../../i18n'
import KarnatakaMap from '../../shared/KarnatakaMap'
import PlatformShell, { RiskLegend } from '../../shared/PlatformShell'
import TalukDetail from '../../shared/TalukDetail'
import { useAsOf, useLoad, useTalukSel } from '../../shared/hooks'
import { platform } from '../../shared/platforms'
import { ErrorBox, Loading, MockBanner, ProvisionalNote, RiskBadge, Stat, m, pct } from '../../shared/ui'
import { urbanApi } from './api'

const COLOR = platform('urban').color

export default function UrbanPlatform() {
  const [asOf, setAsOf, meta] = useAsOf()
  const [sel, setSel] = useTalukSel()
  const res = useLoad(() => (asOf ? urbanApi.cities(asOf) : Promise.resolve(null)), [asOf])
  const cities = res.data?.cities || []

  const map = (
    <KarnatakaMap selected={sel} onSelect={setSel} legend={<RiskLegend />}
      points={cities.filter((c) => c.lat).map((c) => ({
        key: c.city, lat: c.lat, lon: c.lon, color: RISK_COLOR[c.risk], radius: c.live_ward_model ? 12 : 8,
        label: `${c.city}: ${c.risk} risk`, onClick: () => setSel(c.taluk_idx),
      }))} />
  )

  return (
    <PlatformShell which="urban" asOf={asOf} setAsOf={setAsOf} meta={meta} map={map}>
      <Link to={`/urban/bengaluru?as_of=${asOf || ''}`} className="ps-hero-link">
        <span>🏙️</span>
        <div><b>Bengaluru ward-level model</b><div className="small">243 wards · days-until-shortage · why · interventions · 2024 backtest · EN/ಕನ್ನಡ chatbot</div></div>
        <span>→</span>
      </Link>
      {sel != null && <TalukDetail idx={sel} asOf={asOf} color={COLOR} onClose={() => setSel(null)} />}
      {asOf && <CauveryOutlook asOf={asOf} />}
      <h2>Cities across Karnataka</h2>
      <ProvisionalNote model={res.data?.model} />
      <MockBanner>Population and supply (MLD) are rough estimates until city data is added.</MockBanner>
      {res.error && <ErrorBox error={res.error} />}
      {!res.data ? <Loading what="cities" /> : (
        <table className="ps-table">
          <thead><tr><th>City</th><th>Risk</th><th>Rain 12 m</th><th>Groundwater</th><th>Supply</th></tr></thead>
          <tbody>
            {cities.map((c) => (
              <tr key={c.city} onClick={() => setSel(c.taluk_idx)}>
                <td><b>{c.city}</b><div className="muted small">{c.population_lakh} lakh people</div></td>
                <td><RiskBadge risk={c.risk} /></td><td>{pct(c.rain_365d_dev_pct)}</td><td>{m(c.gw_anom_m)}</td><td>{c.supply_mld} MLD</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </PlatformShell>
  )
}

/** Storage in KRS + Kabini + Harangi + Hemavathy, which feed Bengaluru's Cauvery piped supply. */
function CauveryOutlook({ asOf }) {
  const { data: c, error } = useLoad(() => urbanApi.cauvery(asOf), [asOf])
  if (error) return <ErrorBox error={error} />
  if (!c) return <Loading what="Cauvery storage" />
  const vs = c.normal_tmc ? (c.storage_tmc / c.normal_tmc - 1) * 100 : null
  return (
    <div className="ps-card">
      <h2>Cauvery supply outlook</h2>
      <div className="muted small">KRS, Kabini, Harangi, Hemavathy: the dams behind Bengaluru's piped water. Real daily data (NWDP).</div>
      <div className="ps-stats">
        <Stat label="Storage now" value={c.storage_tmc} unit="TMC" sub={`of ${c.capacity_tmc} TMC`} />
        <Stat label="vs normal for this day" value={pct(vs)} sub={`normal ${c.normal_tmc} TMC`} tone={vs < -20 ? 'bad' : ''} />
      </div>
      <div style={{ height: 170 }}>
        <ResponsiveContainer>
          <ComposedChart data={c.series} margin={{ top: 6, right: 8, left: -14, bottom: 0 }}>
            <CartesianGrid stroke="#eef1f5" vertical={false} />
            <XAxis dataKey="date" tick={{ fontSize: 10 }} interval={60} />
            <YAxis tick={{ fontSize: 10 }} domain={[0, c.capacity_tmc]} />
            <Tooltip />
            <Line dataKey="normal_tmc" name="normal" stroke="#9aa6b5" strokeDasharray="4 3" dot={false} isAnimationActive={false} />
            <Area dataKey="storage_tmc" name="storage" stroke={COLOR} fill={COLOR} fillOpacity={0.18} strokeWidth={2} isAnimationActive={false} />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
      <MockBanner>Storage forecast and "months of supply left" come with model M4.</MockBanner>
    </div>
  )
}
