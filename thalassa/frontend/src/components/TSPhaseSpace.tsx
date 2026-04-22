import React, { useMemo, useCallback } from 'react'
import Plot from 'react-plotly.js'
import { useStore } from '../state/store'
import { useDensityFields } from '../api/derived'

export default function TSPhaseSpace() {
  const { roi, setSigma0, setBrushedSigma0Range } = useStore()

  const { data, isLoading, isError } = useDensityFields(
    roi,
    ['CT', 'SA', 'sigma0'],
    true,
  )

  // Flatten CT / SA / σ₀ surface slices into scatter arrays
  const { ct, sa, s0 } = useMemo(() => {
    if (!data?.fields) return { ct: [], sa: [], s0: [] }
    const ctSlice = data.fields['CT']?.surface_slice ?? []
    const saSlice = data.fields['SA']?.surface_slice ?? []
    const s0Slice = data.fields['sigma0']?.surface_slice ?? []

    const ct: number[] = [], sa: number[] = [], s0: number[] = []
    for (let y = 0; y < ctSlice.length; y++) {
      for (let x = 0; x < (ctSlice[y]?.length ?? 0); x++) {
        const cv = ctSlice[y][x], sv = saSlice[y]?.[x], dv = s0Slice[y]?.[x]
        if (isFinite(cv) && isFinite(sv) && isFinite(dv)) {
          ct.push(cv); sa.push(sv); s0.push(dv)
        }
      }
    }
    return { ct, sa, s0 }
  }, [data])

  // When user selects points via lasso, compute σ₀ range of selection
  // and update the store → triggers a new isopycnal job at the median σ₀.
  const onSelected = useCallback((event: Plotly.PlotSelectionEvent) => {
    if (!event?.points?.length) { setBrushedSigma0Range(null); return }
    const selectedSigma0 = event.points
      .map(p => s0[p.pointIndex])
      .filter(isFinite)
    if (!selectedSigma0.length) return
    const lo = Math.min(...selectedSigma0)
    const hi = Math.max(...selectedSigma0)
    setBrushedSigma0Range([lo, hi])
    setSigma0(+((lo + hi) / 2).toFixed(2))
  }, [s0, setSigma0, setBrushedSigma0Range])

  if (isLoading) {
    return (
      <div style={{ width:'100%', height:'100%', display:'flex', alignItems:'center', justifyContent:'center', background:'#060f1a', color:'#2a6a9c', fontSize:12 }}>
        Loading T-S data…
      </div>
    )
  }
  if (isError || !data) {
    return (
      <div style={{ width:'100%', height:'100%', display:'flex', alignItems:'center', justifyContent:'center', background:'#060f1a', color:'#f04040', fontSize:12 }}>
        T-S data unavailable — backend may be busy
      </div>
    )
  }

  return (
    <Plot
      data={[{
        type: 'scattergl',
        mode: 'markers',
        x: ct,
        y: sa,
        marker: {
          size: 3,
          color: s0,
          colorscale: 'Viridis',
          showscale: true,
          colorbar: {
            title: { text: 'σ₀', font: { color: '#6aaad4', size: 10 } } as any,
            tickfont: { color: '#6aaad4', size: 9 },
            thickness: 10,
            len: 0.8,
          },
          opacity: 0.7,
        },
      } as any]}
      layout={{
        paper_bgcolor: '#060f1a',
        plot_bgcolor: '#060f1a',
        margin: { l: 50, r: 20, t: 30, b: 45 },
        title: {
          text: 'T–S Phase Space  (lasso to set σ₀)',
          font: { color: '#6aaad4', size: 12 },
          x: 0.5,
          y: 0.97,
        },
        xaxis: {
          title: { text: 'Conservative Temperature CT (°C)', font: { color: '#6aaad4', size: 10 } },
          color: '#2a6a9c',
          gridcolor: '#0a1929',
          zerolinecolor: '#1a3a5c',
        },
        yaxis: {
          title: { text: 'Absolute Salinity SA (g kg⁻¹)', font: { color: '#6aaad4', size: 10 } },
          color: '#2a6a9c',
          gridcolor: '#0a1929',
          zerolinecolor: '#1a3a5c',
        },
        dragmode: 'lasso',
        font: { color: '#6aaad4' },
      }}
      config={{ displayModeBar: true, modeBarButtonsToRemove: ['toImage'], responsive: true }}
      style={{ width: '100%', height: '100%' }}
      onSelected={onSelected}
      onDeselect={() => setBrushedSigma0Range(null)}
      useResizeHandler
    />
  )
}
