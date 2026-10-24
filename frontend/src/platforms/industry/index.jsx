// 🏭 Industries & Businesses. TODO list: backend/usecases/industry.py
import { useState } from 'react'
import { core } from '../../api'
import { RISK_COLOR } from '../../i18n'
import KarnatakaMap from '../../shared/KarnatakaMap'
import PlatformShell, { RiskLegend } from '../../shared/PlatformShell'
import TalukDetail from '../../shared/TalukDetail'
import { useAsOf, useLoad } from '../../shared/hooks'
import { ErrorBox, Loading, MockBanner, ProvisionalNote, RiskBadge, m, pct } from '../../shared/ui'
import { industryApi } from './api'

export default function IndustryPlatform() {
  const [asOf, setAsOf, meta] = useAsOf()
  const [sel, setSel] = useState(null)
  const ind = useLoad(() => (asOf ? core.indicators(asOf) : Promise.resolve(null)), [asOf]).data
  const res = useLoad(() => (asOf ? industryApi.areas(asOf) : Promise.resolve(null)), [asOf])
  const areas = res.data?.areas || []
  const byIdx = ind ? ind.taluks : []

  const map = (
    <KarnatakaMap selected={sel} onSelect={setSel} legend={<RiskLegend />}
      colorOf={(i) => byIdx[i] && RISK_COLOR[byIdx[i].risk] + '66'}
      points={areas.map((a) => ({
        key: a.area, lat: a.taluk_lat, lon: a.taluk_lon, color: RISK_COLOR[a.risk],
        label: `${a.area} (${a.sector}): ${a.risk} risk`, onClick: () => setSel(a.taluk_idx),
      }))} />
  )

  return (
    <PlatformShell which="industry" asOf={asOf} setAsOf={setAsOf} meta={meta} map={map}>
      <div className="ps-empty">📍 Click any taluk on the map to get a water-risk report for a business location.</div>
      {sel != null && <TalukDetail idx={sel} asOf={asOf} onClose={() => setSel(null)} />}
      <h2>Industrial areas</h2>
      <ProvisionalNote />
      <MockBanner>Area list, sectors and demand are placeholders until the KIADB data is cleaned.</MockBanner>
      {res.error && <ErrorBox error={res.error} />}
      {!res.data ? <Loading what="industrial areas" /> : (
        <table className="ps-table">
          <thead><tr><th>Area</th><th>Risk</th><th>Rain 12 m</th><th>Groundwater</th><th>Demand</th></tr></thead>
          <tbody>
            {areas.map((a) => (
              <tr key={a.area} onClick={() => setSel(a.taluk_idx)}>
                <td><b>{a.area}</b><div className="muted small">{a.sector} · {a.taluk}</div></td>
                <td><RiskBadge risk={a.risk} /></td><td>{pct(a.rain_365d_dev_pct)}</td><td>{m(a.gw_anom_m)}</td><td>{a.demand_mld} MLD</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </PlatformShell>
  )
}
