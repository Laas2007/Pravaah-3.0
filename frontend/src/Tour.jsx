import { useEffect } from 'react'

// Each step sets up the app (view, ward, date, layer, language, chat) and spotlights one element.
export const TOUR = [
  {
    title: 'Every ward gets its own forecast',
    text: 'All 243 BBMP wards of Bengaluru, coloured by how soon each will run short of water. Not one vague number for the whole city.',
    state: { view: 'overview', layer: 'risk', asOf: 'latest', ward: null, lang: 'en', chat: false },
    focus: 'map',
  },
  {
    title: 'Heatmap of water stress',
    text: 'The same forecast as a heatmap: hotspots show where the shortage is closest. Switch layers to see groundwater and borewell dependence too.',
    state: { layer: 'heat' },
    focus: 'layers',
  },
  {
    title: 'Your area, in plain words',
    text: 'A resident of Whitefield on 1 Jan 2024 would have seen: high risk, water shortage in 37–42 days, around 7–12 Feb.',
    state: { view: 'area', layer: 'risk', asOf: '2024-01-01', ward: 'Whitefield' },
    focus: 'countdown',
  },
  {
    title: 'Why? No black box',
    text: 'Each factor is switched off one at a time and the forecast re-run. Here, borewell dependence and the 2023 rain deficit cause the shortage, and IT-park demand brings it 76 days sooner.',
    state: {},
    focus: 'why',
  },
  {
    title: 'Time Machine: the 2024 crisis',
    text: 'Rewound to 1 Dec 2023 using only data that existed then, the model flagged Whitefield about 90 days before the crisis peaked. Press ▶ on the timeline to watch it spread.',
    state: { view: 'backtest', asOf: '2023-12-01', ward: 'Whitefield', layer: 'heat' },
    focus: 'story',
  },
  {
    title: 'Plan the fix',
    text: 'Officials test interventions before spending money. Extending Cauvery pipes and adding rainwater harvesting moves Whitefield from "shortage in 37–42 days" to low risk.',
    state: { view: 'official', officialTab: 'plan', asOf: '2024-01-01', ward: 'Whitefield', layer: 'risk', preset: { extra_piped: 0.3, rwh_boost: 0.5, demand_cut: 0, tanker_mld: 0 } },
    focus: 'planner',
  },
  {
    title: 'Ask in English or Kannada',
    text: 'JalaMitra answers residents in their language, using this ward\'s actual prediction: why it is happening and what to do.',
    state: { view: 'area', lang: 'kn', chat: true, ward: 'Whitefield', asOf: '2024-01-01', layer: 'risk', chatAsk: 'ಇಲ್ಲಿ ನೀರಿನ ಕೊರತೆ ಏಕೆ? ನಾನು ಏನು ಮಾಡಬಹುದು?' },
    focus: 'chat',
  },
]

export default function Tour({ step, setStep, apply }) {
  const s = TOUR[step]

  useEffect(() => { apply(s.state) }, [step]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const h = setTimeout(() => {
      document.querySelectorAll('.tour-focus').forEach((e) => e.classList.remove('tour-focus'))
      const el = document.querySelector(`[data-tour="${s.focus}"]`)
      if (el) { el.classList.add('tour-focus'); el.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }
    }, 700)
    return () => { clearTimeout(h); document.querySelectorAll('.tour-focus').forEach((e) => e.classList.remove('tour-focus')) }
  }, [step, s.focus])

  return (
    <div className="tour">
      <div className="tour-step">Feature {step + 1} of {TOUR.length}</div>
      <div className="tour-title">{s.title}</div>
      <div className="tour-text">{s.text}</div>
      <div className="tour-foot">
        <div className="tour-dots">
          {TOUR.map((_, i) => <button key={i} className={i === step ? 'on' : ''} onClick={() => setStep(i)} aria-label={`Step ${i + 1}`} />)}
        </div>
        <div className="tour-btns">
          <button className="ghost" onClick={() => setStep(null)}>Exit</button>
          {step > 0 && <button className="ghost" onClick={() => setStep(step - 1)}>Back</button>}
          {step < TOUR.length - 1
            ? <button className="primary" onClick={() => setStep(step + 1)}>Next →</button>
            : <button className="primary" onClick={() => setStep(null)}>Explore yourself ✓</button>}
        </div>
      </div>
    </div>
  )
}
