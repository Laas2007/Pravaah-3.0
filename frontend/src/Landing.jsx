import { Link, useNavigate } from 'react-router-dom'
import { core } from './api'
import { RISK_COLOR, RISK_ORDER } from './i18n'
import KarnatakaMap from './shared/KarnatakaMap'
import ModelCard from './shared/ModelCard'
import { fetchWards, getWardGeo, wardOverlay } from './shared/wards'
import { LangButton, RiskLegend } from './shared/PlatformShell'
import { STEPS } from './shared/Tour'
import { getMeta, useLoad } from './shared/hooks'
import { RISK_TEXT, useTr } from './shared/lang'
import { PLATFORMS } from './shared/platforms'

const BLURB_KN = {
  agri: 'ನೀರಿನ ಲಭ್ಯತೆ ಆಧಾರಿತ ಬೆಳೆ ಆಯ್ಕೆ, ಬರ ಮತ್ತು ಬೆಳೆ ನೀರಿನ ಒತ್ತಡ, ನೀರಾವರಿ ವೇಳಾಪಟ್ಟಿ, ಬಿತ್ತನೆ ದಿನಾಂಕ, ಇಳುವರಿ ಅಪಾಯ, ಅಂತರ್ಜಲ ಕುಸಿತ.',
  urban: 'ವಾರ್ಡ್ ಮತ್ತು ನಗರ ಮಟ್ಟದ ಕೊರತೆ ಮುನ್ಸೂಚನೆ, ಪೂರೈಕೆ ಎಷ್ಟು ದಿನ, ಕಾವೇರಿ ಮುನ್ನೋಟ, ಟ್ಯಾಂಕರ್ ಅಗತ್ಯ, ಮಳೆನೀರು ಸಂಗ್ರಹ, ಸೋರಿಕೆ.',
  industry: 'ಸ್ಥಳದ ನೀರಿನ ಅಪಾಯ, ಕಾರ್ಯಾಚರಣೆಗೆ ಕೊರತೆ, ಬೇಡಿಕೆ ಮುನ್ಸೂಚನೆ, ಉತ್ಪಾದನೆ ಅಡಚಣೆ, ತ್ಯಾಜ್ಯನೀರು ಮರುಬಳಕೆ.',
}

export default function Landing() {
  const tr = useTr()
  const navigate = useNavigate()
  const meta = useLoad(getMeta, []).data
  const ind = useLoad(() => (meta ? core.indicators(meta.climate_until) : Promise.resolve(null)), [meta]).data
  const byIdx = ind ? ind.taluks : []
  const wardGeo = useLoad(getWardGeo, []).data
  const wards = useLoad(() => (meta ? fetchWards(meta.climate_until) : Promise.resolve(null)), [meta]).data
  const counts = Object.fromEntries(RISK_ORDER.map((r) => [r, byIdx.filter((t) => t.risk === r).length]))
  const lang = tr.lang === 'kn' ? '?lang=kn' : ''
  const startTour = () => {
    const s = STEPS[0]
    const p = new URLSearchParams({ ...s.q, tour: '0' })
    if (tr.lang === 'kn') p.set('lang', 'kn')
    navigate(`${s.path}?${p}`)
  }

  return (
    <div className={`landing lang-${tr.lang}`}>
      <div className="landing-hero">
        <div className="landing-text">
          <div className="landing-top">
            <div className="ps-brand big"><span className="ps-logo">💧</span><span><b>Pravaah</b><small>{tr('Karnataka', 'ಕರ್ನಾಟಕ')}</small></span></div>
            <LangButton light />
          </div>
          <h1>{tr('Water scarcity, predicted early, for everyone who depends on it.', 'ನೀರಿನ ಕೊರತೆ, ಮುಂಚಿತವಾಗಿ ಮುನ್ಸೂಚನೆ, ಅದನ್ನು ಅವಲಂಬಿಸಿರುವ ಎಲ್ಲರಿಗೂ.')}</h1>
          <p>{tr('One explainable engine for all 227 taluks of Karnataka and every Bengaluru ward, built on real rain-gauge, groundwater-well and reservoir records, with dedicated platforms for farmers, urban residents and industry.',
            'ಕರ್ನಾಟಕದ ಎಲ್ಲಾ 227 ತಾಲೂಕುಗಳು ಮತ್ತು ಬೆಂಗಳೂರಿನ ಪ್ರತಿ ವಾರ್ಡ್‌ಗೆ ವಿವರಿಸಬಲ್ಲ ಒಂದೇ ಮಾದರಿ: ನೈಜ ಮಳೆ ಮಾಪಕ, ಅಂತರ್ಜಲ ಬಾವಿ ಮತ್ತು ಜಲಾಶಯ ದತ್ತಾಂಶ ಆಧಾರಿತ; ರೈತರು, ನಗರ ನಿವಾಸಿಗಳು ಮತ್ತು ಉದ್ಯಮಗಳಿಗೆ ಪ್ರತ್ಯೇಕ ವೇದಿಕೆಗಳು.')}</p>
          <div className="landing-facts">
            <span><b>227</b> {tr('taluks', 'ತಾಲೂಕುಗಳು')}</span><span><b>243</b> {tr('Bengaluru wards', 'ಬೆಂಗಳೂರು ವಾರ್ಡ್‌ಗಳು')}</span>
            <span><b>2,701</b> {tr('groundwater wells', 'ಅಂತರ್ಜಲ ಬಾವಿಗಳು')}</span><span><b>35</b> {tr('reservoirs', 'ಜಲಾಶಯಗಳು')}</span>
            <span><b>2014→{meta ? meta.climate_until.slice(0, 4) : '…'}</b> {tr('daily data', 'ದೈನಂದಿನ ದತ್ತಾಂಶ')}</span>
          </div>
          {ind && (
            <div className="landing-now">
              {tr(`Today (${meta.climate_until}):`, `ಇಂದು (${meta.climate_until}):`)}{' '}
              {RISK_ORDER.map((r) => <span key={r} style={{ color: RISK_COLOR[r] }}><b>{counts[r]}</b> {tr(RISK_TEXT[r].en, RISK_TEXT[r].kn)} </span>)}
              <small> ({ind.model.startsWith('m2') ? tr('ML groundwater forecast', 'ML ಅಂತರ್ಜಲ ಮುನ್ಸೂಚನೆ') : tr('provisional index', 'ತಾತ್ಕಾಲಿಕ ಸೂಚ್ಯಂಕ')})</small>
            </div>
          )}
          <button className="landing-tour" onClick={startTour}>▶ {tr('Take the tour: the 2023 drought → 2024 crisis', 'ಪ್ರವಾಸ: 2023 ಬರ → 2024 ಬಿಕ್ಕಟ್ಟು')}</button>
        </div>
        <div className="landing-map">
          <KarnatakaMap colorOf={(i) => byIdx[i] && RISK_COLOR[byIdx[i].risk]} legend={<RiskLegend />}
            overlay={wardOverlay(wardGeo, wards, null, null)} />
        </div>
      </div>
      <div className="landing-cards">
        {PLATFORMS.map((p) => (
          <Link key={p.key} to={`${p.path}${lang}`} className="landing-card" style={{ '--pc': p.color }}>
            <div className="landing-card-icon">{p.icon}</div>
            <div className="landing-card-title">{tr(p.en, p.kn)}</div>
            <div className="landing-card-kn">{tr(p.kn, p.en)}</div>
            <p>{tr(p.blurb, BLURB_KN[p.key])}</p>
            <span className="landing-card-go">{tr('Open →', 'ತೆರೆಯಿರಿ →')}</span>
          </Link>
        ))}
      </div>
      <div className="landing-model"><ModelCard /></div>
      <footer className="landing-foot">
        {tr('🟢 Real: IMD rainfall, NWDP groundwater wells & reservoirs, LGD boundaries · 🟠 Estimated: demand, supply · 🔵 Simulated: daily groundwater between readings',
          '🟢 ನೈಜ: IMD ಮಳೆ, NWDP ಅಂತರ್ಜಲ ಬಾವಿಗಳು ಮತ್ತು ಜಲಾಶಯಗಳು, LGD ಗಡಿಗಳು · 🟠 ಅಂದಾಜು: ಬೇಡಿಕೆ, ಪೂರೈಕೆ · 🔵 ಅನುಕರಣೆ: ಮಾಪನಗಳ ನಡುವಿನ ದೈನಂದಿನ ಅಂತರ್ಜಲ')}
      </footer>
    </div>
  )
}
