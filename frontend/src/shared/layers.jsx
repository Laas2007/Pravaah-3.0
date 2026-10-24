// Map layers for the taluk platforms, styled like the Bengaluru ward app (risk zones + continuous index layers).
import { useSearchParams } from 'react-router-dom'
import { RISK_COLOR, RISK_ORDER } from '../i18n'
import { RISK_TEXT, useTr } from './lang'

const clip = (x) => Math.max(0, Math.min(1, x))
const RAMP = {
  heat: ['#fff5f0', '#fdd0bb', '#fc9272', '#ef5a3c', '#c81d1d', '#7a0510'],
  water: ['#f3f5ff', '#c6cdf2', '#8e9ae0', '#5562c9', '#2a32ad', '#0a0f8a'],
  diverging: ['#8c510a', '#d8b365', '#f6e8c3', '#c7eae5', '#5ab4ac', '#01665e'],
  industry: ['#fff7ec', '#fdd9a8', '#fbad62', '#e8792b', '#b9500f', '#73300a'],
}

function hex(h) { return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)) }
export function interp(stops, t) {
  const x = clip(t) * (stops.length - 1)
  const i = Math.min(Math.floor(x), stops.length - 2)
  const a = hex(stops[i]), b = hex(stops[i + 1]), f = x - i
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(',')})`
}

const pctTxt = (v) => (v == null ? '–' : `${v > 0 ? '+' : ''}${Math.round(v)}%`)
const mTxt = (v) => (v == null ? '–' : `${v > 0 ? '+' : ''}${v.toFixed(1)} m`)

// value(row) -> 0..1 (dark = high), fmt(row) -> tooltip value, ticks: colour-bar labels top -> bottom
export const LAYER_DEFS = {
  risk: { icon: '🚦', name: ['Risk zones', 'ಅಪಾಯ ವಲಯ'] },
  heat: {
    icon: '🔥', name: ['Heatmap', 'ಹೀಟ್‌ಮ್ಯಾಪ್'], ramp: RAMP.heat,
    title: ['Water Scarcity Index', 'ನೀರಿನ ಕೊರತೆ ಸೂಚ್ಯಂಕ'], axis: ['Scarcity (0 = safe, 100 = at stress now)', 'ಕೊರತೆ (0 = ಸುರಕ್ಷಿತ, 100 = ಈಗ ಒತ್ತಡ)'],
    ticks: ['100', '75', '50', '25', '0'], value: (r) => r.stress, fmt: (r) => (r.stress == null ? '–' : Math.round(r.stress * 100)),
  },
  groundwater: {
    icon: '💧', name: ['Groundwater', 'ಅಂತರ್ಜಲ'], ramp: RAMP.water,
    title: ['Groundwater vs normal (wells)', 'ಅಂತರ್ಜಲ vs ವಾಡಿಕೆ (ಬಾವಿಗಳು)'], axis: ['Water table vs normal (dark = more water)', 'ನೀರಿನ ಮಟ್ಟ vs ವಾಡಿಕೆ (ಗಾಢ = ಹೆಚ್ಚು ನೀರು)'],
    ticks: ['6 m higher', '3 m', 'normal', '3 m', '6 m lower'],
    value: (r) => (r.gw_anom_m == null ? null : clip((6 - r.gw_anom_m) / 12)), fmt: (r) => mTxt(r.gw_anom_m),
  },
  rain12: {
    icon: '🌧️', name: ['Rain 12 months', '12 ತಿಂ. ಮಳೆ'], ramp: RAMP.diverging,
    title: ['Rain, last 12 months vs normal (IMD)', 'ಕಳೆದ 12 ತಿಂಗಳ ಮಳೆ vs ವಾಡಿಕೆ (IMD)'], axis: ['% vs normal', 'ವಾಡಿಕೆಗಿಂತ %'],
    ticks: ['+60%', '+30%', 'normal', '−30%', '−60%'],
    value: (r) => (r.rain_365d_dev_pct == null ? null : clip((r.rain_365d_dev_pct + 60) / 120)), fmt: (r) => pctTxt(r.rain_365d_dev_pct),
  },
  rain3: {
    icon: '🌦️', name: ['Rain 3 months', '3 ತಿಂ. ಮಳೆ'], ramp: RAMP.diverging,
    title: ['Rain, last 3 months vs normal (IMD)', 'ಕಳೆದ 3 ತಿಂಗಳ ಮಳೆ vs ವಾಡಿಕೆ (IMD)'], axis: ['% vs normal', 'ವಾಡಿಕೆಗಿಂತ %'],
    ticks: ['+60%', '+30%', 'normal', '−30%', '−60%'],
    value: (r) => (r.rain_90d_dev_pct == null ? null : clip((r.rain_90d_dev_pct + 60) / 120)), fmt: (r) => pctTxt(r.rain_90d_dev_pct),
  },
  waterbal: {
    icon: '⚖️', name: ['Season water balance', 'ಋತುವಿನ ನೀರಿನ ಸಮತೋಲನ'], ramp: RAMP.diverging,
    title: ['Season water balance: rain − crop water demand (ET0)', 'ಋತುವಿನ ನೀರಿನ ಸಮತೋಲನ: ಮಳೆ − ಬೆಳೆ ನೀರಿನ ಬೇಡಿಕೆ'], axis: ['mm since season start', 'ಋತು ಆರಂಭದಿಂದ ಮಿ.ಮೀ.'],
    ticks: ['+400', '+200', '0', '−200', '−400'],
    value: (r) => (r.season_wb_mm == null ? null : clip((r.season_wb_mm + 400) / 800)), fmt: (r) => (r.season_wb_mm == null ? '–' : `${Math.round(r.season_wb_mm)} mm`),
  },
  drought: {
    icon: '🌵', name: ['Kharif drought (M1)', 'ಮುಂಗಾರು ಬರ (M1)'],
    title: ['Kharif drought early warning (M1)', 'ಮುಂಗಾರು ಬರ ಮುನ್ನೆಚ್ಚರಿಕೆ (M1)'],
    cat: (r) => r.drought_level || 'off',
    colors: { likely: '#d03b3b', watch: '#fab219', low: '#0ca30c', off: '#d5dbe3' },
    entries: [['likely', ['Drought likely', 'ಬರ ಸಾಧ್ಯತೆ ಹೆಚ್ಚು'], ['trigger met, model ≥ 50%', 'ಮಾನದಂಡ + ಮಾದರಿ ≥ 50%']],
      ['watch', ['Drought watch', 'ಬರ ಎಚ್ಚರಿಕೆ'], ['trigger met', 'ಮಾನದಂಡ ಪೂರೈಸಿದೆ']],
      ['low', ['No alert', 'ಎಚ್ಚರಿಕೆ ಇಲ್ಲ'], ['trigger not met', 'ಮಾನದಂಡ ಇಲ್ಲ']]],
    off: ['Runs 1 Jul – 30 Sep (pick a kharif date)', '1 ಜುಲೈ – 30 ಸೆಪ್ಟೆಂಬರ್ ಮಾತ್ರ'],
    fmt: (r) => (r.drought_p == null ? '–' : `${Math.round(r.drought_p * 100)}%`),
  },
  m7: {
    icon: '🏭', name: ['Industrial risk', 'ಕೈಗಾರಿಕಾ ಅಪಾಯ'], ramp: RAMP.industry,
    title: ['Industrial output at risk, next 6 months (M7)', 'ಮುಂದಿನ 6 ತಿಂಗಳ ಕೈಗಾರಿಕಾ ಉತ್ಪಾದನೆ ಅಪಾಯ (M7)'], axis: ['% of output at risk (district)', 'ಅಪಾಯದ ಉತ್ಪಾದನೆ % (ಜಿಲ್ಲೆ)'],
    ticks: ['100%', '75%', '50%', '25%', '0%'],
    value: (r) => (r.m7 == null ? null : clip(r.m7 / 100)), fmt: (r) => (r.m7 == null ? '–' : `${r.m7}%`),
  },
}

export function useLayer(available, fallback) {
  const [params, setParams] = useSearchParams()
  const want = params.get('layer')
  const layer = available.includes(want) ? want : fallback
  const setLayer = (l) => setParams((p) => { p.set('layer', l); return p }, { replace: true })
  return [layer, setLayer]
}

const TIER_TXT = {
  critical: ['at stress now / likely ≤ 90 days', 'ಈಗ ಒತ್ತಡ / ≤ 90 ದಿನ'],
  high: ['likely ≤ 6 months', '≤ 6 ತಿಂಗಳು ಸಾಧ್ಯತೆ'],
  medium: ['watch: dry year ≤ 6 months', 'ಎಚ್ಚರಿಕೆ: ಒಣ ವರ್ಷ ≤ 6 ತಿಂ.'],
  low: ['not within 6 months', '6 ತಿಂಗಳೊಳಗೆ ಇಲ್ಲ'],
}

/** Build map props (colours, tooltips, legend, switcher) for the chosen layer. rows: per-taluk objects indexed by idx. */
export function useLayerMap({ layers, fallback, rows, wards }) {
  const tr = useTr()
  const [layer, setLayer] = useLayer(layers, fallback)
  const def = LAYER_DEFS[layer]
  const byIdx = rows || []
  const cat = !!def.cat                       // categorical layer (e.g. drought alerts)
  const index = layer !== 'risk' && !cat
  const colorOf = (i) => {
    const r = byIdx[i]
    if (!r) return null
    if (cat) return def.colors[def.cat(r)]
    if (!index) return RISK_COLOR[r.risk]
    const v = def.value(r)
    return v == null ? '#e3e7ed' : interp(def.ramp, v)
  }
  const when = (r) => {
    if (r.days_mid == null) return tr('provisional index (no recent wells)', 'ತಾತ್ಕಾಲಿಕ ಸೂಚ್ಯಂಕ')
    if (r.days_mid === 0) return tr('at stress now', 'ಈಗ ಒತ್ತಡ')
    if (r.days_mid <= 183) return tr(`stress likely in ~${Math.round(r.days_mid)} days`, `~${Math.round(r.days_mid)} ದಿನಗಳಲ್ಲಿ ಒತ್ತಡ ಸಾಧ್ಯತೆ`)
    if (r.days_low != null && r.days_low <= 183) return tr(`stress in ~${Math.round(r.days_low)} days if dry`, `ಒಣಗಿದರೆ ~${Math.round(r.days_low)} ದಿನಗಳಲ್ಲಿ ಒತ್ತಡ`)
    return tr('no stress within 6 months', '6 ತಿಂಗಳೊಳಗೆ ಒತ್ತಡ ಇಲ್ಲ')
  }
  const labelOf = (i) => {
    const r = byIdx[i]
    if (!r) return ''
    const idxLine = index || cat ? `<div class="tt-idx">${tr(...def.title)}: <b>${def.fmt(r)}</b></div>` : ''
    return `${idxLine}<span class="tt-dot" style="background:${RISK_COLOR[r.risk]}"></span>${tr(RISK_TEXT[r.risk].en, RISK_TEXT[r.risk].kn)} · ${when(r)}`
  }
  // Bengaluru wards follow the layer where the ward model has a matching quantity
  const wardColor = (w) => {
    if (layer === 'heat') return interp(RAMP.heat, w.days_mid === 0 ? 1 : clip(1 - w.days_mid / 365))
    if (layer === 'groundwater') return interp(RAMP.water, w.groundwater_pct / 100)
    return RISK_COLOR[w.risk]
  }
  const counts = Object.fromEntries(RISK_ORDER.map((k) => [k, byIdx.filter((r) => r && r.risk === k).length]))
  const offSeason = cat && byIdx.every((r) => !r || def.cat(r) === 'off')
  const legend = cat ? (
    <div className="legend">
      <div className="legend-title">{tr(...def.title)}</div>
      {offSeason ? <div className="muted">{tr(...def.off)}</div> : def.entries.map(([k, name, rule]) => (
        <div key={k} className="legend-row">
          <span className="swatch" style={{ background: def.colors[k] }} />
          <span>{tr(...name)}</span>
          <span className="muted">{tr(...rule)}</span>
          <b>{byIdx.filter((r) => r && def.cat(r) === k).length}</b>
        </div>
      ))}
    </div>
  ) : index ? (
    <div className="colorbar">
      <div className="cb-bar" style={{ background: `linear-gradient(0deg, ${def.ramp.join(',')})` }} />
      <div className="cb-ticks">{def.ticks.map((t) => <span key={t}>{t}</span>)}</div>
      <div className="cb-axis">{tr(...def.axis)}</div>
    </div>
  ) : (
    <div className="legend">
      <div className="legend-title">{tr('Groundwater stress (taluks)', 'ಅಂತರ್ಜಲ ಒತ್ತಡ (ತಾಲೂಕುಗಳು)')}</div>
      {RISK_ORDER.map((k) => (
        <div key={k} className="legend-row">
          <span className="swatch" style={{ background: RISK_COLOR[k] }} />
          <span>{tr(RISK_TEXT[k].en, RISK_TEXT[k].kn)}</span>
          <span className="muted">{tr(...TIER_TXT[k])}</span>
          <b>{counts[k]}</b>
        </div>
      ))}
    </div>
  )
  const switcher = (
    <div className="layer-switch" data-tour="layers">
      {layers.map((k) => (
        <button key={k} className={layer === k ? 'on' : ''} onClick={() => setLayer(k)}>
          <span>{LAYER_DEFS[k].icon}</span>{tr(...LAYER_DEFS[k].name)}
        </button>
      ))}
    </div>
  )
  const title = index || cat ? <div className="map-title">{tr(...def.title)}</div> : null
  return { layer, index, colorOf, labelOf, legend, switcher, title, wardColor, counts }
}
