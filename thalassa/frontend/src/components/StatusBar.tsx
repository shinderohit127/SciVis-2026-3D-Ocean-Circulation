import React from 'react'

interface Props {
  status?: string
  jobId?: string
  error?: string | null
  vertexCount?: number
  faceCount?: number
}

const DOT: Record<string, string> = {
  queued:   '#f0a020',
  running:  '#20a8f0',
  complete: '#20c060',
  failed:   '#f04040',
}

export default function StatusBar({ status, jobId, error, vertexCount, faceCount }: Props) {
  return (
    <div style={{
      background: '#060f1a',
      borderTop: '1px solid #112240',
      padding: '3px 12px',
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      fontSize: 11,
      color: '#6aaad4',
      height: 24,
      flexShrink: 0,
    }}>
      {status && (
        <>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: DOT[status] ?? '#888', display: 'inline-block', flexShrink: 0 }} />
          <span>Isopycnal job</span>
          {jobId && <code style={{ color: '#2a6a9c', fontFamily: 'monospace' }}>{jobId.slice(0, 8)}…</code>}
          <span style={{ color: DOT[status] ?? '#888' }}>({status})</span>
          {status === 'complete' && vertexCount != null && (
            <span style={{ color: '#3a8abd' }}>
              {vertexCount.toLocaleString()} verts · {faceCount?.toLocaleString()} faces
            </span>
          )}
          {error && <span style={{ color: '#f04040', marginLeft: 4 }}>⚠ {error}</span>}
        </>
      )}
      {!status && <span style={{ color: '#2a4a6c' }}>Ready — set ROI and σ₀ to extract isopycnal surface</span>}
    </div>
  )
}
