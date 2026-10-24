// The 3 platforms (PLAN.md §6). Order = order on the landing page.
export const PLATFORMS = [
  {
    key: 'agri', path: '/agri', icon: '🌾', color: '#2f8f4e',
    en: 'Agriculture & Farmers', kn: 'ಕೃಷಿ ಮತ್ತು ರೈತರು',
    blurb: 'Crop choice from expected water, drought & crop water stress, irrigation schedules, sowing dates, yield risk, groundwater depletion.',
  },
  {
    key: 'urban', path: '/urban', icon: '🏙️', color: '#2a78d6',
    en: 'Urban Population', kn: 'ನಗರ ಜನಸಂಖ್ಯೆ',
    blurb: 'Ward and city shortage forecasts, how long supply lasts, Cauvery supply outlook, tanker needs, rainwater harvesting, leaks.',
  },
  {
    key: 'industry', path: '/industry', icon: '🏭', color: '#8a5a2b',
    en: 'Industries & Businesses', kn: 'ಕೈಗಾರಿಕೆಗಳು ಮತ್ತು ಉದ್ಯಮಗಳು',
    blurb: 'Location water risk, shortages affecting operations, demand forecasts, production disruption, wastewater reuse.',
  },
]

export const platform = (key) => PLATFORMS.find((p) => p.key === key)
