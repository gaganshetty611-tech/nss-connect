import 'leaflet/dist/leaflet.css'
import { CircleMarker, MapContainer, Popup, TileLayer, useMap, useMapEvents } from 'react-leaflet'
import { useEffect } from 'react'
import { Link } from 'react-router-dom'

const DEFAULT_CENTER = [19.076, 72.8777] // Mumbai
const COLORS = { event: '#7c3aed', ngo: '#16a34a', unit: '#2563eb', pick: '#dc2626' }

function FitBounds({ points }) {
  const map = useMap()
  useEffect(() => {
    if (points.length > 1) map.fitBounds(points, { padding: [30, 30], maxZoom: 14 })
    else if (points.length === 1) map.setView(points[0], 13)
  }, [map, JSON.stringify(points)]) // eslint-disable-line react-hooks/exhaustive-deps
  return null
}

function ClickPicker({ onPick }) {
  useMapEvents({ click: (e) => onPick(Number(e.latlng.lat.toFixed(6)), Number(e.latlng.lng.toFixed(6))) })
  return null
}

/**
 * markers: [{ id, lat, lng, type: 'event'|'ngo'|'unit', title, subtitle, link }]
 * onPick(lat, lng): enables click-to-set-location (used by the Host Drive form)
 * Uses OpenStreetMap tiles – no API key required.
 */
export default function MapView({ markers = [], height = 380, onPick, picked }) {
  const valid = markers.filter((m) => m.lat != null && m.lng != null).map((m) => ({ ...m, lat: Number(m.lat), lng: Number(m.lng) }))
  const pts = valid.map((m) => [m.lat, m.lng])
  if (picked?.lat != null && picked?.lng != null) pts.push([Number(picked.lat), Number(picked.lng)])
  return (
    <div style={{ height }} className="overflow-hidden rounded-2xl ring-1 ring-slate-200">
      <MapContainer center={pts[0] || DEFAULT_CENTER} zoom={12} style={{ height: '100%', width: '100%' }} scrollWheelZoom={false}>
        <TileLayer attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors' url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png" />
        <FitBounds points={pts} />
        {onPick && <ClickPicker onPick={onPick} />}
        {valid.map((m) => (
          <CircleMarker key={`${m.type}-${m.id}`} center={[m.lat, m.lng]} radius={9} pathOptions={{ color: '#fff', weight: 2, fillColor: COLORS[m.type] || COLORS.event, fillOpacity: 0.95 }}>
            <Popup>
              <div className="text-sm">
                <p className="font-semibold">{m.title}</p>
                {m.subtitle && <p className="text-xs text-slate-500">{m.subtitle}</p>}
                {m.link && <Link to={m.link} className="text-xs text-brand-700">Open →</Link>}
              </div>
            </Popup>
          </CircleMarker>
        ))}
        {picked?.lat != null && picked?.lng != null && (
          <CircleMarker center={[Number(picked.lat), Number(picked.lng)]} radius={10} pathOptions={{ color: '#fff', weight: 2, fillColor: COLORS.pick, fillOpacity: 1 }} />
        )}
      </MapContainer>
    </div>
  )
}

export function MapLegend() {
  return (
    <div className="flex flex-wrap gap-3 text-xs text-slate-600">
      {[['event', 'Drives'], ['ngo', 'Verified NGOs'], ['unit', 'NSS units']].map(([k, label]) => (
        <span key={k} className="flex items-center gap-1.5">
          <span className="h-3 w-3 rounded-full" style={{ backgroundColor: COLORS[k] }} /> {label}
        </span>
      ))}
    </div>
  )
}
