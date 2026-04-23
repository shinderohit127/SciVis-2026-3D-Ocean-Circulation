import React from 'react'

interface Props {
  status?: string
  jobId?: string
  error?: string | null
  vertexCount?: number
  faceCount?: number
}

const DOT: Record<string, string> = {
  queued:   'var(--warning)',
  running:  'var(--info)',
  complete: 'var(--success)',
  failed:   'var(--danger)',
}

export default function StatusBar({ status, jobId, error, vertexCount, faceCount }: Props) {
  return (
    <div style={{
      background: 'var(--bg-panel)',
      borderTop: '1px solid var(--border)',
      padding: '3px 12px',
      display: 'flex',
      alignItems: 'center',
      gap: 10,
      fontSize: 11,
      color: 'var(--text)',
      height: 24,
      flexShrink: 0,
    }}>
      {status && (
        <>
          <span style={{ width: 7, height: 7, borderRadius: '50%', background: DOT[status] ?? '#888', display: 'inline-block', flexShrink: 0 }} />
          <span>Isopycnal job</span>
          {jobId && <code style={{ color: 'var(--info)', fontFamily: 'monospace' }}>{jobId.slice(0, 8)}…</code>}
          <span style={{ color: DOT[status] ?? '#888' }}>({status})</span>
          {status === 'complete' && vertexCount != null && (
            <span style={{ color: 'var(--accent)' }}>
              {vertexCount.toLocaleString()} verts · {faceCount?.toLocaleString()} faces
            </span>
          )}
          {error && <span style={{ color: 'var(--danger)', marginLeft: 4 }}>⚠ {error}</span>}
        </>
      )}
      {!status && <span style={{ color: 'var(--text-muted)' }}>Ready — set ROI and σ₀ to extract isopycnal surface</span>}
    </div>
  )
}
