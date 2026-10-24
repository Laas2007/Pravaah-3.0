import { Link, useNavigate } from 'react-router-dom'
import { core } from './api'
import { RISK_COLOR, RISK_ORDER } from './i18n'
import KarnatakaMap from './shared/KarnatakaMap'
import ModelCard from './shared/ModelCard'
import Icon from './shared/Icon'
import { fetchWards, getWardGeo, wardOverlay } from './shared/wards'
import { LangButton, RiskLegend } from './shared/PlatformShell'
import { STEPS } from './shared/Tour'
import { getMeta, useLoad } from './shared/hooks'
import { RISK_TEXT, useTr } from './shared/lang'
import { DataTag } from './shared/ui'
import { PLATFORMS } from './shared/platforms'

const BLURB = {
  agri: ['Kharif drought alerts, crop water stress and yield risk, irrigation schedules and sowing dates for every taluk.',
    'ಪ್ರತಿ ತಾಲೂಕಿಗೆ ಮುಂಗಾರು ಬರ ಎಚ್ಚರಿಕೆ, ಬೆಳೆ ನೀರಿನ ಒತ್ತಡ ಮತ್ತು ಇಳುವರಿ ಅಪಾಯ, ನೀರಾವರಿ ವೇಳಾಪಟ್ಟಿ ಮತ್ತು ಬಿತ್ತನೆ ದಿನಾಂಕಗಳು.'],
  urban: ['Days to shortage for each of Bengaluru\'s 243 wards and other cities, the Cauvery reservoir outlook and tanker demand.',
    'ಬೆಂಗಳೂರಿನ 243 ವಾರ್ಡ್‌ಗಳು ಮತ್ತು ಇತರ ನಗರಗಳಿಗೆ ಕೊರತೆಗೆ ಉಳಿದ ದಿನಗಳು, ಕಾವೇರಿ ಜಲಾಶಯ ಮುನ್ನೋಟ ಮತ್ತು ಟ್ಯಾಂಕರ್ ಬೇಡಿಕೆ.'],
  industry: ['Check whether a new factory site can get its water, and see district disruption risk from groundwater and reservoirs.',
    'ಹೊಸ ಕಾರ್ಖಾನೆ ಸ್ಥಳಕ್ಕೆ ನೀರು ಸಿಗುತ್ತದೆಯೇ ಎಂದು ಪರಿಶೀಲಿಸಿ; ಅಂತರ್ಜಲ ಮತ್ತು ಜಲಾಶಯಗಳಿಂದ ಜಿಲ್ಲಾ ಅಡಚಣೆ ಅಪಾಯ.'],
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
  const facts = [
    ['227', tr('taluks forecast', 'ತಾಲೂಕುಗಳ ಮುನ್ಸೂಚನೆ')],
    ['243', tr('Bengaluru wards', 'ಬೆಂಗಳೂರು ವಾರ್ಡ್‌ಗಳು')],
    ['2,664', tr('government monitoring wells', 'ಸರ್ಕಾರಿ ಮೇಲ್ವಿಚಾರಣಾ ಬಾವಿಗಳು')],
    ['34', tr('reservoirs, daily storage', 'ಜಲಾಶಯಗಳು, ದೈನಂದಿನ ಸಂಗ್ರಹ')],
    [`2014–${meta ? meta.climate_until.slice(0, 4) : '…'}`, tr('daily rain records', 'ದೈನಂದಿನ ಮಳೆ ದಾಖಲೆ')],
  ]

  return (
    <div className={`landing lang-${tr.lang}`}>
      <header className="landing-bar">
        <div className="ps-brand"><span className="ps-logo"><Icon name="drop" size={20} stroke={2} /></span>
          <span><b>Pravaah</b><small>{tr('Karnataka water forecasts', 'ಕರ್ನಾಟಕ ನೀರಿನ ಮುನ್ಸೂಚನೆ')}</small></span></div>
        <nav className="landing-links">
          {PLATFORMS.map((p) => <Link key={p.key} to={`${p.path}${lang}`}>{tr(p.en, p.kn)}</Link>)}
          <a href="#model">{tr('Accuracy', 'ನಿಖರತೆ')}</a>
        </nav>
        <LangButton light />
      </header>
      <section className="landing-hero">
        <div className="landing-text">
          <h1>{tr('How long until each taluk in Karnataka runs short of groundwater?', 'ಕರ್ನಾಟಕದ ಪ್ರತಿ ತಾಲೂಕಿನಲ್ಲಿ ಅಂತರ್ಜಲ ಕೊರತೆ ಎಷ್ಟು ದಿನಗಳಲ್ಲಿ?')}</h1>
          <p>{tr('Pravaah forecasts the days left before groundwater reaches stress in all 227 taluks and every Bengaluru ward, from government well readings, IMD rain gauges and reservoir records. Each forecast shows the reasons behind it and how the model scored on years it never saw.',
            'ಪ್ರವಾಹ ಎಲ್ಲಾ 227 ತಾಲೂಕುಗಳು ಮತ್ತು ಬೆಂಗಳೂರಿನ ಪ್ರತಿ ವಾರ್ಡ್‌ನಲ್ಲಿ ಅಂತರ್ಜಲ ಒತ್ತಡ ತಲುಪಲು ಉಳಿದ ದಿನಗಳನ್ನು ಸರ್ಕಾರಿ ಬಾವಿ ದಾಖಲೆ, IMD ಮಳೆ ಮಾಪಕ ಮತ್ತು ಜಲಾಶಯ ದತ್ತಾಂಶದಿಂದ ಮುನ್ಸೂಚಿಸುತ್ತದೆ. ಪ್ರತಿ ಮುನ್ಸೂಚನೆ ಕಾರಣಗಳನ್ನು ಮತ್ತು ನೋಡದ ವರ್ಷಗಳಲ್ಲಿ ಮಾದರಿಯ ನಿಖರತೆಯನ್ನು ತೋರಿಸುತ್ತದೆ.')}</p>
          <dl className="landing-facts">
            {facts.map(([n, l]) => <div key={l}><dt>{n}</dt><dd>{l}</dd></div>)}
          </dl>
          {ind && (
            <div className="landing-now">
              <div className="landing-now-head">{tr(`Groundwater outlook on ${meta.climate_until}`, `${meta.climate_until} ರ ಅಂತರ್ಜಲ ಮುನ್ನೋಟ`)}</div>
              <div className="landing-now-row">
                {RISK_ORDER.map((r) => (
                  <span key={r}><i style={{ background: RISK_COLOR[r] }} /><b>{counts[r]}</b> {tr(RISK_TEXT[r].en, RISK_TEXT[r].kn)}</span>
                ))}
              </div>
              <small>{ind.model.startsWith('m2') ? tr('Taluks by risk tier, ML forecast from monitoring wells', 'ಅಪಾಯ ಮಟ್ಟದ ಪ್ರಕಾರ ತಾಲೂಕುಗಳು, ಬಾವಿ ದತ್ತಾಂಶದ ML ಮುನ್ಸೂಚನೆ')
                : tr('Taluks by risk tier, provisional index', 'ಅಪಾಯ ಮಟ್ಟದ ಪ್ರಕಾರ ತಾಲೂಕುಗಳು, ತಾತ್ಕಾಲಿಕ ಸೂಚ್ಯಂಕ')}</small>
            </div>
          )}
          <div className="landing-actions">
            <Link className="btn-primary" to={`/agri${lang}`}>{tr('Open the taluk map', 'ತಾಲೂಕು ನಕ್ಷೆ ತೆರೆಯಿರಿ')}</Link>
            <button className="btn-secondary" onClick={startTour}>{tr('Guided tour: 2023 drought to 2024 crisis', 'ಮಾರ್ಗದರ್ಶಿ ಪ್ರವಾಸ: 2023 ಬರದಿಂದ 2024 ಬಿಕ್ಕಟ್ಟು')}</button>
          </div>
        </div>
        <div className="landing-map">
          <KarnatakaMap colorOf={(i) => byIdx[i] && RISK_COLOR[byIdx[i].risk]} legend={<RiskLegend />}
            overlay={wardOverlay(wardGeo, wards, null, null)} />
        </div>
      </section>
      <section className="landing-cards">
        {PLATFORMS.map((p) => (
          <Link key={p.key} to={`${p.path}${lang}`} className="landing-card" style={{ '--pc': p.color }}>
            <div className="landing-card-head"><span className="landing-card-icon"><Icon name={p.icon} size={22} /></span>
              <div><div className="landing-card-title">{tr(p.en, p.kn)}</div><div className="landing-card-kn">{tr(p.kn, p.en)}</div></div></div>
            <p>{tr(...BLURB[p.key])}</p>
            <span className="landing-card-go">{tr('Open', 'ತೆರೆಯಿರಿ')} <Icon name="arrow" size={16} /></span>
          </Link>
        ))}
      </section>
      <section className="landing-model" id="model"><ModelCard /></section>
      <footer className="landing-foot">
        <span><DataTag k="real" />{tr('IMD rainfall, NWDP groundwater wells and reservoirs, CGWB groundwater assessment 2023, LGD boundaries',
          'IMD ಮಳೆ, NWDP ಅಂತರ್ಜಲ ಬಾವಿಗಳು ಮತ್ತು ಜಲಾಶಯಗಳು, CGWB ಅಂತರ್ಜಲ ಮೌಲ್ಯಮಾಪನ 2023, LGD ಗಡಿಗಳು')}</span>
        <span><DataTag k="estimated" />{tr('urban demand, industrial water norms', 'ನಗರ ಬೇಡಿಕೆ, ಕೈಗಾರಿಕಾ ನೀರಿನ ಮಾನದಂಡ')}</span>
        <span><DataTag k="simulated" />{tr('daily ward groundwater between well readings, leak test meters', 'ಬಾವಿ ಮಾಪನಗಳ ನಡುವಿನ ದೈನಂದಿನ ವಾರ್ಡ್ ಅಂತರ್ಜಲ, ಸೋರಿಕೆ ಪರೀಕ್ಷಾ ಮೀಟರ್‌ಗಳು')}</span>
      </footer>
    </div>
  )
}
