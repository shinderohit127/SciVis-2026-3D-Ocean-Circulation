import React, { useEffect, useRef, useCallback } from 'react'
import maplibregl from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useStore } from '../state/store'
import { useOverview } from '../api/overview'

// Map σ₀ values to a viridis-like RGBA array on a canvas element.
function renderSliceToCanvas(slice: number[][]): string {
  const ny = slice.length
  const nx = slice[0]?.length ?? 0
  if (!ny || !nx) return ''

  let min = Infinity, max = -Infinity
  for (const row of slice) for (const v of row) {
    if (isFinite(v)) { if (v < min) min = v; if (v > max) max = v }
  }
  const range = max - min || 1

  const canvas = document.createElement('canvas')
  canvas.width = nx
  canvas.height = ny
  const ctx = canvas.getContext('2d')!
  const img = ctx.createImageData(nx, ny)

  for (let y = 0; y < ny; y++) {
    for (let x = 0; x < nx; x++) {
      const t = (slice[y][x] - min) / range
      // viridis approximation: blue → teal → green → yellow
      const r = Math.round(255 * Math.max(0, Math.min(1, 1.8 * t - 0.8)))
      const g = Math.round(255 * Math.max(0, Math.min(1, t < 0.5 ? 2.2 * t : 2.2 - 2.2 * t)))
      const b = Math.round(255 * Math.max(0, Math.min(1, 0.9 - 1.4 * t)))
      const i = (y * nx + x) * 4
      img.data[i] = r; img.data[i + 1] = g; img.data[i + 2] = b; img.data[i + 3] = 180
    }
  }
  ctx.putImageData(img, 0, 0)
  return canvas.toDataURL()
}

export default function OverviewMap() {
  const mapRef = useRef<maplibregl.Map | null>(null)
  const containerRef = useRef<HTMLDivElement>(null)
  const { roi, setROI } = useStore()

  // Draw / update the ROI polygon on the map
  const syncROI = useCallback((map: maplibregl.Map) => {
    const geojson: GeoJSON.Feature<GeoJSON.Polygon> = {
      type: 'Feature',
      geometry: {
        type: 'Polygon',
        coordinates: [[
          [roi.lon_min, roi.lat_min],
          [roi.lon_max, roi.lat_min],
          [roi.lon_max, roi.lat_max],
          [roi.lon_min, roi.lat_max],
          [roi.lon_min, roi.lat_min],
        ]],
      },
      properties: {},
    }
    const src = map.getSource('roi') as maplibregl.GeoJSONSource | undefined
    if (src) src.setData(geojson)
  }, [roi])

  // Fetch overview for surface σ₀ heatmap overlay
  const { data: overview } = useOverview('global', 'sigma0')

  useEffect(() => {
    if (!containerRef.current) return

    const map = new maplibregl.Map({
      container: containerRef.current,
      // CartoDB dark-matter — free, no API key
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: [(roi.lon_min + roi.lon_max) / 2, (roi.lat_min + roi.lat_max) / 2],
      zoom: 3,
      attributionControl: false,
    })

    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')

    map.on('load', () => {
      // ROI rectangle
      map.addSource('roi', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      map.addLayer({
        id: 'roi-fill',
        type: 'fill',
        source: 'roi',
        paint: { 'fill-color': '#20a8f0', 'fill-opacity': 0.12 },
      })
      map.addLayer({
        id: 'roi-line',
        type: 'line',
        source: 'roi',
        paint: { 'line-color': '#20a8f0', 'line-width': 1.5 },
      })
      syncROI(map)
    })

    // Click to recenter ROI on click position
    map.on('click', (e) => {
      const { lng, lat } = e.lngLat
      const halfLon = (roi.lon_max - roi.lon_min) / 2
      const halfLat = (roi.lat_max - roi.lat_min) / 2
      setROI({
        lon_min: +(lng - halfLon).toFixed(1),
        lon_max: +(lng + halfLon).toFixed(1),
        lat_min: +(lat - halfLat).toFixed(1),
        lat_max: +(lat + halfLat).toFixed(1),
      })
    })

    mapRef.current = map
    return () => { map.remove(); mapRef.current = null }
  }, [])

  // Sync ROI rectangle when store changes
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    syncROI(map)
  }, [roi.lat_min, roi.lat_max, roi.lon_min, roi.lon_max])

  // Add σ₀ heatmap overlay when overview data arrives
  useEffect(() => {
    const map = mapRef.current
    if (!map || !overview) return
    const surface = overview.depth_bands.find(b => b.band === 'surface')
    if (!surface?.surface_slice) return

    const dataUrl = renderSliceToCanvas(surface.surface_slice)
    if (!dataUrl) return

    const onLoad = () => {
      if (map.getLayer('sigma0-raster')) map.removeLayer('sigma0-raster')
      if (map.getSource('sigma0-img')) map.removeSource('sigma0-img')

      map.addSource('sigma0-img', {
        type: 'image',
        url: dataUrl,
        coordinates: [[-180, 90], [180, 90], [180, -90], [-180, -90]],
      })
      map.addLayer(
        { id: 'sigma0-raster', type: 'raster', source: 'sigma0-img', paint: { 'raster-opacity': 0.5 } },
        'roi-fill',
      )
    }

    if (map.isStyleLoaded()) onLoad()
    else map.once('load', onLoad)
  }, [overview])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />
      <div style={{
        position: 'absolute', top: 8, left: 8, background: 'rgba(6,15,26,0.75)',
        color: '#6aaad4', fontSize: 10, padding: '3px 6px', borderRadius: 3, pointerEvents: 'none',
      }}>
        Click map to re-center ROI
      </div>
    </div>
  )
}
