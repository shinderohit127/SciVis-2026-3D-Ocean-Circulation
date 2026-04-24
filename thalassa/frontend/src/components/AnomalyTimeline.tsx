import React, { useState, useCallback } from 'react'
import Plot from 'react-plotly.js'
import { useStore } from '../state/store'
import { useTemporalWindow } from '../api/temporal'
import type { TemporalWindowParams } from '../api/temporal'

const MAX_T = 10311

function stepToDate(step: number): string {
  // Step 0 = 2011-09-10 00:00 UTC; 1 step = 1 hour
  const ms = Date.UTC(2011, 8, 10) + step * 3_600_000
  return new Date(ms).toISOString().slice(0, 13).replace('T', ' ') + 'h UTC'
}

export default function AnomalyTimeline() {
  const { roi, setROI } = useStore()
  const [windowParams, setWindowParams] = useState<TemporalWindowParams | null>(null)
  const [tStart, setTStart] = useState(0)
  const [tEnd, setTEnd] = useState(Math.min(500, MAX_T))

  const { result, isLoading, error, status } = useTemporalWindow(windowParams)

  const handleLoad = useCallback(() => {
    setWindowParams({
      lat_min:     roi.lat_min,
      lat_max:     roi.lat_max,
      lon_min:     roi.lon_min,
      lon_max:     roi.lon_max,
      depth_min_m: roi.depth_min_m,
      depth_max_m: roi.depth_max_m,
      t_start:     tStart,
      t_end:       tEnd,
      n_samples:   60,
    })
  }, [roi, tStart, tEnd])

  const onPlotClick = useCallback((event: Plotly.PlotMouseEvent) => {
    const pt = event.points?.[0]
    if (pt == null) return
    const t = pt.x as number
    if (Number.isFinite(t)) setROI({ timestep: Math.round(t) })
  }, [setROI])

  const descriptors = result?.descriptors ?? []
  const xs = descriptors.map(d => d.timestep)
  const ys = descriptors.map(d => d.anomaly_score)
  const texts = descriptors.map(d =>
    `t=${d.timestep}<br>${stepToDate(d.timestep)}<br>σ₀ ${d.sigma0_mean.toFixed(3)}<br>CT ${d.ct_mean.toFixed(2)}°C<br>anomaly z=${d.anomaly_score.toFixed(2)}`
  )

  const barColors = ys.map(v => {
    if (v > 2) return '#c0392b'
    if (v > 1) return '#e67e22'
    return '#2e6f67'
  })

  const inputStyle: React.CSSProperties = {
    width: 70, background: 'var(--bg-panel-alt)', border: '1px solid var(--border-strong)',
    color: 'var(--text-strong)', padding: '2px 4px', borderRadius: 3, fontSize: 11,
  }

  return (
    <div style={{ width: '100%', height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg-panel-alt)', position: 'relative' }}>

      {/* Controls bar */}
      <div style={{
        display: 'flex', alignItems: 'center', gap: 8, padding: '5px 10px',
        background: 'var(--bg-panel)', borderBottom: '1px solid var(--border)', flexShrink: 0, flexWrap: 'wrap',
      }}>
        <span style={{ fontSize: 11, fontWeight: 600, color: 'var(--accent-strong)', letterSpacing: '0.03em' }}>
          Anomaly Timeline
        </span>
        <span style={{ fontSize: 10, color: 'var(--text-muted)' }}>
          Scores show how unusual σ₀ is at each sampled timestep.  High (red) = anomalous regime.
        </span>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginLeft: 'auto' }}>
          <label style={{ fontSize: 10, color: 'var(--info)' }}>t₀</label>
          <input style={inputStyle} type="number" min={0} max={MAX_T - 1} value={tStart}
            onChange={e => setTStart(Math.max(0, Math.min(tEnd - 1, +e.target.value)))} />
          <label style={{ fontSize: 10, color: 'var(--info)' }}>t₁</label>
          <input style={inputStyle} type="number" min={1} max={MAX_T} value={tEnd}
            onChange={e => setTEnd(Math.max(tStart + 1, Math.min(MAX_T, +e.target.value)))} />
          <button
            onClick={handleLoad}
            disabled={isLoading}
            style={{
              padding: '3px 10px', background: isLoading ? 'var(--border)' : 'var(--accent)',
              border: '1px solid var(--accent-strong)', borderRadius: 3,
              color: '#fffaf2', fontSize: 11, cursor: isLoading ? 'default' : 'pointer',
            }}
          >
            {isLoading ? `${status ?? 'loading'}…` : 'Load window'}
          </button>
        </div>
      </div>

      {/* Chart or placeholder */}
      {!windowParams && (
        <div style={{
          flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center',
          color: 'var(--info)', fontSize: 12, gap: 6, padding: 20, textAlign: 'center',
        }}>
          <div style={{ fontSize: 13, color: 'var(--accent-strong)', fontWeight: 600 }}>
            Temporal Anomaly Navigator
          </div>
          <div style={{ fontSize: 11, color: 'var(--text-muted)', maxWidth: 340, lineHeight: 1.5 }}>
            Set a time window (t₀ → t₁) and click <strong>Load window</strong> to compute
            thermohaline descriptors at 60 sampled timesteps.  Each bar is a z-score
            measuring how anomalous the density field is relative to the window mean.
            Click any bar to jump to that timestep.
          </div>
          <div style={{ fontSize: 10, color: 'var(--text-muted)', marginTop: 4 }}>
            Step 0 = Sep 10 2011 · Step 10 311 = Nov 2012 · 1 step = 1 hour
          </div>
        </div>
      )}

      {error && (
        <div style={{
          flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center',
          color: 'var(--danger)', fontSize: 12, padding: 20, textAlign: 'center',
        }}>
          Timeline computation failed — {error}
        </div>
      )}

      {windowParams && !error && (
        <div style={{ flex: 1, minHeight: 0 }}>
          <Plot
            data={[
              {
                type: 'bar',
                x: xs,
                y: ys,
                text: texts,
                hovertemplate: '%{text}<extra></extra>',
                marker: { color: barColors, opacity: 0.88 },
                name: 'Anomaly score',
              } as any,
              // Vertical line at current timestep
              {
                type: 'scatter',
                mode: 'lines',
                x: [roi.timestep, roi.timestep],
                y: [0, Math.max(...ys, 1) * 1.12],
                line: { color: '#e74c3c', width: 1.5, dash: 'dot' },
                hoverinfo: 'skip',
                showlegend: false,
                name: 'current',
              } as any,
            ]}
            layout={{
              paper_bgcolor: 'var(--bg-panel-alt, #f7f1e7)',
              plot_bgcolor:  'var(--bg-panel-alt, #fbf7f1)',
              margin: { l: 52, r: 18, t: 28, b: 52 },
              title: {
                text: result
                  ? `${result.n_computed} samples · t ${result.t_start}–${result.t_end} · click a bar to jump`
                  : isLoading ? 'Computing…' : '',
                font: { color: '#215851', size: 10 }, x: 0.5, y: 0.98,
              },
              xaxis: {
                title: { text: 'Timestep', font: { color: '#215851', size: 10 } },
                color: '#5c5043', gridcolor: '#e1d5c2', zerolinecolor: '#cfbea7',
              },
              yaxis: {
                title: { text: '|σ₀ z-score|', font: { color: '#215851', size: 10 } },
                color: '#5c5043', gridcolor: '#e1d5c2', rangemode: 'nonnegative',
                // reference lines at z=1 and z=2
              },
              shapes: [
                { type: 'line', x0: xs[0] ?? 0, x1: xs[xs.length - 1] ?? MAX_T, y0: 1, y1: 1,
                  line: { color: '#e67e22', width: 1, dash: 'dot' } },
                { type: 'line', x0: xs[0] ?? 0, x1: xs[xs.length - 1] ?? MAX_T, y0: 2, y1: 2,
                  line: { color: '#c0392b', width: 1, dash: 'dot' } },
              ],
              annotations: [
                { x: xs[xs.length - 1] ?? MAX_T, y: 1, xanchor: 'right', yanchor: 'bottom',
                  text: 'z=1', showarrow: false, font: { size: 8, color: '#e67e22' } },
                { x: xs[xs.length - 1] ?? MAX_T, y: 2, xanchor: 'right', yanchor: 'bottom',
                  text: 'z=2', showarrow: false, font: { size: 8, color: '#c0392b' } },
              ],
              font: { color: '#5c5043' },
              hovermode: 'x unified',
            }}
            config={{ displayModeBar: false, responsive: true }}
            style={{ width: '100%', height: '100%' }}
            onClick={onPlotClick}
            useResizeHandler
          />
        </div>
      )}
    </div>
  )
}
