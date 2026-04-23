import React from 'react'
import { useStore } from '../state/store'
import type { ColorBy } from '../state/store'

const s: Record<string, React.CSSProperties> = {
  panel: {
    width: 220,
    minWidth: 220,
    padding: '0.75rem',
    background: '#0a1929',
    color: '#e0f0ff',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.6rem',
    fontSize: 12,
    overflowY: 'auto',
    borderRight: '1px solid #1a3a5c',
  },
  label: { display: 'block', marginBottom: 2, color: '#6aaad4', fontSize: 11 },
  hint: { fontSize: 10, color: '#2a5a7c', marginTop: 3, lineHeight: 1.4 },
  input: {
    width: '100%',
    background: '#112240',
    border: '1px solid #1e4976',
    color: '#e0f0ff',
    padding: '3px 6px',
    borderRadius: 3,
    boxSizing: 'border-box' as const,
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
    marginBottom: 4,
  },
  divider: { borderTop: '1px solid #0d2035', margin: '2px 0' },
}

export default function ROIControls({ onApply }: { onApply?: () => void }) {
  const { roi, sigma0Value, colorBy, setROI, setSigma0, setColorBy } = useStore()

  return (
    <div style={s.panel}>

      {/* Header */}
      <div style={{ marginBottom: 4 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: '#40a0e0', letterSpacing: '0.04em' }}>
          3D Ocean Circulation
        </div>
        <div style={{ fontSize: 10, color: '#2a6a9c', marginTop: 2 }}>
          ECCO LLC4320 · IEEE SciVis 2026
        </div>
      </div>

      <div style={s.divider} />

      {/* ROI section */}
      <div style={{ ...s.sectionTitle, marginBottom: 6 }}>Region of Interest</div>
      <div style={{ fontSize: 10, color: '#2a5a7c', marginTop: -4, marginBottom: 4, lineHeight: 1.4 }}>
        Drag the map to re-center, or type coordinates directly.
      </div>

      <div>
        <div style={s.sectionTitle}>Latitude (°N)</div>
        <div style={s.group}>
          <div style={s.half}>
            <label style={s.label}>South</label>
            <input style={s.input} type="number" step={1} value={roi.lat_min}
              onChange={e => setROI({ lat_min: +e.target.value })} />
          </div>
          <div style={s.half}>
            <label style={s.label}>North</label>
            <input style={s.input} type="number" step={1} value={roi.lat_max}
              onChange={e => setROI({ lat_max: +e.target.value })} />
          </div>
        </div>
      </div>

      <div>
        <div style={s.sectionTitle}>Longitude (°E)</div>
        <div style={s.group}>
          <div style={s.half}>
            <label style={s.label}>West</label>
            <input style={s.input} type="number" step={1} value={roi.lon_min}
              onChange={e => setROI({ lon_min: +e.target.value })} />
          </div>
          <div style={s.half}>
            <label style={s.label}>East</label>
            <input style={s.input} type="number" step={1} value={roi.lon_max}
              onChange={e => setROI({ lon_max: +e.target.value })} />
          </div>
        </div>
        <div style={s.hint}>Negative = west of prime meridian (e.g. −40 = 40°W)</div>
      </div>

      <div>
        <div style={s.sectionTitle}>Depth (m)</div>
        <div style={s.group}>
          <div style={s.half}>
            <label style={s.label}>Surface</label>
            <input style={s.input} type="number" step={100} value={roi.depth_min_m}
              onChange={e => setROI({ depth_min_m: +e.target.value })} />
          </div>
          <div style={s.half}>
            <label style={s.label}>Bottom</label>
            <input style={s.input} type="number" step={100} value={roi.depth_max_m}
              onChange={e => setROI({ depth_max_m: +e.target.value })} />
          </div>
        </div>
        <div style={s.hint}>Ocean depth range to query. Max ≈ 6 600 m in the abyss.</div>
      </div>

      <div>
        <div style={s.sectionTitle}>Timestep</div>
        <input style={s.input} type="number" min={0} max={10311} step={1}
          value={roi.timestep}
          onChange={e => setROI({ timestep: +e.target.value })} />
        <div style={s.hint}>
          1 step = 1 hour. Step 0 = Sep 10 2011 00:00 UTC. Range: 0 – 10 311.
        </div>
      </div>

      <div style={s.divider} />

      {/* Isopycnal σ₀ */}
      <div>
        <div style={s.sectionTitle}>Isopycnal Surface (σ₀)</div>
        <label style={s.label}>Potential density σ₀ (kg m⁻³)</label>
        <input style={s.input} type="number" step={0.1} min={20} max={30}
          value={sigma0Value}
          onChange={e => setSigma0(+e.target.value)} />
        <div style={s.hint}>
          An isopycnal is a surface where seawater has the same potential density.
          Water on the same isopycnal mixes easily; crossing one requires energy.
        </div>
        <div style={{ ...s.hint, marginTop: 4, borderLeft: '2px solid #1a4a6c', paddingLeft: 5 }}>
          Typical ranges — surface warm water: 24–26 · thermocline: 26–27.5 ·
          deep cold water: 27.5–28
        </div>
      </div>

      {/* Color by */}
      <div>
        <div style={s.sectionTitle}>Color Surface By</div>
        <select style={s.input} value={colorBy ?? ''}
          onChange={e => setColorBy((e.target.value || null) as ColorBy)}>
          <option value="">Uniform (no coloring)</option>
          <option value="CT">Conservative Temperature (CT)</option>
          <option value="SA">Absolute Salinity (SA)</option>
          <option value="alpha">Thermal Expansion (α)</option>
          <option value="beta">Haline Contraction (β)</option>
        </select>
        <div style={s.hint}>
          Paint the isopycnal with a scalar field. CT reveals warm/cold cores;
          SA shows fresher vs saltier water masses.
        </div>
      </div>

      {onApply && (
        <button
          style={{
            width: '100%', padding: '5px 8px', background: '#1a5f9c',
            border: 'none', borderRadius: 3, color: '#e0f0ff',
            fontSize: 11, cursor: 'pointer', marginTop: 4,
          }}
          onClick={onApply}
        >
          Apply &amp; re-query
        </button>
      )}
    </div>
  )
}
