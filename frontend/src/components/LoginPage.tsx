import { useEffect, useState } from 'react'
import type { FormEvent } from 'react'
import { KeyRound, Loader2 } from 'lucide-react'
import { API_BASE } from '../config'
import type { CurrentUser } from '../types'
import { useLang } from '../i18n'
import type { Lang } from '../i18n'

export function LoginPage({
  onLogin,
}: {
  onLogin: (token: string, user: CurrentUser) => void
}) {
  const { lang, setLang, t } = useLang()
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
    setError(match[1] === 'disabled' ? t.login.ssoDisabled : t.login.ssoFailed)
    history.replaceState(null, '', window.location.pathname + window.location.search)
    // Le message suit la langue courante ; ne relance pas au changement de langue.
    // eslint-disable-next-line react-hooks/exhaustive-deps
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
        setError(t.login.badCredentials)
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
      setError(t.login.apiUnreachable)
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="login-shell">
      <div className="login-card">
        <div className="login-topline">
          <div className="brand-lockup">
            <span className="brand-mark">FQ</span>
            <div>
              <h1>FabriQ</h1>
              <p>{t.login.subtitle}</p>
            </div>
          </div>
          <div className="lang-toggle" role="group" aria-label={t.header.langAria}>
            {(['fr', 'en', 'de'] as Lang[]).map((code) => (
              <button
                key={code}
                type="button"
                className={lang === code ? 'active' : undefined}
                aria-pressed={lang === code}
                onClick={() => setLang(code)}
              >
                {code.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="login-form">
          <label>
            {t.login.email}
            <input
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              autoComplete="email"
              required
            />
          </label>
          <label>
            {t.login.password}
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
            {loading ? t.login.submitting : t.login.submit}
          </button>
        </form>

        {ssoAvailable && (
          <div className="sso-block">
            <div className="sso-divider">{t.login.ssoOr}</div>
            <button
              type="button"
              className="sso-button"
              onClick={() => {
                window.location.href = `${API_BASE}/api/auth/oidc/login`
              }}
            >
              <KeyRound size={16} />
              {t.login.ssoButton}
            </button>
          </div>
        )}
      </div>
    </main>
  )
}
