import { Component, ReactNode } from 'react'

interface Props {
  children: ReactNode
}

interface State {
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  render() {
    if (this.state.error) {
      return (
        <div style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          minHeight: '100svh',
          gap: 16,
          padding: 32,
          fontFamily: 'system-ui, sans-serif',
          color: '#18202f',
          background: '#f6f7f9',
        }}>
          <div style={{ fontSize: 40 }}>⚠️</div>
          <h1 style={{ margin: 0, fontSize: 22 }}>Une erreur inattendue s'est produite</h1>
          <p style={{ margin: 0, color: '#64748b', textAlign: 'center' }}>
            Rechargez la page pour continuer. Si l'erreur persiste, contactez l'administrateur.
          </p>
          <pre style={{
            maxWidth: 560,
            padding: '12px 16px',
            background: '#fff',
            border: '1px solid #dde3ea',
            borderRadius: 8,
            fontSize: 12,
            overflowX: 'auto',
            color: '#e11d48',
          }}>
            {this.state.error.message}
          </pre>
          <button
            onClick={() => window.location.reload()}
            style={{
              padding: '10px 24px',
              background: '#1f6feb',
              color: '#fff',
              border: 'none',
              borderRadius: 8,
              cursor: 'pointer',
              fontWeight: 700,
              fontSize: 14,
            }}
          >
            Recharger
          </button>
        </div>
      )
    }
    return this.props.children
  }
}
