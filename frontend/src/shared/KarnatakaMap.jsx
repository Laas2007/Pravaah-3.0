import { useEffect, useRef } from 'react'
import { MapContainer, TileLayer, GeoJSON, CircleMarker, Tooltip } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'
import { getTaluks, useLoad } from './hooks'

const KA_BOUNDS = [[11.55, 74.0], [18.5, 78.6]]

/**
 * Taluk choropleth for any platform.
 *   colorOf(idx)  -> fill colour for a taluk (or null for grey)
 *   labelOf(idx)  -> extra tooltip text
 *   points        -> optional markers [{lat, lon, color, label, key, onClick}]
 */
export default function KarnatakaMap({ colorOf, labelOf, selected, onSelect, points = [], legend, height }) {
  const geo = useLoad(getTaluks, []).data
  const layer = useRef(null)

  const style = (f) => {
    const i = f.properties.idx
    const sel = i === selected
    return {
      fillColor: colorOf?.(i) || '#d5dbe3', fillOpacity: sel ? 0.95 : 0.78,
      color: sel ? '#0b1b2e' : '#ffffff', weight: sel ? 2.5 : 0.6,
    }
  }

  // react-leaflet doesn't re-style GeoJSON on prop changes, so do it by hand
  useEffect(() => { layer.current?.setStyle(style) })

  return (
    <div className="ps-map" style={height ? { height } : undefined}>
      <MapContainer bounds={KA_BOUNDS} zoomSnap={0.25} className="ps-map-inner" scrollWheelZoom>
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
        {points.map((pt) => (
          <CircleMarker key={pt.key} center={[pt.lat, pt.lon]} radius={pt.radius || 8}
            pathOptions={{ color: '#fff', weight: 2, fillColor: pt.color || '#0b2545', fillOpacity: 0.95 }}
            eventHandlers={{ click: () => pt.onClick?.() }}>
            <Tooltip>{pt.label}</Tooltip>
          </CircleMarker>
        ))}
      </MapContainer>
      {legend && <div className="ps-legend">{legend}</div>}
    </div>
  )
}
