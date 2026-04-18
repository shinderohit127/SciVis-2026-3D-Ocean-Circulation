import React from 'react'
import { useMetadata } from './api/metadata'

const styles: Record<string, React.CSSProperties> = {
  root: { fontFamily: 'system-ui, sans-serif', maxWidth: 900, margin: '0 auto', padding: '2rem' },
  center: { display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', height: '100vh' },
  header: { marginBottom: '2rem', borderBottom: '2px solid #1a3a5c', paddingBottom: '1rem' },
  title: { margin: 0, fontSize: '2.5rem', color: '#1a3a5c' },
  subtitle: { margin: '0.25rem 0 0', color: '#555' },
  main: { display: 'flex', flexDirection: 'column', gap: '1.5rem' },
  card: { border: '1px solid #c8d8e8', borderRadius: 6, padding: '1.25rem', background: '#f8fafc' },
  cardMuted: { border: '1px solid #ccc', borderRadius: 6, padding: '1.25rem', background: '#f8fafc', color: '#888' },
  table: { width: '100%', borderCollapse: 'collapse', marginTop: '0.5rem' },
  version: { fontSize: '0.8rem', color: '#888', marginTop: '0.5rem' },
  code: { fontFamily: 'monospace', background: '#e8f0fa', padding: '0 4px', borderRadius: 3 },
}

export default function App() {
  const { data, isLoading, isError, error } = useMetadata()

  if (isLoading) {
    return (
      <div style={styles.center}>
        <p>Connecting to THALASSA backend...</p>
      </div>
    )
  }

  if (isError) {
    return (
      <div style={styles.center}>
        <p style={{ color: '#c00' }}>Backend unavailable: {(error as Error).message}</p>
        <p>Start the FastAPI server: <code style={styles.code}>cd thalassa/backend && uvicorn main:app --reload</code></p>
      </div>
    )
  }

  return (
    <div style={styles.root}>
      <header style={styles.header}>
        <h1 style={styles.title}>THALASSA</h1>
        <p style={styles.subtitle}>Multiscale visual analytics — ECCO LLC4320 ocean circulation</p>
      </header>

      <main style={styles.main}>
        <section style={styles.card}>
          <h2>Dataset: {data!.dataset}</h2>
          <p>
            Grid: {data!.grid.ny.toLocaleString()} lat &times; {data!.grid.nx.toLocaleString()} lon &times; {data!.grid.nz} depth levels
          </p>
          <p>
            Timesteps: {data!.timesteps.count.toLocaleString()} hourly ({data!.timesteps.start.slice(0, 10)} &rarr; {data!.timesteps.end.slice(0, 10)})
          </p>
          <p style={styles.version}>metric_version: {data!.metric_version}</p>
        </section>

        <section style={styles.card}>
          <h2>Variables</h2>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={{ textAlign: 'left', paddingBottom: 8 }}>Name</th>
                <th style={{ textAlign: 'left', paddingBottom: 8 }}>Units</th>
                <th style={{ textAlign: 'left', paddingBottom: 8 }}>Description</th>
              </tr>
            </thead>
            <tbody>
              {data!.variables.map((v) => (
                <tr key={v.name}>
                  <td style={{ paddingBottom: 4 }}><code style={styles.code}>{v.name}</code></td>
                  <td style={{ paddingBottom: 4 }}>{v.units}</td>
                  <td style={{ paddingBottom: 4 }}>{v.description}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </section>

        <section style={styles.card}>
          <h2>Region Presets</h2>
          <ul>
            {Object.entries(data!.regions).map(([key, region]) => (
              <li key={key}>
                <strong>{key.replace(/_/g, ' ')}</strong>: lat [{region.lat[0]}, {region.lat[1]}], lon [{region.lon[0]}, {region.lon[1]}]
              </li>
            ))}
          </ul>
        </section>

        <section style={styles.cardMuted}>
          <h2>Week 1–2 milestones (next)</h2>
          <ul>
            <li>OpenVisus access verification for theta, salt, w</li>
            <li>Depth level &rarr; metres mapping confirmed</li>
            <li>Grid orientation verified with cartopy coastline overlay</li>
            <li>Small-ROI density prototype via TEOS-10 / gsw</li>
          </ul>
        </section>
      </main>
    </div>
  )
}
