// 🌾 Agriculture & Farmers. TODO list: backend/usecases/agri.py
import { core } from '../../api'
import KarnatakaMap from '../../shared/KarnatakaMap'
import TalukDetail from '../../shared/TalukDetail'
import { platform } from '../../shared/platforms'
import PlatformShell from '../../shared/PlatformShell'
import { useAsOf, useLoad, useTalukSel } from '../../shared/hooks'
import { ErrorBox, Loading, MockBanner, RiskBadge, Stat, m, pct } from '../../shared/ui'
import { agriApi } from './api'

// rain deviation (last 3 months) -> brown (dry) .. green (wet)
function devColor(v) {
  if (v == null) return null
  if (v <= -50) return '#8c510a'
  if (v <= -25) return '#d8b365'
  if (v <= -10) return '#f6e8c3'
  if (v < 10) return '#e9f0e4'
  if (v < 40) return '#a6d96a'
  return '#1a9641'
}

export default function AgriPlatform() {
  const [asOf, setAsOf, meta] = useAsOf()
  const [sel, setSel] = useTalukSel()
  const ind = useLoad(() => (asOf ? core.indicators(asOf) : Promise.resolve(null)), [asOf]).data
  const byIdx = ind ? ind.taluks : []

  const map = (
    <KarnatakaMap selected={sel} onSelect={setSel}
      colorOf={(i) => devColor(byIdx[i]?.rain_90d_dev_pct)}
      labelOf={(i) => byIdx[i] && `Rain, last 3 months: ${pct(byIdx[i].rain_90d_dev_pct)} vs normal`}
      legend={<><span><i style={{ background: '#8c510a' }} />≤ −50%</span><span><i style={{ background: '#d8b365' }} />−25%</span>
        <span><i style={{ background: '#e9f0e4' }} />normal</span><span><i style={{ background: '#1a9641' }} />+40%</span></>} />
  )

  return (
    <PlatformShell which="agri" asOf={asOf} setAsOf={setAsOf} meta={meta} map={map}>
      {sel == null
        ? <div className="ps-empty">👆 Click your taluk on the map to see season rainfall, water stress and crop advice.</div>
        : <><TalukDetail idx={sel} asOf={asOf} color={platform('agri').color} onClose={() => setSel(null)} /><Detail idx={sel} asOf={asOf} /></>}
    </PlatformShell>
  )
}

function Detail({ idx, asOf }) {
  const { data: a, error } = useLoad(() => agriApi.taluk(idx, asOf), [idx, asOf])
  if (error) return <ErrorBox error={error} />
  if (!a) return <Loading what="taluk" />
  const s = a.season
  return (
    <div className="ps-card">
      <div className="ps-card-head"><div><h2>{a.name}</h2><div className="muted small">{a.district} district</div></div><RiskBadge risk={a.risk} /></div>
      <h3>{s.name} season so far ({s.days} days since {s.start})</h3>
      <div className="ps-stats">
        <Stat label="Rain" value={Math.round(s.rain_mm)} unit="mm" sub={`${pct(s.dev_pct)} vs normal (${Math.round(s.normal_mm)} mm)`} tone={s.dev_pct < -25 ? 'bad' : ''} />
        <Stat label="Crop water demand (ET0)" value={Math.round(s.et0_mm)} unit="mm" sub="FAO reference, ERA5" />
        <Stat label="Water balance" value={Math.round(s.water_balance_mm)} unit="mm" sub="rain − ET0" tone={s.water_balance_mm < -100 ? 'bad' : ''} />
        <Stat label="Groundwater" value={a.groundwater.depth_m?.toFixed(1)} unit="m" sub={`${m(a.groundwater.anom_m)} vs normal`} />
      </div>
      <h3>Crops vs water need</h3>
      <MockBanner>{a.crops.note}</MockBanner>
      <table className="ps-table">
        <thead><tr><th>Crop</th><th>Season water need</th><th>Fits normal rain?</th></tr></thead>
        <tbody>
          {a.crops.items.map((c) => (
            <tr key={c.crop}><td><b>{c.crop}</b> <span className="muted">{c.kn}</span></td><td>{c.water_need_mm} mm</td>
              <td>{c.fits_normal_rain ? '✅' : '⚠️ needs irrigation'}</td></tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
