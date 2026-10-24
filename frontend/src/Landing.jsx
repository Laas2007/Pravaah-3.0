import { Link } from 'react-router-dom'
import { core } from './api'
import { RISK_COLOR, RISK_ORDER } from './i18n'
import KarnatakaMap from './shared/KarnatakaMap'
import ModelCard from './shared/ModelCard'
import { RiskLegend } from './shared/PlatformShell'
import { getMeta, useLoad } from './shared/hooks'
import { PLATFORMS } from './shared/platforms'

export default function Landing() {
  const meta = useLoad(getMeta, []).data
  const ind = useLoad(() => (meta ? core.indicators(meta.climate_until) : Promise.resolve(null)), [meta]).data
  const byIdx = ind ? ind.taluks : []
  const counts = Object.fromEntries(RISK_ORDER.map((r) => [r, byIdx.filter((t) => t.risk === r).length]))

  return (
    <div className="landing">
      <div className="landing-hero">
        <div className="landing-text">
          <div className="ps-brand big"><span className="ps-logo">💧</span><span><b>Pravaah</b><small>Karnataka</small></span></div>
          <h1>Water scarcity, predicted early, for everyone who depends on it.</h1>
          <p>One explainable engine for all 227 taluks of Karnataka, built on real rain-gauge, groundwater-well and
            reservoir records, with dedicated platforms for farmers, urban residents and industry.</p>
          <div className="landing-facts">
            <span><b>227</b> taluks</span><span><b>2,701</b> groundwater wells</span><span><b>35</b> reservoirs</span>
            <span><b>2014→{meta ? meta.climate_until.slice(0, 4) : '…'}</b> daily data</span>
          </div>
          {ind && (
            <div className="landing-now">
              Today ({meta.climate_until}):{' '}
              {RISK_ORDER.map((r) => <span key={r} style={{ color: RISK_COLOR[r] }}><b>{counts[r]}</b> {r} </span>)}
              <small> ({ind.model.startsWith('m2') ? 'ML groundwater forecast' : 'provisional index'})</small>
            </div>
          )}
        </div>
        <div className="landing-map">
          <KarnatakaMap colorOf={(i) => byIdx[i] && RISK_COLOR[byIdx[i].risk]} legend={<RiskLegend />} />
        </div>
      </div>
      <div className="landing-cards">
        {PLATFORMS.map((p) => (
          <Link key={p.key} to={p.path} className="landing-card" style={{ '--pc': p.color }}>
            <div className="landing-card-icon">{p.icon}</div>
            <div className="landing-card-title">{p.en}</div>
            <div className="landing-card-kn">{p.kn}</div>
            <p>{p.blurb}</p>
            <span className="landing-card-go">Open →</span>
          </Link>
        ))}
      </div>
      <div className="landing-model"><ModelCard /></div>
      <footer className="landing-foot">
        🟢 Real: IMD rainfall, NWDP groundwater wells & reservoirs, LGD boundaries · 🟠 Estimated: demand, supply ·
        🔵 Simulated: daily groundwater between readings
      </footer>
    </div>
  )
}
