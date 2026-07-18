import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { KeyRound, Loader2 } from 'lucide-react'
import { API_BASE } from '../config'
import type { CurrentUser } from '../types'

const SSO_ERROR_MESSAGES: Record<string, string> = {
  disabled: 'Ce compte SSO est désactivé.',
  oidc_failed: 'La connexion SSO a échoué. Réessayez.',
}

export function LoginPage({
  onLogin,
}: {
  onLogin: (token: string, user: CurrentUser) => void
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [ssoAvailable, setSsoAvailable] = useState(false)

  // Le bouton SSO n'apparait que si le backend expose oidc_enabled=true.
  useEffect(() => {
    fetch(`${API_BASE}/api/health`)
      .then((res) => res.json())
      .then((payload: { oidc_enabled?: boolean }) => setSsoAvailable(payload.oidc_enabled === true))
      .catch(() => setSsoAvailable(false))
  }, [])

  // Erreur remontee par le callback SSO dans le fragment (#sso_error=...).
  useEffect(() => {
    const match = window.location.hash.match(/sso_error=([^&]+)/)
    if (!match) return
    setError(SSO_ERROR_MESSAGES[match[1]] ?? 'La connexion SSO a échoué.')
    history.replaceState(null, '', window.location.pathname + window.location.search)
  }, [])

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setLoading(true)
    setError(null)

    try {
      const loginRes = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      })

      if (!loginRes.ok) {
        setError('Email ou mot de passe incorrect.')
        return
      }

      const { access_token } = (await loginRes.json()) as { access_token: string }
      localStorage.setItem('fabriq_token', access_token)

      const meRes = await fetch(`${API_BASE}/api/auth/me`, {
        headers: { Authorization: `Bearer ${access_token}` },
      })

      const user = (await meRes.json()) as CurrentUser
      onLogin(access_token, user)
    } catch {
      setError("Impossible de joindre l'API FabriQ.")
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-shell">
      <div className="login-card">
        <div className="brand-lockup">
          <span className="brand-mark">FQ</span>
          <div>
            <h1>FabriQ</h1>
            <p>Assistant NL - SQL industriel</p>
          </div>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <label>
            Email
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label>
            Mot de passe
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              autoComplete="current-password"
              required
            />
          </label>
          {error && <div className="notice error">{error}</div>}
          <button type="submit" disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : null}
            {loading ? 'Connexion...' : 'Se connecter'}
          </button>
        </form>

        {ssoAvailable && (
          <div className="sso-block">
            <div className="sso-divider">ou</div>
            <button
              type="button"
              className="sso-button"
              onClick={() => {
                window.location.href = `${API_BASE}/api/auth/oidc/login`
              }}
            >
              <KeyRound size={16} />
              Se connecter avec SSO
            </button>
          </div>
        )}
      </div>
    </main>
  )
}
