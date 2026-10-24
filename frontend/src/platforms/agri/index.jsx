// Agriculture & Farmers. TODO list: backend/usecases/agri.py
import { core } from '../../api'
import KarnatakaMap from '../../shared/KarnatakaMap'
import TalukDetail from '../../shared/TalukDetail'
import TimeMachine from '../../shared/TimeMachine'
import PlatformChat from '../../shared/PlatformChat'
import { platform } from '../../shared/platforms'
import PlatformShell from '../../shared/PlatformShell'
import { useAsOf, useLoad, useTaluk, useTalukSel } from '../../shared/hooks'
import { useTr } from '../../shared/lang'
import { ErrorBox, Loading, RiskBadge, Stat, m, pct } from '../../shared/ui'
import { agriApi } from './api'
import { useMemo } from 'react'
import CropAdvisor from './CropAdvisor'
import DroughtCard from './DroughtCard'
import { useLayerMap } from '../../shared/layers'
import StateSummary, { talukItems } from '../../shared/StateSummary'

const COLOR = platform('agri').color
const SEASON_KN = { Kharif: 'ಮುಂಗಾರು', Rabi: 'ಹಿಂಗಾರು', Summer: 'ಬೇಸಿಗೆ' }

export default function AgriPlatform() {
  const tr = useTr()
  const [asOf, setAsOf, meta] = useAsOf()
  const [sel, setSel] = useTalukSel()
  const taluk = useTaluk(sel)
  const ind = useLoad(() => (asOf ? core.indicators(asOf) : Promise.resolve(null)), [asOf]).data
  const dr = useLoad(() => (asOf ? agriApi.drought(asOf) : Promise.resolve(null)), [asOf]).data
  const byIdx = useMemo(() => {
    if (!ind) return []
    const d = dr && dr.in_season ? Object.fromEntries(dr.taluks.map((t) => [t.idx, t])) : {}
    return ind.taluks.map((r) => ({ ...r, drought_level: d[r.idx]?.level, drought_p: d[r.idx]?.p_drought }))
  }, [ind, dr])

  const lm = useLayerMap({ layers: ['risk', 'drought', 'heat', 'rain3', 'waterbal', 'groundwater'], fallback: 'risk', rows: byIdx })
  const map = (
    <KarnatakaMap selected={sel} onSelect={setSel} colorOf={lm.colorOf} labelOf={lm.labelOf} indexMode={lm.index}
      ui={<>{lm.switcher}{lm.title}{lm.legend}</>} />
  )

  return (
    <PlatformShell which="agri" asOf={asOf} setAsOf={setAsOf} meta={meta} map={map}>
      {sel == null
        ? <>
          {ind && <StateSummary kicker={tr('Karnataka · farm taluks', 'ಕರ್ನಾಟಕ · ಕೃಷಿ ತಾಲೂಕುಗಳು')} asOf={asOf} items={talukItems(byIdx, tr)}
            text={tr(<>taluks where groundwater is <b>likely to reach stress within 6 months</b> (critical or high), from the ML forecast on 2,664 wells</>,
              <>ತಾಲೂಕುಗಳಲ್ಲಿ <b>6 ತಿಂಗಳೊಳಗೆ ಅಂತರ್ಜಲ ಒತ್ತಡ ಸಾಧ್ಯತೆ</b> (ಗಂಭೀರ ಅಥವಾ ಹೆಚ್ಚು), 2,664 ಬಾವಿಗಳ ML ಮುನ್ಸೂಚನೆ</>)}
            urgentTitle={tr('Most urgent taluks', 'ಅತ್ಯಂತ ತುರ್ತು ತಾಲೂಕುಗಳು')} onPick={(x) => setSel(x.idx)} />}
          <div className="ps-empty">{tr('Click your taluk on the map to see season rainfall, groundwater forecast and crop advice.',
            'ಋತುವಿನ ಮಳೆ, ಅಂತರ್ಜಲ ಮುನ್ಸೂಚನೆ ಮತ್ತು ಬೆಳೆ ಸಲಹೆಗಾಗಿ ನಕ್ಷೆಯಲ್ಲಿ ನಿಮ್ಮ ತಾಲೂಕು ಕ್ಲಿಕ್ ಮಾಡಿ.')}</div>
          {asOf && <TimeMachine asOf={asOf} color={COLOR} />}
        </>
        : <><TalukDetail idx={sel} asOf={asOf} color={COLOR} onClose={() => setSel(null)} /><DroughtCard idx={sel} asOf={asOf} /><CropAdvisor idx={sel} asOf={asOf} /><Detail idx={sel} asOf={asOf} /></>}
      <PlatformChat platform="agri" asOf={asOf} taluk={taluk} />
    </PlatformShell>
  )
}

function Detail({ idx, asOf }) {
  const tr = useTr()
  const { data: a, error } = useLoad(() => agriApi.taluk(idx, asOf), [idx, asOf])
  if (error) return <ErrorBox error={error} />
  if (!a) return <Loading what="taluk" />
  const s = a.season
  return (
    <div className="ps-card">
      <div className="ps-card-head"><div><h2>{a.name}</h2><div className="muted small">{tr(`${a.district} district`, `${a.district} ಜಿಲ್ಲೆ`)}</div></div><RiskBadge risk={a.risk} /></div>
      <h3>{tr(`${s.name} season so far (${s.days} days since ${s.start})`, `${SEASON_KN[s.name] || s.name} ಋತು ಇಲ್ಲಿಯವರೆಗೆ (${s.start} ರಿಂದ ${s.days} ದಿನ)`)}</h3>
      <div className="ps-stats">
        <Stat label={tr('Rain', 'ಮಳೆ')} value={Math.round(s.rain_mm)} unit="mm"
          sub={tr(`${pct(s.dev_pct)} vs normal (${Math.round(s.normal_mm)} mm)`, `ವಾಡಿಕೆಗಿಂತ ${pct(s.dev_pct)} (${Math.round(s.normal_mm)} ಮಿ.ಮೀ.)`)} tone={s.dev_pct < -25 ? 'bad' : ''} />
        <Stat label={tr('Crop water demand (ET0)', 'ಬೆಳೆ ನೀರಿನ ಬೇಡಿಕೆ (ET0)')} value={Math.round(s.et0_mm)} unit="mm" sub={tr('FAO reference, ERA5', 'FAO ಉಲ್ಲೇಖ, ERA5')} />
        <Stat label={tr('Water balance', 'ನೀರಿನ ಸಮತೋಲನ')} value={Math.round(s.water_balance_mm)} unit="mm" sub={tr('rain − ET0', 'ಮಳೆ − ET0')} tone={s.water_balance_mm < -100 ? 'bad' : ''} />
        <Stat label={tr('Groundwater', 'ಅಂತರ್ಜಲ')} value={a.groundwater.depth_m?.toFixed(1)} unit="m" sub={tr(`${m(a.groundwater.anom_m)} vs normal`, `ವಾಡಿಕೆಗಿಂತ ${m(a.groundwater.anom_m)}`)} />
      </div>
    </div>
  )
}
