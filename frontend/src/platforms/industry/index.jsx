// 🏭 Industries & Businesses. TODO list: backend/usecases/industry.py
import { RISK_COLOR } from '../../i18n'
import KarnatakaMap from '../../shared/KarnatakaMap'
import PlatformShell, { RiskLegend } from '../../shared/PlatformShell'
import PlatformChat from '../../shared/PlatformChat'
import TalukDetail from '../../shared/TalukDetail'
import TimeMachine from '../../shared/TimeMachine'
import { useAsOf, useLoad, usePlaceSel, useTaluk } from '../../shared/hooks'
import { useTr } from '../../shared/lang'
import { platform } from '../../shared/platforms'
import { WardCard, fetchWards, getWardGeo, wardOverlay } from '../../shared/wards'
import { ErrorBox, Loading, RiskBadge, Stat } from '../../shared/ui'
import { industryApi } from './api'

const COLOR = platform('industry').color

export default function IndustryPlatform() {
  const tr = useTr()
  const [asOf, setAsOf, meta] = useAsOf()
  const { taluk: sel, ward: wsel, selectTaluk: setSel, selectWard: setWard } = usePlaceSel()
  const taluk = useTaluk(sel)
  const wardGeo = useLoad(getWardGeo, []).data
  const wards = useLoad(() => (asOf ? fetchWards(asOf) : Promise.resolve(null)), [asOf]).data
  const res = useLoad(() => (asOf ? industryApi.districts(asOf) : Promise.resolve(null)), [asOf])
  const rows = res.data?.districts || []
  const byTaluk = {}
  rows.forEach((r) => r.taluk_idx.forEach((i) => { byTaluk[i] = r }))

  const map = (
    <KarnatakaMap selected={sel} onSelect={setSel} legend={<RiskLegend />}
      overlay={wardOverlay(wardGeo, wards, wsel, setWard)}
      colorOf={(i) => byTaluk[i] && RISK_COLOR[byTaluk[i].risk]}
      labelOf={(i) => byTaluk[i] && tr(`${byTaluk[i].district}: ${byTaluk[i].output_at_risk_pct}% industrial output at risk (6 months)`,
        `${byTaluk[i].district}: ${byTaluk[i].output_at_risk_pct}% ಕೈಗಾರಿಕಾ ಉತ್ಪಾದನೆ ಅಪಾಯದಲ್ಲಿ`)} />
  )

  return (
    <PlatformShell which="industry" asOf={asOf} setAsOf={setAsOf} meta={meta} map={map}>
      <div className="ps-empty">📍 {tr('Map colour = industrial water-disruption risk per district. Click any taluk, or any Bengaluru ward (zoom in), for a site-level water report.',
        'ನಕ್ಷೆಯ ಬಣ್ಣ = ಜಿಲ್ಲೆಯ ಕೈಗಾರಿಕಾ ನೀರಿನ ಅಡಚಣೆ ಅಪಾಯ. ಸ್ಥಳ ವರದಿಗಾಗಿ ತಾಲೂಕು ಅಥವಾ ಬೆಂಗಳೂರು ವಾರ್ಡ್ ಕ್ಲಿಕ್ ಮಾಡಿ.')}</div>
      {wsel != null && wards && <WardCard ward={wards.wards[wsel]} asOf={wards.as_of} onClose={() => setWard(null)} />}
      {sel != null && <TalukDetail idx={sel} asOf={asOf} color={COLOR} onClose={() => setSel(null)} />}
      {res.error && <ErrorBox error={res.error} />}
      {!res.data ? <Loading what="industrial risk" /> : <Disruption data={res.data} onSelect={setSel} />}
      {asOf && sel == null && <TimeMachine asOf={asOf} color={COLOR} />}
      <PlatformChat platform="industry" asOf={asOf} taluk={taluk} ward={wsel != null && wards ? wards.wards[wsel] : null} />
    </PlatformShell>
  )
}

function Disruption({ data, onSelect }) {
  const tr = useTr()
  const t = data.totals
  const a = data.assumptions
  return (
    <div className="ps-card" data-tour="m7">
      <h2>🏭 {tr('Industrial water-disruption risk (next 6 months)', 'ಕೈಗಾರಿಕಾ ನೀರಿನ ಅಡಚಣೆ ಅಪಾಯ (ಮುಂದಿನ 6 ತಿಂಗಳು)')}</h2>
      <div className="muted small">{tr('KIADB industrial land per district (real) × water-use norm (estimated) → demand; groundwater forecast (M2) and reservoir forecast (M4) → share of the next 6 months with a shortfall.',
        'ಜಿಲ್ಲೆಯ KIADB ಕೈಗಾರಿಕಾ ಭೂಮಿ (ನೈಜ) × ನೀರಿನ ಬಳಕೆ ಮಾನದಂಡ (ಅಂದಾಜು) → ಬೇಡಿಕೆ; ಅಂತರ್ಜಲ (M2) ಮತ್ತು ಜಲಾಶಯ (M4) ಮುನ್ಸೂಚನೆ → ಮುಂದಿನ 6 ತಿಂಗಳ ಕೊರತೆಯ ಪಾಲು.')}</div>
      <div className="ps-stats">
        <Stat label={tr('KIADB industrial water demand', 'KIADB ಕೈಗಾರಿಕಾ ನೀರಿನ ಬೇಡಿಕೆ')} value={t.demand_mld} unit="MLD"
          sub={tr(`${Math.round(t.developed_acres).toLocaleString()} acres developed`, `${Math.round(t.developed_acres).toLocaleString()} ಎಕರೆ ಅಭಿವೃದ್ಧಿ`)} />
        <Stat label={tr('Water at risk', 'ಅಪಾಯದಲ್ಲಿರುವ ನೀರು')} value={t.water_at_risk_mld} unit="MLD" tone={t.water_at_risk_mld > 50 ? 'bad' : ''} />
        <Stat label={tr('Reuse potential', 'ಮರುಬಳಕೆ ಸಾಮರ್ಥ್ಯ')} value={t.reuse_potential_mld} unit="MLD"
          sub={tr('if 70% of wastewater is recycled (STP / ZLD)', 'ತ್ಯಾಜ್ಯನೀರಿನ 70% ಮರುಬಳಸಿದರೆ')} />
      </div>
      <table className="ps-table">
        <thead><tr><th>{tr('District', 'ಜಿಲ್ಲೆ')}</th><th>{tr('Risk', 'ಅಪಾಯ')}</th><th>{tr('Output at risk', 'ಉತ್ಪಾದನೆ ಅಪಾಯ')}</th>
          <th>{tr('Demand', 'ಬೇಡಿಕೆ')}</th><th>{tr('Main source', 'ಮುಖ್ಯ ಮೂಲ')}</th></tr></thead>
        <tbody>
          {data.districts.map((r) => (
            <tr key={r.district} onClick={() => r.taluk_idx[0] != null && onSelect(r.taluk_idx[0])}>
              <td><b>{r.district}</b><div className="muted small">{tr(`${r.kiadb_areas} KIADB areas`, `${r.kiadb_areas} KIADB ಪ್ರದೇಶಗಳು`)}</div></td>
              <td><RiskBadge risk={r.risk} /></td>
              <td><b>{r.output_at_risk_pct}%</b><div className="muted small">{r.water_at_risk_mld} MLD</div></td>
              <td>{r.demand_mld} MLD</td>
              <td className="small">{r.reservoir_system
                ? <>{r.reservoir_system}<div className="muted">{tr(`${Math.round(r.reservoir_p_low_6m * 100)}% chance of low storage`, `ಕಡಿಮೆ ಸಂಗ್ರಹ ${Math.round(r.reservoir_p_low_6m * 100)}% ಸಾಧ್ಯತೆ`)}</div></>
                : tr('Groundwater', 'ಅಂತರ್ಜಲ')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <div className="muted small" style={{ marginTop: 6 }}>{tr(`Assumptions (estimated): ${a.water_norm_kl_per_ha_day} kL per hectare per day; ${a.surface_dependence_served * 100}% surface water where a modelled reservoir system serves the district, else ${a.surface_dependence_unserved * 100}%. There are no public records of industrial water disruption to train on, so this is a transparent score, not a trained model.`,
        `ಊಹೆಗಳು (ಅಂದಾಜು): ಹೆಕ್ಟೇರ್‌ಗೆ ದಿನಕ್ಕೆ ${a.water_norm_kl_per_ha_day} kL; ಜಲಾಶಯ ಸೇವೆ ಇರುವಲ್ಲಿ ${a.surface_dependence_served * 100}% ಮೇಲ್ಮೈ ನೀರು. ತರಬೇತಿಗೆ ಸಾರ್ವಜನಿಕ ದತ್ತಾಂಶ ಇಲ್ಲದ ಕಾರಣ ಇದು ಪಾರದರ್ಶಕ ಅಂಕ.`)}</div>
    </div>
  )
}
