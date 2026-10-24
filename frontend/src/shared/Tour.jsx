import { useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useTr } from './lang'

// Guided tour across the 3 platforms: the 2023 drought -> 2024 Bengaluru crisis. Each step opens a page (path + query)
// and spotlights the element with data-tour="<focus>". The step number lives in the URL (?tour=2).
export const STEPS = [
  {
    path: '/agri', q: { as_of: '2023-08-01' }, focus: 'map',
    title: ['Every taluk, from real data', 'ಪ್ರತಿ ತಾಲೂಕು, ನೈಜ ದತ್ತಾಂಶದಿಂದ'],
    text: ['All 227 taluks coloured by how far this season\'s rain is from normal, measured by IMD rain gauges. On 1 Aug 2023 the monsoon was failing across the interior.',
      'ಎಲ್ಲಾ 227 ತಾಲೂಕುಗಳು, ಈ ಋತುವಿನ ಮಳೆ ವಾಡಿಕೆಯಿಂದ ಎಷ್ಟು ದೂರ ಎಂಬುದರ ಪ್ರಕಾರ ಬಣ್ಣ (IMD ಮಳೆ ಮಾಪಕಗಳು). 1 ಆಗಸ್ಟ್ 2023 ರಂದು ಒಳನಾಡಿನಲ್ಲಿ ಮುಂಗಾರು ವಿಫಲವಾಗುತ್ತಿತ್ತು.'],
  },
  {
    path: '/agri', q: { as_of: '2023-11-01', taluk: '210' }, focus: 'forecast',
    title: ['ML forecast, with a range and a reason', 'ವ್ಯಾಪ್ತಿ ಮತ್ತು ಕಾರಣ ಸಹಿತ ML ಮುನ್ಸೂಚನೆ'],
    text: ['Learned from 2,664 real monitoring wells, the model forecasts groundwater 6 months ahead, gives a likely range, and explains which factors push it down.',
      '2,664 ನೈಜ ಮೇಲ್ವಿಚಾರಣಾ ಬಾವಿಗಳಿಂದ ಕಲಿತ ಮಾದರಿ, 6 ತಿಂಗಳ ಮುಂಚಿತ ಅಂತರ್ಜಲ ಮುನ್ಸೂಚನೆ, ಸಂಭಾವ್ಯ ವ್ಯಾಪ್ತಿ ಮತ್ತು ಕಾರಣಗಳನ್ನು ನೀಡುತ್ತದೆ.'],
  },
  {
    path: '/agri', q: { as_of: '2023-11-01', taluk: '210' }, focus: 'timemachine',
    title: ['Time Machine: tested on history', 'ಟೈಮ್ ಮೆಷಿನ್: ಇತಿಹಾಸದ ಮೇಲೆ ಪರೀಕ್ಷೆ'],
    text: ['Pick any past date and the forecast is compared with what the wells actually showed afterwards. From 2022 on, the forecast comes from a model that never saw those years.',
      'ಯಾವುದೇ ಹಿಂದಿನ ದಿನಾಂಕ ಆಯ್ಕೆಮಾಡಿ: ಮುನ್ಸೂಚನೆಯನ್ನು ನಂತರ ಬಾವಿಗಳು ನಿಜವಾಗಿ ತೋರಿಸಿದುದರೊಂದಿಗೆ ಹೋಲಿಸಲಾಗುತ್ತದೆ. 2022 ರಿಂದ, ಆ ವರ್ಷಗಳನ್ನು ನೋಡದ ಮಾದರಿಯ ಮುನ್ಸೂಚನೆ.'],
  },
  {
    path: '/urban', q: { as_of: '2024-03-01', zoom: 'blr' }, focus: 'map',
    title: ['Bengaluru, ward by ward', 'ಬೆಂಗಳೂರು, ವಾರ್ಡ್‌ವಾರು'],
    text: ['All 243 wards get their own forecast. On 1 Mar 2024 the outer ring (Whitefield, Mahadevapura, RR Nagar, Bommanahalli) is critical while the Cauvery-piped core stays safe.',
      'ಎಲ್ಲಾ 243 ವಾರ್ಡ್‌ಗಳಿಗೆ ಪ್ರತ್ಯೇಕ ಮುನ್ಸೂಚನೆ. 1 ಮಾರ್ಚ್ 2024 ರಂದು ಹೊರವಲಯ (ವೈಟ್‌ಫೀಲ್ಡ್, ಮಹದೇವಪುರ, ಆರ್‌ಆರ್ ನಗರ, ಬೊಮ್ಮನಹಳ್ಳಿ) ಗಂಭೀರ; ಕಾವೇರಿ ಕೊಳವೆ ನೀರಿನ ಕೇಂದ್ರ ಸುರಕ್ಷಿತ.'],
  },
  {
    path: '/urban', q: { as_of: '2023-10-01' }, focus: 'cauvery',
    title: ['Cauvery supply outlook', 'ಕಾವೇರಿ ಪೂರೈಕೆ ಮುನ್ನೋಟ'],
    text: ['On 1 Oct 2023 the four dams that feed Bengaluru held 39% less water than normal for that day: five months before the crisis peaked.',
      '1 ಅಕ್ಟೋಬರ್ 2023 ರಂದು ಬೆಂಗಳೂರಿಗೆ ನೀರುಣಿಸುವ ನಾಲ್ಕು ಜಲಾಶಯಗಳಲ್ಲಿ ವಾಡಿಕೆಗಿಂತ 39% ಕಡಿಮೆ ನೀರು: ಬಿಕ್ಕಟ್ಟಿಗೆ ಐದು ತಿಂಗಳ ಮುಂಚೆ.'],
  },
  {
    path: '/industry', q: { as_of: '2024-03-01', zoom: 'blr' }, focus: 'map',
    title: ['Water risk for any business location', 'ಯಾವುದೇ ಉದ್ಯಮ ಸ್ಥಳಕ್ಕೆ ನೀರಿನ ಅಪಾಯ'],
    text: ['Click a taluk anywhere in Karnataka, or a single Bengaluru ward, for a water-risk report before choosing or expanding a site.',
      'ಸ್ಥಳ ಆಯ್ಕೆ ಅಥವಾ ವಿಸ್ತರಣೆಗೆ ಮುನ್ನ ಕರ್ನಾಟಕದ ಯಾವುದೇ ತಾಲೂಕು ಅಥವಾ ಬೆಂಗಳೂರಿನ ಒಂದು ವಾರ್ಡ್ ಕ್ಲಿಕ್ ಮಾಡಿ ನೀರಿನ ಅಪಾಯ ವರದಿ ಪಡೆಯಿರಿ.'],
  },
  {
    path: '/agri', q: { as_of: '2023-11-01', taluk: '210' }, lang: 'kn', focus: 'chat',
    title: ['Ask JalaMitra, in Kannada or English', 'ಜಲಮಿತ್ರನನ್ನು ಕನ್ನಡ ಅಥವಾ ಇಂಗ್ಲಿಷ್‌ನಲ್ಲಿ ಕೇಳಿ'],
    text: ['Everything switches to Kannada with one button, and the assistant answers questions about the selected taluk or ward using its actual forecast.',
      'ಒಂದೇ ಬಟನ್‌ನಿಂದ ಎಲ್ಲವೂ ಕನ್ನಡಕ್ಕೆ; ಆಯ್ಕೆಮಾಡಿದ ತಾಲೂಕು ಅಥವಾ ವಾರ್ಡ್‌ನ ನೈಜ ಮುನ್ಸೂಚನೆ ಬಳಸಿ ಸಹಾಯಕ ಉತ್ತರಿಸುತ್ತಾನೆ.'],
  },
]

export function useTourStep() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const raw = params.get('tour')
  const step = raw == null || raw === '' || Number.isNaN(Number(raw)) ? null : Math.min(Number(raw), STEPS.length - 1)
  const setStep = (n) => {
    if (n == null) {
      const p = new URLSearchParams(params)
      p.delete('tour')
      navigate({ search: p.toString() }, { replace: true })
      return
    }
    const s = STEPS[n]
    const p = new URLSearchParams({ ...s.q, tour: String(n) })
    const lang = s.lang || params.get('lang')
    if (lang === 'kn') p.set('lang', 'kn')
    navigate(`${s.path}?${p}`)
  }
  return [step, setStep]
}

export default function Tour({ step, setStep }) {
  const tr = useTr()
  const s = STEPS[step]

  useEffect(() => {
    const h = setTimeout(() => {
      document.querySelectorAll('.tour-focus').forEach((e) => e.classList.remove('tour-focus'))
      const el = document.querySelector(`[data-tour="${s.focus}"]`)
      if (el) { el.classList.add('tour-focus'); el.scrollIntoView({ block: 'nearest', behavior: 'smooth' }) }
    }, 900)
    return () => { clearTimeout(h); document.querySelectorAll('.tour-focus').forEach((e) => e.classList.remove('tour-focus')) }
  }, [step, s.focus])

  return (
    <div className="ps-tour">
      <div className="tour-step">{tr(`Step ${step + 1} of ${STEPS.length}`, `ಹಂತ ${step + 1} / ${STEPS.length}`)}</div>
      <div className="tour-title">{tr(...s.title)}</div>
      <div className="tour-text">{tr(...s.text)}</div>
      <div className="tour-foot">
        <div className="tour-dots">
          {STEPS.map((_, i) => <button key={i} className={i === step ? 'on' : ''} onClick={() => setStep(i)} aria-label={`Step ${i + 1}`} />)}
        </div>
        <div className="tour-btns">
          <button className="ghost" onClick={() => setStep(null)}>{tr('Exit', 'ನಿರ್ಗಮಿಸಿ')}</button>
          {step > 0 && <button className="ghost" onClick={() => setStep(step - 1)}>{tr('Back', 'ಹಿಂದೆ')}</button>}
          {step < STEPS.length - 1
            ? <button className="primary" onClick={() => setStep(step + 1)}>{tr('Next', 'ಮುಂದೆ')}</button>
            : <button className="primary" onClick={() => setStep(null)}>{tr('Finish tour', 'ಪ್ರವಾಸ ಮುಗಿಸಿ')}</button>}
        </div>
      </div>
    </div>
  )
}
