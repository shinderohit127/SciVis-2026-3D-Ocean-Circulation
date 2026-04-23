import React from 'react'
import ROIControls from '../components/ROIControls'
import OverviewMap from '../components/OverviewMap'
import IsopycnalView from '../components/IsopycnalView'
import TSPhaseSpace from '../components/TSPhaseSpace'
import StatusBar from '../components/StatusBar'
import PanelBoundary from '../components/PanelBoundary'
import { useStore } from '../state/store'
import { useIsopycnalJob } from '../api/isopycnal'

export default function MainLayout() {
  const { roi, sigma0Value, colorBy } = useStore()
  const { status, mesh, error, jobId, isLoading } = useIsopycnalJob(roi, sigma0Value, colorBy)

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: '100vh',
      background: '#060f1a',
      overflow: 'hidden',
    }}>
      {/* Main area: sidebar + panels */}
      <div style={{ display: 'flex', flex: 1, minHeight: 0 }}>
        {/* Left sidebar */}
        <ROIControls />

        {/* 3-panel grid */}
        <div style={{
          flex: 1,
          display: 'grid',
          height: '100%',
          gridTemplateColumns: '1fr 1fr',
          gridTemplateRows: '55fr 45fr',
          minWidth: 0,
        }}>
          {/* Top-left: overview map */}
          <div style={{ borderRight: '1px solid #112240', borderBottom: '1px solid #112240', overflow: 'hidden' }}>
            <PanelBoundary label="Overview Map">
              <OverviewMap />
            </PanelBoundary>
          </div>

          {/* Top-right: 3D isopycnal */}
          <div style={{ borderBottom: '1px solid #112240', overflow: 'hidden' }}>
            <PanelBoundary label="Isopycnal View">
              <IsopycnalView mesh={mesh} isLoading={isLoading} />
            </PanelBoundary>
          </div>

          {/* Bottom: T-S phase space (spans both columns) */}
          <div style={{ gridColumn: '1 / -1', overflow: 'hidden' }}>
            <PanelBoundary label="T-S Phase Space">
              <TSPhaseSpace />
            </PanelBoundary>
          </div>
        </div>
      </div>

      {/* Status bar */}
      <StatusBar
        status={status}
        jobId={jobId}
        error={error}
        vertexCount={mesh?.vertex_count}
        faceCount={mesh?.face_count}
      />
    </div>
  )
}
