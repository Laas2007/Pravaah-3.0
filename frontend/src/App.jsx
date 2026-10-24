import { useCallback, useEffect, useMemo, useState } from 'react'
import { api } from './api'
import { T } from './i18n'
import MapView from './MapView'
import Timeline from './Timeline'
import Overview from './Overview'
import CitizenView from './CitizenView'
import OfficialView from './OfficialView'
import BacktestView from './BacktestView'
import Chat from './Chat'
import Tour from './Tour'

const params = new URLSearchParams(window.location.search)

const NAV = [
  { key: 'overview', icon: '🏙️', en: 'Overview', kn: 'ಸಾರಾಂಶ' },
  { key: 'area', icon: '📍', en: 'My Area', kn: 'ನನ್ನ ಪ್ರದೇಶ' },
  { key: 'official', icon: '🏛️', en: 'Officials', kn: 'ಅಧಿಕಾರಿಗಳು' },
  { key: 'backtest', icon: '⏪', en: 'Time Machine', kn: 'ಟೈಮ್ ಮೆಷಿನ್' },
]

export default function App() {
  const [meta, setMeta] = useState(null)
  const [geo, setGeo] = useState(null)
  const [view, setView] = useState(params.get('view') || 'overview')
  const [lang, setLang] = useState(params.get('lang') === 'kn' ? 'kn' : 'en')
  const [layer, setLayer] = useState(params.get('layer') || 'risk')
  const [asOf, setAsOf] = useState(null)
  const [wards, setWards] = useState([])
  const [selected, setSelected] = useState(null)
  const [detail, setDetail] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [chatOpen, setChatOpen] = useState(false)
  const [officialTab, setOfficialTab] = useState('rank')
  const [preset, setPreset] = useState(null)
  const [chatAsk, setChatAsk] = useState(null)
  const [tourStep, setTourStep] = useState(params.has('tour') ? Number(params.get('tour')) || 0 : null)
  const [pendingWard, setPendingWard] = useState(params.get('ward'))
  const t = T[lang]

  useEffect(() => {
    api.meta().then((m) => { setMeta(m); setAsOf(params.get('as_of') || m.data_until) }).catch((e) => setError(e.message))
    api.geojson().then(setGeo).catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    if (!asOf) return
    let live = true
    setLoading(true)
    api.predict(asOf).then((r) => { if (live) { setWards(r.wards); setLoading(false) } }).catch((e) => setError(e.message))
    return () => { live = false }
  }, [asOf])

  useEffect(() => {
    if (selected == null || !asOf) return
    let live = true
    api.ward(selected, asOf).then((d) => live && setDetail(d)).catch((e) => setError(e.message))
    return () => { live = false }
  }, [selected, asOf])

  // resolve a ward name (URL or tour) once predictions are loaded
  useEffect(() => {
    if (!pendingWard || !wards.length) return
    const w = wards.find((x) => x.name.toLowerCase() === pendingWard.toLowerCase())
    if (w) setSelected(w.idx)
    setPendingWard(null)
  }, [pendingWard, wards])

  const onSelect = useCallback((i) => {
    setSelected(i)
    setView((v) => (v === 'overview' ? 'area' : v))
  }, [])
  const wardsByName = useMemo(() => Object.fromEntries(wards.map((w) => [w.name, w.idx])), [wards])

  const applyTourState = useCallback((s) => {
    if (s.view) setView(s.view)
    if (s.layer) setLayer(s.layer)
    if (s.lang) setLang(s.lang)
    if (s.chat !== undefined) setChatOpen(s.chat)
    if (s.officialTab) setOfficialTab(s.officialTab)
    setPreset(s.preset || null)
    setChatAsk(s.chatAsk || null)
    if (s.asOf) setAsOf(s.asOf === 'latest' ? meta.data_until : s.asOf)
    if (s.ward === null) { setSelected(null); setDetail(null) } else if (s.ward) setPendingWard(s.ward)
  }, [meta])

  function goTo(v) {
    setView(v)
    if (v === 'backtest' && (asOf < '2023-09-01' || asOf > '2024-04-30')) setAsOf('2023-12-01')
  }

  if (error) return <div className="fatal">⚠️ Could not reach the API: {error}<br />Start the backend: <code>cd backend &amp;&amp; uvicorn main:app --port 8000</code></div>
  if (!meta || !asOf) return <div className="fatal splash"><div className="drop">💧</div>Pravaah</div>

  const shownDetail = detail && detail.idx === selected ? detail : null

  return (
    <div className={`app lang-${lang} ${tourStep != null ? 'touring' : ''}`}>
      <header>
        <div className="brand">
          <div className="logo">💧</div>
          <div>
            <div className="name">Pravaah</div>
            <div className="tag">{t.tagline}</div>
          </div>
        </div>
        <nav className="nav">
          {NAV.map((n) => (
            <button key={n.key} className={view === n.key ? 'on' : ''} onClick={() => goTo(n.key)}>
              <span>{n.icon}</span>{n[lang]}
            </button>
          ))}
        </nav>
        <div className="head-right">
          <button className="lang-btn" onClick={() => setLang(lang === 'en' ? 'kn' : 'en')}
            aria-label={lang === 'en' ? 'Switch language to Kannada' : 'Switch language to English'}>
            <span className="globe">🌐</span>
            <span className="lang-text">
              <small>{lang === 'en' ? 'Language · ಭಾಷೆ' : 'ಭಾಷೆ · Language'}</small>
              <b>{lang === 'en' ? 'ಕನ್ನಡದಲ್ಲಿ ನೋಡಿ' : 'View in English'}</b>
            </span>
          </button>
          <button className="tour-btn" onClick={() => setTourStep(0)}>▶ {lang === 'kn' ? 'ಪ್ರವಾಸ' : 'Take the tour'}</button>
        </div>
      </header>
      <main>
        <section className="map-col">
          <MapView geo={geo} wards={wards} selected={selected} onSelect={onSelect} riskLabels={meta.risk_labels}
            lang={lang} layer={layer} setLayer={setLayer} />
          {loading && <div className="map-loading">⏳ {t.loading}</div>}
          {tourStep != null && <Tour step={tourStep} setStep={setTourStep} apply={applyTourState} />}
          <Timeline asOf={asOf} setAsOf={setAsOf} meta={meta} lang={lang} />
        </section>
        <aside className="panel">
          {view === 'overview' && <Overview wards={wards} asOf={asOf} meta={meta} lang={lang} onSelect={onSelect} goTo={goTo} />}
          {view === 'area' && <CitizenView wards={wards} detail={shownDetail} onSelect={onSelect} t={t} lang={lang} meta={meta} openChat={() => setChatOpen(true)} />}
          {view === 'official' && <OfficialView wards={wards} detail={shownDetail} onSelect={onSelect} asOf={asOf} meta={meta} t={T.en}
            tab={officialTab} setTab={setOfficialTab} preset={preset} />}
          {view === 'backtest' && <BacktestView selected={selected} onSelect={onSelect} asOf={asOf} setAsOf={setAsOf} detail={shownDetail} wardsByName={wardsByName} />}
          <div className="data-note">
            🟢 Real: rainfall (ERA5), ward boundaries · 🟠 Estimated: demand, pipe coverage · 🔵 Simulated: groundwater
          </div>
        </aside>
      </main>
      <Chat ward={shownDetail} asOf={asOf} lang={lang} t={t} open={chatOpen} setOpen={setChatOpen} autoAsk={chatAsk} clearAutoAsk={() => setChatAsk(null)} />
    </div>
  )
}
