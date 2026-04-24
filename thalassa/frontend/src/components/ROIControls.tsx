import React, { useEffect, useRef } from 'react'
import { useStore } from '../state/store'
import type { ColorBy, PlaySpeed } from '../state/store'

const s: Record<string, React.CSSProperties> = {
  panel: {
    width: 220,
    minWidth: 220,
    padding: '0.75rem',
    background: 'var(--bg-panel)',
    color: 'var(--text)',
    display: 'flex',
    flexDirection: 'column',
    gap: '0.6rem',
    fontSize: 12,
    overflowY: 'auto',
    borderRight: '1px solid var(--border)',
  },
  label: { display: 'block', marginBottom: 2, color: 'var(--accent-strong)', fontSize: 11 },
  hint: { fontSize: 10, color: 'var(--text-muted)', marginTop: 3, lineHeight: 1.4 },
  input: {
    width: '100%',
    background: 'var(--bg-panel-alt)',
    border: '1px solid var(--border-strong)',
    color: 'var(--text-strong)',
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
    color: 'var(--info)',
    borderBottom: '1px solid var(--border)',
    paddingBottom: 3,
    marginBottom: 4,
  },
  divider: { borderTop: '1px solid var(--border)', margin: '2px 0' },
}

const MAX_TIMESTEP = 10311

function stepToDate(step: number): string {
  const ms = Date.UTC(2011, 8, 10) + step * 3_600_000
  const d = new Date(ms)
  return d.toUTCString().slice(5, 22)   // e.g. "10 Sep 2011 06:00"
}

export default function ROIControls({ onApply }: { onApply?: () => void }) {
  const {
    roi, sigma0Value, colorBy, isPlaying, playSpeed,
    setROI, setSigma0, setColorBy, setIsPlaying, setPlaySpeed,
  } = useStore()

  const playRef = useRef<ReturnType<typeof setInterval> | null>(null)

  useEffect(() => {
    if (playRef.current) clearInterval(playRef.current)
    if (!isPlaying) return
    const ms = Math.round(1000 / playSpeed)
    playRef.current = setInterval(() => {
      setROI({ timestep: (roi.timestep + 1) > MAX_TIMESTEP ? 0 : roi.timestep + 1 })
    }, ms)
    return () => { if (playRef.current) clearInterval(playRef.current) }
  }, [isPlaying, playSpeed, roi.timestep])

  return (
    <div style={s.panel}>

      {/* Header */}
      <div style={{ marginBottom: 4 }}>
        <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--accent-strong)', letterSpacing: '0.04em' }}>
          3D Ocean Circulation
        </div>
        <div style={{ fontSize: 10, color: 'var(--info)', marginTop: 2 }}>
          ECCO LLC4320 · IEEE SciVis 2026
        </div>
      </div>

      <div style={s.divider} />

      {/* ROI section */}
      <div style={{ ...s.sectionTitle, marginBottom: 6 }}>Region of Interest</div>
      <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: -4, marginBottom: 4, lineHeight: 1.4 }}>
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

      {/* Temporal navigation */}
      <div>
        <div style={s.sectionTitle}>Temporal Navigation</div>

        {/* Date display */}
        <div style={{
          fontSize: 11, color: 'var(--accent-strong)', fontVariantNumeric: 'tabular-nums',
          marginBottom: 4, letterSpacing: '0.02em',
        }}>
          t={roi.timestep} · {stepToDate(roi.timestep)}
        </div>

        {/* Slider */}
        <input
          type="range" min={0} max={MAX_TIMESTEP} step={1}
          value={roi.timestep}
          onChange={e => { setIsPlaying(false); setROI({ timestep: +e.target.value }) }}
          style={{ width: '100%', accentColor: 'var(--accent)', cursor: 'pointer' }}
        />

        {/* Step buttons + play/pause */}
        <div style={{ display: 'flex', gap: 4, marginTop: 4, justifyContent: 'center' }}>
          {([
            { label: '⏮', title: 'First', action: () => { setIsPlaying(false); setROI({ timestep: 0 }) } },
            { label: '◀', title: 'Step back', action: () => { setIsPlaying(false); setROI({ timestep: Math.max(0, roi.timestep - 1) }) } },
            {
              label: isPlaying ? '⏸' : '▶',
              title: isPlaying ? 'Pause' : 'Play',
              action: () => setIsPlaying(!isPlaying),
              accent: true,
            },
            { label: '▶', title: 'Step forward', action: () => { setIsPlaying(false); setROI({ timestep: Math.min(MAX_TIMESTEP, roi.timestep + 1) }) } },
            { label: '⏭', title: 'Last', action: () => { setIsPlaying(false); setROI({ timestep: MAX_TIMESTEP }) } },
          ] as const).map(({ label, title, action, accent }: any) => (
            <button key={title} title={title} onClick={action} style={{
              flex: 1, padding: '3px 0', fontSize: 13,
              background: accent ? 'var(--accent)' : 'var(--bg-panel-alt)',
              border: '1px solid var(--border-strong)',
              borderRadius: 3, color: accent ? '#fffaf2' : 'var(--text-strong)',
              cursor: 'pointer',
            }}>
              {label}
            </button>
          ))}
        </div>

        {/* Speed selector */}
        <div style={{ display: 'flex', gap: 3, marginTop: 5, alignItems: 'center' }}>
          <span style={{ fontSize: 10, color: 'var(--text-muted)', whiteSpace: 'nowrap' }}>Speed:</span>
          {([0.5, 1, 2, 4] as PlaySpeed[]).map(v => (
            <button key={v} onClick={() => setPlaySpeed(v)} style={{
              flex: 1, padding: '2px 0', fontSize: 10,
              background: playSpeed === v ? 'var(--accent)' : 'var(--bg-panel-alt)',
              border: `1px solid ${playSpeed === v ? 'var(--accent-strong)' : 'var(--border-strong)'}`,
              borderRadius: 3,
              color: playSpeed === v ? '#fffaf2' : 'var(--text-strong)',
              cursor: 'pointer',
            }}>
              {v}×
            </button>
          ))}
        </div>
        <div style={s.hint}>
          Scrub or play through 10,312 hourly snapshots (Sep 2011 – Nov 2012).
          Use the Anomaly Timeline panel to find interesting regimes first.
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
        <div style={{ ...s.hint, marginTop: 4, borderLeft: '2px solid var(--info)', paddingLeft: 5 }}>
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
            width: '100%', padding: '5px 8px', background: 'var(--accent)',
            border: '1px solid var(--accent-strong)', borderRadius: 3, color: '#fffaf2',
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
