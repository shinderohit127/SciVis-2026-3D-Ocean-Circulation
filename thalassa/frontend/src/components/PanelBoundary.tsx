import React from 'react'

interface State { error: Error | null }

export default class PanelBoundary extends React.Component<
  { label: string; children: React.ReactNode },
  State
> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          width: '100%', height: '100%',
          display: 'flex', flexDirection: 'column',
          alignItems: 'center', justifyContent: 'center',
          background: '#060f1a', color: '#f04040', fontSize: 12, gap: 6, padding: 16,
        }}>
          <strong>{this.props.label} — render error</strong>
          <code style={{ color: '#6aaad4', fontSize: 11, wordBreak: 'break-all', textAlign: 'center' }}>
            {this.state.error.message}
          </code>
        </div>
      )
    }
    return this.props.children
  }
}
