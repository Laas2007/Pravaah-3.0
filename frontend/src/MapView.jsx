import { useEffect, useMemo, useRef } from 'react'
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { RISK_COLOR, RISK_ICON, RISK_ORDER, rangeText } from './i18n'

export const LAYERS = [
  { key: 'risk', icon: '🚦', en: 'Risk zones', kn: 'ಅಪಾಯ ವಲಯ' },
  { key: 'heat', icon: '🔥', en: 'Heatmap', kn: 'ಹೀಟ್‌ಮ್ಯಾಪ್' },
  { key: 'groundwater', icon: '💧', en: 'Groundwater', kn: 'ಅಂತರ್ಜಲ' },
  { key: 'borewell', icon: '🛠️', en: 'Borewell dependence', kn: 'ಕೊಳವೆಬಾವಿ ಅವಲಂಬನೆ' },
]

export const stress = (w) => (w.days_mid === 0 ? 1 : Math.max(0, Math.min(1, 1 - w.days_mid / 365)))

// Continuous single-hue ramps, light -> dark (value 0..1).
const RAMPS = {
  heat: ['#fff5f0', '#fdd0bb', '#fc9272', '#ef5a3c', '#c81d1d', '#7a0510'],
  groundwater: ['#f3f5ff', '#c6cdf2', '#8e9ae0', '#5562c9', '#2a32ad', '#0a0f8a'],
  borewell: ['#fff7ec', '#fdd9a8', '#fbad62', '#e8792b', '#b9500f', '#73300a'],
}

function hex(h) { return [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16)) }
function interp(stops, t) {
  const x = Math.max(0, Math.min(1, t)) * (stops.length - 1)
  const i = Math.min(Math.floor(x), stops.length - 2)
  const a = hex(stops[i]), b = hex(stops[i + 1]), f = x - i
  return `rgb(${a.map((v, k) => Math.round(v + (b[k] - v) * f)).join(',')})`
}

// Value shown by each index layer, scaled 0..1 (dark = high).
const VALUE = {
  heat: (w) => stress(w),
  groundwater: (w) => w.groundwater_pct / 100,
  borewell: (w) => 1 - w.inputs.cauvery_coverage_pct / 100,
}

const INDEX_INFO = {
  heat: {
    title: { en: 'Water Scarcity Index', kn: 'ನೀರಿನ ಕೊರತೆ ಸೂಚ್ಯಂಕ' },
    axis: { en: 'Scarcity (0 = safe, 100 = shortage now)', kn: 'ಕೊರತೆ (0 = ಸುರಕ್ಷಿತ, 100 = ಈಗ ಕೊರತೆ)' },
  },
  groundwater: {
    title: { en: 'Groundwater Index (simulated)', kn: 'ಅಂತರ್ಜಲ ಸೂಚ್ಯಂಕ (ಸಿಮ್ಯುಲೇಟೆಡ್)' },
    axis: { en: 'Groundwater level, % of usable storage', kn: 'ಅಂತರ್ಜಲ ಮಟ್ಟ, %' },
  },
  borewell: {
    title: { en: 'Borewell Dependence Index (est.)', kn: 'ಕೊಳವೆಬಾವಿ ಅವಲಂಬನೆ ಸೂಚ್ಯಂಕ (ಅಂದಾಜು)' },
    axis: { en: '% of water from borewells', kn: 'ಕೊಳವೆಬಾವಿ ನೀರಿನ %' },
  },
}

function FlyTo({ feature }) {
  const map = useMap()
  useEffect(() => {
    if (!feature) return
    const coords = feature.geometry.type === 'Polygon' ? [feature.geometry.coordinates] : feature.geometry.coordinates
    let minX = 999, minY = 999, maxX = -999, maxY = -999
    coords.forEach((poly) => poly[0].forEach(([x, y]) => {
      minX = Math.min(minX, x); maxX = Math.max(maxX, x); minY = Math.min(minY, y); maxY = Math.max(maxY, y)
    }))
    map.flyToBounds([[minY, minX], [maxY, maxX]], { maxZoom: 13, duration: 0.8, padding: [120, 120] })
  }, [feature, map])
  return null
}

// Show the whole city when switching to an index layer with no ward selected.
function FitCity({ layerRef, layer, selected }) {
  const map = useMap()
  useEffect(() => {
    if (selected != null || !layerRef.current) return
    const b = layerRef.current.getBounds()
    if (b.isValid()) map.fitBounds(b, { padding: [70, 40] })
  }, [layer, selected, layerRef, map])
  return null
}

function RiskLegend({ wards, riskLabels, lang }) {
  return (
    <div className="legend">
      <div className="legend-title">{lang === 'kn' ? 'ಕೊರತೆಗೆ ದಿನಗಳು' : 'Days until shortage'}</div>
      {RISK_ORDER.map((r) => (
        <div key={r} className="legend-row">
          <span className="swatch" style={{ background: RISK_COLOR[r] }} />
          <span>{RISK_ICON[r]} {riskLabels?.[r]?.[lang] ?? r}</span>
          <span className="muted">{r === 'critical' ? '≤30' : r === 'high' ? '31–90' : r === 'medium' ? '91–180' : '180+'}</span>
          <b>{(wards || []).filter((w) => w.risk === r).length}</b>
        </div>
      ))}
    </div>
  )
}

// Vertical colour bar, dark (high) at the top.
function ColorBar({ layer, lang }) {
  const stops = RAMPS[layer]
  return (
    <div className="colorbar">
      <div className="cb-bar" style={{ background: `linear-gradient(0deg, ${stops.join(',')})` }} />
      <div className="cb-ticks">
        {[100, 75, 50, 25, 0].map((v) => <span key={v}>{v}</span>)}
      </div>
      <div className="cb-axis">{INDEX_INFO[layer].axis[lang]}</div>
    </div>
  )
}

export default function MapView({ geo, wards, selected, onSelect, riskLabels, lang, layer, setLayer }) {
  const layerRef = useRef()
  const byIdx = useMemo(() => Object.fromEntries((wards || []).map((w) => [w.idx, w])), [wards])
  const index = layer !== 'risk'

  const style = (f) => {
    const w = byIdx[f.properties.idx]
    const sel = f.properties.idx === selected
    if (index) {
      return {
        fillColor: w ? interp(RAMPS[layer], VALUE[layer](w)) : '#eee', fillOpacity: 1,
        color: sel ? '#000' : '#3b3b3b', weight: sel ? 3.5 : 0.7, opacity: 1,
      }
    }
    return { fillColor: w ? RISK_COLOR[w.risk] : '#ccc', fillOpacity: sel ? 0.75 : 0.55, color: sel ? '#0b2545' : '#ffffff', weight: sel ? 3.5 : 1, opacity: 0.9 }
  }

  useEffect(() => {
    const lyr = layerRef.current
    if (!lyr) return
    lyr.setStyle(style)
    lyr.eachLayer((l) => {
      const w = byIdx[l.feature.properties.idx]
      if (!w) return
      const r = rangeText(w)
      const label = riskLabels?.[w.risk]?.[lang] ?? w.risk
      const when = w.days_mid === 0 ? (lang === 'kn' ? 'ಈಗ ಕೊರತೆ' : 'in shortage now')
        : r ? (lang === 'kn' ? `${r} ದಿನಗಳಲ್ಲಿ ಕೊರತೆ` : `shortage in ${r} days`)
        : (lang === 'kn' ? '1 ವರ್ಷದೊಳಗೆ ಕೊರತೆ ಇಲ್ಲ' : 'no shortage within 1 yr')
      const idxLine = index ? `<div class="tt-idx">${INDEX_INFO[layer].title[lang]}: <b>${Math.round(VALUE[layer](w) * 100)}</b></div>` : ''
      l.setTooltipContent(
        `<div class="tt"><b>${w.name}</b>${idxLine}<div><span class="tt-dot" style="background:${RISK_COLOR[w.risk]}"></span>${label} · ${when}</div>` +
        `<div class="tt-sub">💧 ${w.groundwater_pct}% groundwater · 🛠️ ${Math.round(100 - w.inputs.cauvery_coverage_pct)}% borewell</div></div>`
      )
      if (l.feature.properties.idx === selected) l.bringToFront()
    })
  })

  const selFeature = useMemo(() => geo?.features.find((f) => f.properties.idx === selected), [geo, selected])

  return (
    <div className={`map-wrap ${index ? 'index-mode' : ''}`} data-tour="map">
      <MapContainer center={[12.97, 77.6]} zoom={11} minZoom={9} zoomSnap={0.25} className="map">
        {!index && (
          <TileLayer
            attribution="Tiles &copy; Esri &mdash; Esri, HERE, Garmin, USGS, &copy; OpenStreetMap contributors"
            url="https://server.arcgisonline.com/ArcGIS/rest/services/World_Street_Map/MapServer/tile/{z}/{y}/{x}"
            maxZoom={18}
          />
        )}
        {geo && (
          <GeoJSON
            ref={layerRef}
            data={geo}
            style={style}
            onEachFeature={(f, l) => {
              l.bindTooltip(f.properties.name, { sticky: true, className: 'ward-tt' })
              l.on('click', () => onSelect(f.properties.idx))
            }}
          />
        )}
        <FitCity layerRef={layerRef} layer={layer} selected={selected} />
        <FlyTo feature={selFeature} />
      </MapContainer>
      <div className="layer-switch" data-tour="layers">
        {LAYERS.map((l) => (
          <button key={l.key} className={layer === l.key ? 'on' : ''} onClick={() => setLayer(l.key)}>
            <span>{l.icon}</span>{l[lang]}
          </button>
        ))}
      </div>
      {index && <div className="map-title">{INDEX_INFO[layer].title[lang]}</div>}
      {index ? <ColorBar layer={layer} lang={lang} /> : <RiskLegend wards={wards} riskLabels={riskLabels} lang={lang} />}
    </div>
  )
}
