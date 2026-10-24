import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { getTaluks, useLoad } from './hooks'

const KA_BOUNDS = [[11.55, 74.0], [18.5, 78.6]]
const BLR_BOUNDS = [[12.83, 77.42], [13.14, 77.78]]

/**
 * Taluk choropleth for any platform.
 *   colorOf(idx)  -> fill colour for a taluk (or null for grey)
 *   labelOf(idx)  -> extra tooltip text
 *   points        -> optional markers [{lat, lon, color, label, key, onClick}]
 *   overlay       -> optional finer polygons drawn on top (Bengaluru wards):
 *                    {geo, colorOf(idx), labelOf(idx), selected, onSelect}; adds Karnataka / Bengaluru zoom buttons
 */
export default function KarnatakaMap({ colorOf, labelOf, selected, onSelect, points = [], legend, height, overlay, indexMode, ui }) {
  const geo = useLoad(getTaluks, []).data
  const layer = useRef(null)
  const wardLayer = useRef(null)

  const style = (f) => {
    const i = f.properties.idx
    const sel = i === selected
    if (indexMode) {   // continuous index layer: solid fills and thin dark borders, like the Bengaluru heatmap
      return { fillColor: colorOf?.(i) || '#e3e7ed', fillOpacity: 1, color: sel ? '#000' : '#3b3b3b', weight: sel ? 3 : 0.5 }
    }
    return {
      fillColor: colorOf?.(i) || '#d5dbe3', fillOpacity: sel ? 0.95 : 0.78,
      color: sel ? '#0b1b2e' : '#ffffff', weight: sel ? 2.5 : 0.6,
    }
  }
  const wardStyle = (f) => {
    const i = f.properties.idx
    const sel = i === overlay?.selected
    return {
      fillColor: overlay?.colorOf?.(i) || '#d5dbe3', fillOpacity: sel ? 1 : 0.9,
      color: sel ? '#0b1b2e' : '#ffffff', weight: sel ? 2 : 0.3,
    }
  }

  // react-leaflet doesn't re-style GeoJSON on prop changes, so do it by hand
  useEffect(() => { layer.current?.setStyle(style) })
  useEffect(() => { wardLayer.current?.setStyle(wardStyle) })

  return (
    <div className={`ps-map ${indexMode ? 'index-mode' : ''}`} style={height ? { height } : undefined}>
      <MapContainer bounds={startOnBengaluru() ? BLR_BOUNDS : KA_BOUNDS} zoomSnap={0.25} className="ps-map-inner" scrollWheelZoom>
        <TileLayer url="https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Light_Gray_Base/MapServer/tile/{z}/{y}/{x}"
          attribution="Tiles &copy; Esri" maxZoom={16} />
        {geo && (
          <GeoJSON ref={layer} data={geo} style={style}
            onEachFeature={(f, l) => {
              const p = f.properties
              l.on('click', () => onSelect?.(p.idx))
              l.bindTooltip(() => `<b>${p.name}</b> · ${p.district}${labelOf ? '<br/>' + (labelOf(p.idx) ?? '') : ''}`, { sticky: true })
            }} />
        )}
        {overlay?.geo && (
          <GeoJSON ref={wardLayer} data={overlay.geo} style={wardStyle}
            onEachFeature={(f, l) => {
              const p = f.properties
              l.on('click', (e) => { e.originalEvent?.stopPropagation?.(); overlay.onSelect?.(p.idx) })
              l.bindTooltip(() => `<b>${p.name}</b> (ward ${p.ward_no})${overlay.labelOf ? '<br/>' + (overlay.labelOf(p.idx) ?? '') : ''}`, { sticky: true })
            }} />
        )}
        {points.map((pt) => (
          <CircleMarker key={pt.key} center={[pt.lat, pt.lon]} radius={pt.radius || 8}
            pathOptions={{ color: '#fff', weight: 2, fillColor: pt.color || '#0b2545', fillOpacity: 0.95 }}
            eventHandlers={{ click: () => pt.onClick?.() }}>
            <Tooltip>{pt.label}</Tooltip>
          </CircleMarker>
        ))}
        {overlay && <ZoomButtons below={!!ui} />}
      </MapContainer>
      {legend && <div className="ps-legend">{legend}</div>}
      {ui}
    </div>
  )
}

// ?zoom=blr in the URL opens the map on the Bengaluru wards (handy for demo links)
const startOnBengaluru = () => new URLSearchParams(window.location.search).get('zoom') === 'blr'

function ZoomButtons({ below }) {
  const map = useMap()
  return (
    <div className={`ps-zoom ${below ? 'below' : ''}`}>
      <button onClick={() => map.fitBounds(KA_BOUNDS)}>Karnataka</button>
      <button onClick={() => map.fitBounds(BLR_BOUNDS)}>🔎 Bengaluru wards</button>
    </div>
  )
}
