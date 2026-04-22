import React from 'react'
import { useStore } from '../state/store'
import type { ColorBy } from '../state/store'

const s: Record<string, React.CSSProperties> = {
  panel: {
    width: 210,
    minWidth: 210,
    padding: '0.75rem',
    background: '#0a1929',
    color: '#e0f0ff',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.65rem',
    fontSize: 12,
    overflowY: 'auto',
    borderRight: '1px solid #1a3a5c',
  },
  label: { display: 'block', marginBottom: 2, color: '#6aaad4', fontSize: 11 },
  input: {
    width: '100%',
    background: '#112240',
    border: '1px solid #1e4976',
    color: '#e0f0ff',
    padding: '3px 6px',
    borderRadius: 3,
    boxSizing: 'border-box',
    fontSize: 12,
  },
  group: { display: 'flex', gap: 4 },
  half: { flex: 1, minWidth: 0 },
  sectionTitle: {
    fontSize: 10,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.08em',
    color: '#2a6a9c',
    borderBottom: '1px solid #112240',
    paddingBottom: 3,
    marginBottom: 3,
  },
  logo: { marginBottom: 2 },
  logoTitle: { fontSize: 18, fontWeight: 700, color: '#40a0e0', letterSpacing: '0.05em' },
  logoSub: { fontSize: 10, color: '#2a6a9c', marginTop: 1 },
  btn: {
    width: '100%',
    padding: '5px 8px',
    background: '#1a5f9c',
    border: 'none',
    borderRadius: 3,
    color: '#e0f0ff',
    fontSize: 11,
    cursor: 'pointer',
  },
}

export default function ROIControls({ onApply }: { onApply?: () => void }) {
  const { roi, sigma0Value, colorBy, setROI, setSigma0, setColorBy } = useStore()

  return (
    <div style={s.panel}>
      <div style={s.logo}>
        <div style={s.logoTitle}>THALASSA</div>
        <div style={s.logoSub}>LLC4320 · ECCO SciVis 2026</div>
      </div>

      <div>
        <div style={s.sectionTitle}>Latitude</div>
        <div style={s.group}>
          <div style={s.half}>
            <label style={s.label}>Min</label>
            <input style={s.input} type="number" step={1} value={roi.lat_min}
              onChange={e => setROI({ lat_min: +e.target.value })} />
          </div>
          <div style={s.half}>
            <label style={s.label}>Max</label>
            <input style={s.input} type="number" step={1} value={roi.lat_max}
              onChange={e => setROI({ lat_max: +e.target.value })} />
          </div>
        </div>
      </div>

      <div>
        <div style={s.sectionTitle}>Longitude</div>
        <div style={s.group}>
          <div style={s.half}>
            <label style={s.label}>Min</label>
            <input style={s.input} type="number" step={1} value={roi.lon_min}
              onChange={e => setROI({ lon_min: +e.target.value })} />
          </div>
          <div style={s.half}>
            <label style={s.label}>Max</label>
            <input style={s.input} type="number" step={1} value={roi.lon_max}
              onChange={e => setROI({ lon_max: +e.target.value })} />
          </div>
        </div>
      </div>

      <div>
        <div style={s.sectionTitle}>Depth (m)</div>
        <div style={s.group}>
          <div style={s.half}>
            <label style={s.label}>Min</label>
            <input style={s.input} type="number" step={100} value={roi.depth_min_m}
              onChange={e => setROI({ depth_min_m: +e.target.value })} />
          </div>
          <div style={s.half}>
            <label style={s.label}>Max</label>
            <input style={s.input} type="number" step={100} value={roi.depth_max_m}
              onChange={e => setROI({ depth_max_m: +e.target.value })} />
          </div>
        </div>
      </div>

      <div>
        <div style={s.sectionTitle}>Timestep</div>
        <input style={s.input} type="number" min={0} max={10311} step={1}
          value={roi.timestep}
          onChange={e => setROI({ timestep: +e.target.value })} />
        <div style={{ fontSize: 10, color: '#2a6a9c', marginTop: 2 }}>0 – 10311 (hourly)</div>
      </div>

      <div>
        <div style={s.sectionTitle}>Isopycnal surface</div>
        <label style={s.label}>σ₀ value (kg m⁻³ − 1000)</label>
        <input style={s.input} type="number" step={0.1} min={20} max={30}
          value={sigma0Value}
          onChange={e => setSigma0(+e.target.value)} />
      </div>

      <div>
        <div style={s.sectionTitle}>Color by</div>
        <select style={s.input} value={colorBy ?? ''}
          onChange={e => setColorBy((e.target.value || null) as ColorBy)}>
          <option value="">None (uniform)</option>
          <option value="CT">Conservative Temp (CT)</option>
          <option value="SA">Absolute Salinity (SA)</option>
          <option value="alpha">Thermal expansion (α)</option>
          <option value="beta">Haline contraction (β)</option>
        </select>
      </div>

      {onApply && (
        <button style={s.btn} onClick={onApply}>
          Apply &amp; re-query
        </button>
      )}
    </div>
  )
}
