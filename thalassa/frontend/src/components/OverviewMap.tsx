import React, { useEffect, useRef, useCallback, useMemo } from 'react'
import maplibregl, { type StyleSpecification } from 'maplibre-gl'
import 'maplibre-gl/dist/maplibre-gl.css'
import { useStore } from '../state/store'
import { useOverview } from '../api/overview'

function buildGraticule(step = 10): GeoJSON.FeatureCollection<GeoJSON.LineString> {
  const features: GeoJSON.Feature<GeoJSON.LineString>[] = []

  for (let lon = -180; lon <= 180; lon += step) {
    const coords: [number, number][] = []
    for (let lat = -90; lat <= 90; lat += 2) coords.push([lon, lat])
    features.push({
      type: 'Feature',
      properties: { kind: 'meridian', value: lon },
      geometry: { type: 'LineString', coordinates: coords },
    })
  }

  for (let lat = -80; lat <= 80; lat += step) {
    const coords: [number, number][] = []
    for (let lon = -180; lon <= 180; lon += 2) coords.push([lon, lat])
    features.push({
      type: 'Feature',
      properties: { kind: 'parallel', value: lat },
      geometry: { type: 'LineString', coordinates: coords },
    })
  }

  return { type: 'FeatureCollection', features }
}

// Map σ₀ values to a viridis-like RGBA array on a canvas element.
function renderSliceToCanvas(slice: number[][]): string {
  const ny = slice.length
  const nx = slice[0]?.length ?? 0
  if (!ny || !nx) return ''

  const valid: number[] = []
  for (const row of slice) for (const v of row) {
    if (Number.isFinite(v) && v !== 0) valid.push(v)
  }
  if (!valid.length) return ''

  valid.sort((a, b) => a - b)
  const q05 = valid[Math.floor((valid.length - 1) * 0.05)]
  const q95 = valid[Math.floor((valid.length - 1) * 0.95)]
  const min = q05
  const max = q95 > q05 ? q95 : valid[valid.length - 1]
  const range = max - min || 1

  const canvas = document.createElement('canvas')
  canvas.width = nx
  canvas.height = ny
  const ctx = canvas.getContext('2d')!
  const img = ctx.createImageData(nx, ny)

  for (let y = 0; y < ny; y++) {
    for (let x = 0; x < nx; x++) {
      const value = slice[y][x]
      const i = (y * nx + x) * 4
      if (!Number.isFinite(value) || value === 0) {
        img.data[i + 3] = 0
        continue
      }
      const t = Math.max(0, Math.min(1, (value - min) / range))
      // viridis approximation: blue → teal → green → yellow
      const r = Math.round(255 * Math.max(0, Math.min(1, 1.8 * t - 0.8)))
      const g = Math.round(255 * Math.max(0, Math.min(1, t < 0.5 ? 2.2 * t : 2.2 - 2.2 * t)))
      const b = Math.round(255 * Math.max(0, Math.min(1, 0.9 - 1.4 * t)))
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
  const {
    data: overview,
    isLoading,
    isError,
  } = useOverview('north_atlantic', 'sigma0')

  useEffect(() => {
    if (!containerRef.current) return

    // Use a real raster basemap when available, with an internal graticule fallback
    // so the panel still reads like a map if external tiles are blocked.
    const BASEMAP_STYLE: StyleSpecification = {
      version: 8,
      sources: {
        osm: {
          type: 'raster',
          tiles: [
            'https://tile.openstreetmap.org/{z}/{x}/{y}.png',
            'https://a.tile.openstreetmap.org/{z}/{x}/{y}.png',
            'https://b.tile.openstreetmap.org/{z}/{x}/{y}.png',
            'https://c.tile.openstreetmap.org/{z}/{x}/{y}.png',
          ],
          tileSize: 256,
          attribution: '© OpenStreetMap contributors',
          maxzoom: 19,
        },
      },
      layers: [
        { id: 'bg', type: 'background', paint: { 'background-color': '#e9decc' } },
        {
          id: 'osm-raster',
          type: 'raster',
          source: 'osm',
          paint: {
            'raster-opacity': 0.8,
            'raster-saturation': -0.55,
            'raster-contrast': 0.08,
            'raster-brightness-min': 0.3,
            'raster-brightness-max': 0.98,
          },
        },
      ],
    }

    const map = new maplibregl.Map({
      container: containerRef.current,
      style: BASEMAP_STYLE,
      center: [(roi.lon_min + roi.lon_max) / 2, (roi.lat_min + roi.lat_max) / 2],
      zoom: 3,
      attributionControl: false,
    })

    map.addControl(new maplibregl.NavigationControl(), 'top-right')
    map.addControl(new maplibregl.AttributionControl({ compact: true }), 'bottom-right')

    map.on('load', () => {
      map.resize()
      map.addSource('graticule', {
        type: 'geojson',
        data: buildGraticule(),
      })
      map.addLayer({
        id: 'graticule',
        type: 'line',
        source: 'graticule',
        paint: {
          'line-color': '#9d8d74',
          'line-opacity': 0.36,
          'line-width': 1,
        },
      })

      // ROI rectangle
      map.addSource('roi', {
        type: 'geojson',
        data: { type: 'FeatureCollection', features: [] },
      })
      map.addLayer({
        id: 'roi-fill',
        type: 'fill',
        source: 'roi',
        paint: { 'fill-color': '#2e6f67', 'fill-opacity': 0.14 },
      })
      map.addLayer({
        id: 'roi-line',
        type: 'line',
        source: 'roi',
        paint: { 'line-color': '#215851', 'line-width': 1.8 },
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

    // Keep map sized to its container as CSS grid finalizes
    const ro = new ResizeObserver(() => map.resize())
    ro.observe(containerRef.current)

    return () => { ro.disconnect(); map.remove(); mapRef.current = null }
  }, [])

  // Sync ROI rectangle when store changes
  useEffect(() => {
    const map = mapRef.current
    if (!map || !map.isStyleLoaded()) return
    syncROI(map)
    map.fitBounds(
      [
        [roi.lon_min, roi.lat_min],
        [roi.lon_max, roi.lat_max],
      ],
      { padding: 28, duration: 0, maxZoom: 5.5 },
    )
  }, [roi.lat_min, roi.lat_max, roi.lon_min, roi.lon_max])

  // Add σ₀ heatmap overlay when overview data arrives
  useEffect(() => {
    const map = mapRef.current
    if (!map || !overview) return
    const surface = overview.depth_bands.find(b => b.band === 'surface')
    if (!surface?.mean_map) return

    const dataUrl = renderSliceToCanvas(surface.mean_map)
    if (!dataUrl) return
    const minLon = Math.min(...overview.lons)
    const maxLon = Math.max(...overview.lons)
    const minLat = Math.min(...overview.lats)
    const maxLat = Math.max(...overview.lats)

    const onLoad = () => {
      if (map.getLayer('sigma0-raster')) map.removeLayer('sigma0-raster')
      if (map.getSource('sigma0-img')) map.removeSource('sigma0-img')

      map.addSource('sigma0-img', {
        type: 'image',
        url: dataUrl,
        coordinates: [
          [minLon, maxLat],
          [maxLon, maxLat],
          [maxLon, minLat],
          [minLon, minLat],
        ],
      })
      map.addLayer(
        {
          id: 'sigma0-raster',
          type: 'raster',
          source: 'sigma0-img',
          paint: {
            'raster-opacity': 0.68,
            'raster-resampling': 'nearest',
          },
        },
        'graticule',
      )
    }

    if (map.isStyleLoaded()) onLoad()
    else map.once('load', onLoad)
  }, [overview])

  // Compute σ₀ range from overview data for legend
  const sigma0Range = useMemo(() => {
    if (!overview) return null
    const surface = overview.depth_bands.find(b => b.band === 'surface')
    if (!surface) return null
    return { min: surface.stats.min, max: surface.stats.max }
  }, [overview])

  return (
    <div style={{ position: 'relative', width: '100%', height: '100%' }}>
      <div ref={containerRef} style={{ width: '100%', height: '100%' }} />

      {/* Panel title */}
      <div style={{
        position: 'absolute', top: 8, left: 8,
        background: 'var(--bg-overlay)', color: 'var(--accent-strong)',
        fontSize: 11, fontWeight: 600, padding: '4px 8px',
        borderRadius: 4, pointerEvents: 'none', letterSpacing: '0.03em', border: '1px solid var(--border)',
      }}>
        Surface σ₀ — North Atlantic
      </div>

      {/* Click hint */}
      <div style={{
        position: 'absolute', top: 34, left: 8,
        background: 'var(--bg-overlay)', color: 'var(--info)',
        fontSize: 10, padding: '2px 6px', borderRadius: 3, pointerEvents: 'none', border: '1px solid var(--border)',
      }}>
        Click to re-center ROI
      </div>

      {/* σ₀ color scale legend */}
      {sigma0Range && (
        <div style={{
          position: 'absolute', bottom: 28, left: 8,
          background: 'var(--bg-overlay)', borderRadius: 4,
          padding: '5px 8px', pointerEvents: 'none', minWidth: 160, border: '1px solid var(--border)',
        }}>
          <div style={{ fontSize: 10, color: 'var(--accent-strong)', marginBottom: 3 }}>
            Potential density σ₀ (kg m⁻³)
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
            <span style={{ fontSize: 9, color: 'var(--info)' }}>{sigma0Range.min.toFixed(2)}</span>
            <div style={{
              flex: 1, height: 8, borderRadius: 2,
              background: 'linear-gradient(to right, rgb(68,1,84) 0%, rgb(59,82,139) 25%, rgb(33,145,140) 50%, rgb(94,201,98) 75%, rgb(253,231,37) 100%)',
            }} />
            <span style={{ fontSize: 9, color: 'var(--info)' }}>{sigma0Range.max.toFixed(2)}</span>
          </div>
        </div>
      )}
      {isLoading && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(247, 241, 231, 0.32)', color: 'var(--accent-strong)', fontSize: 12, pointerEvents: 'none',
        }}>
          Loading basin overview…
        </div>
      )}
      {isError && (
        <div style={{
          position: 'absolute', inset: 0, display: 'flex', alignItems: 'center', justifyContent: 'center',
          background: 'rgba(247, 241, 231, 0.72)', color: 'var(--warning)', fontSize: 12, pointerEvents: 'none',
          textAlign: 'center', padding: 24,
        }}>
          Basin overview unavailable right now
        </div>
      )}
    </div>
  )
}
