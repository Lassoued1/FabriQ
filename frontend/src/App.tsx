import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useToast } from './useToast'
import { ToastContainer } from './ToastContainer'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Bell,
  Clock3,
  Database,
  Layers3,
  Loader2,
  LogOut,
  MessageSquare,
  Plus,
  RefreshCw,
  Send,
  Server,
  ShieldCheck,
  Table2,
  Terminal,
  Trash2,
  User,
} from 'lucide-react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import './App.css'

// ─── Types ────────────────────────────────────────────────────────────────────

type CurrentUser = {
  email: string
  tenant_id: string
  role: string
}

type ChartSpec = {
  type: 'bar' | 'line' | 'area' | 'table'
  x: string
  y: string
  title: string
}

type ValidationReport = {
  ok: boolean
  checks: string[]
  blocked: string[]
}

type OrchestrationStep = {
  node: string
  status: 'done' | 'blocked' | 'skipped' | 'waiting'
  detail: string
}

type ClarificationOption = {
  intent_id: string
  label: string
  question: string
  reason: string
}

type AskResponse = {
  trace_id: string | null
  question: string
  intent: string | null
  routing_strategy: string
  llm_provider: string
  llm_reason: string | null
  orchestration: OrchestrationStep[]
  answer: string
  sql: string | null
  explanation: string
  columns: string[]
  rows: Record<string, string | number | null>[]
  chart: ChartSpec | null
  validation: ValidationReport
  needs_clarification: boolean
  clarification: string | null
  clarification_options: ClarificationOption[]
}

type HealthResponse = {
  status: string
  service: string
  database: string
  db_ok?: boolean
  db_latency_ms?: number | null
  version?: string
  llm_provider?: string
  llm_model?: string
  llm_mode?: string
  llm_status?: string
  llm_reachable?: boolean
  llm_model_available?: boolean | null
  llm_latency_ms?: number | null
  llm_error?: string | null
}

type AdminUser = {
  email: string
  tenant_id: string
  role: string
  disabled: boolean
}

type AuditEvent = {
  trace_id: string
  created_at: string
  question: string
  intent: string | null
  validation_ok: boolean
  needs_clarification: boolean
  row_count: number
  chart_type: string | null
  blocked: string[]
}

type CatalogIntent = {
  id: string
  label: string
  description: string
  keywords: string[]
  example_question: string
  chart: ChartSpec
}

type CatalogColumn = {
  name: string
  label: string
  description: string
}

type CatalogTable = {
  name: string
  label: string
  description: string
  columns: CatalogColumn[]
}

type CatalogResponse = {
  intents: CatalogIntent[]
  tables: CatalogTable[]
}

type CatalogTab = 'intents' | 'tables'

type AlertRule = {
  id: string
  name: string
  intent_id: string
  threshold_column: string
  threshold_value: number
  operator: 'gt' | 'lt' | 'gte' | 'lte'
  tenant_id: string
  cron: string
  enabled: boolean
  webhook_url?: string
  email_to?: string[]
  slack_webhook_url?: string
}

type AlertEvent = {
  rule_id: string
  rule_name: string
  fired_at: string
  tenant_id: string
  triggered_value: number
  rows_snapshot: Record<string, string | number | null>[]
}

// ─── Constants ────────────────────────────────────────────────────────────────

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000'
const APP_VERSION = 'v0.10.0'

const fallbackExamples = [
  'Quels produits ont vu leur marge baisser le trimestre dernier ?',
  'Quels fournisseurs ont ete le plus souvent en retard ?',
  "Montre le chiffre d'affaires mensuel par categorie.",
  'Quels SKU risquent une rupture dans les 14 prochains jours ?',
]

// ─── LoginPage ────────────────────────────────────────────────────────────────

function LoginPage({
  onLogin,
}: {
  onLogin: (token: string, user: CurrentUser) => void
}) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

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
      </div>
    </main>
  )
}

// ─── App ──────────────────────────────────────────────────────────────────────

function App() {
  const [authToken, setAuthToken] = useState<string | null>(
    () => localStorage.getItem('fabriq_token'),
  )
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)

  const [question, setQuestion] = useState(fallbackExamples[1])
  const [examples, setExamples] = useState(fallbackExamples)
  const [result, setResult] = useState<AskResponse | null>(null)
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [auditEvents, setAuditEvents] = useState<AuditEvent[]>([])
  const [catalog, setCatalog] = useState<CatalogResponse | null>(null)
  const [catalogTab, setCatalogTab] = useState<CatalogTab>('intents')
  const [loading, setLoading] = useState(false)
  const { toasts, addToast, dismiss } = useToast()
  const [opsLoading, setOpsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [opsError, setOpsError] = useState<string | null>(null)
  const [catalogError, setCatalogError] = useState<string | null>(null)
  const [auditPage, setAuditPage] = useState(1)
  const [auditTotal, setAuditTotal] = useState(0)
  const [auditFilterIntent, setAuditFilterIntent] = useState('')
  const [auditFilterStatus, setAuditFilterStatus] = useState<'' | 'ok' | 'failed'>('')
  const [adminUsers, setAdminUsers] = useState<AdminUser[]>([])
  const [alertRules, setAlertRules] = useState<AlertRule[]>([])
  const [alertEvents, setAlertEvents] = useState<AlertEvent[]>([])
  const [alertEventsTotal, setAlertEventsTotal] = useState(0)
  const [alertEventsPage, setAlertEventsPage] = useState(1)
  // alertsError is surfaced via toast; kept as state for backward compat
  const [alertsError, setAlertsError] = useState<string | null>(null)
  const bootstrapped = useRef(false)
  const [darkMode, setDarkMode] = useState<boolean>(
    () => localStorage.getItem('fabriq_dark') === '1'
  )

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', darkMode ? 'dark' : 'light')
    localStorage.setItem('fabriq_dark', darkMode ? '1' : '0')
  }, [darkMode])

  const visibleRows = useMemo(() => result?.rows.slice(0, 12) ?? [], [result])

  function authHeaders(extra: Record<string, string> = {}): HeadersInit {
    const base: Record<string, string> = { 'Content-Type': 'application/json', ...extra }
    if (authToken) base['Authorization'] = `Bearer ${authToken}`
    return base
  }

  function handleUnauthorized() {
    localStorage.removeItem('fabriq_token')
    setAuthToken(null)
    setCurrentUser(null)
    bootstrapped.current = false
  }

  function handleLogin(token: string, user: CurrentUser) {
    setAuthToken(token)
    setCurrentUser(user)
  }

  function handleLogout() {
    handleUnauthorized()
    setResult(null)
    setAuditEvents([])
    setHealth(null)
    setError(null)
  }

  // Resolve user info when authToken is present (e.g. after page reload)
  useEffect(() => {
    if (!authToken) {
      setCurrentUser(null)
      return
    }
    fetch(`${API_BASE}/api/auth/me`, {
      headers: { Authorization: `Bearer ${authToken}` },
    })
      .then(async (res) => {
        if (res.status === 401) { handleUnauthorized(); return }
        if (!res.ok) return
        setCurrentUser((await res.json()) as CurrentUser)
      })
      .catch(() => { /* network error — keep trying */ })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken])

  // Auto-refresh JWT 5 minutes before expiry (token lifetime = 60 min → refresh at 55 min)
  useEffect(() => {
    if (!authToken) return
    const REFRESH_INTERVAL_MS = 55 * 60 * 1000
    const id = window.setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/auth/refresh`, {
          method: 'POST',
          headers: { Authorization: `Bearer ${authToken}` },
        })
        if (res.status === 401) { handleUnauthorized(); return }
        if (!res.ok) return
        const { access_token } = (await res.json()) as { access_token: string }
        localStorage.setItem('fabriq_token', access_token)
        setAuthToken(access_token)
      } catch {
        // network error — will retry next interval
      }
    }, REFRESH_INTERVAL_MS)
    return () => window.clearInterval(id)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken])

  // Bootstrap: fetch examples and catalog once authenticated
  useEffect(() => {
    if (!authToken) return
    Promise.all([
      fetch(`${API_BASE}/api/examples`, { headers: authHeaders() }),
      fetch(`${API_BASE}/api/catalog`, { headers: authHeaders() }),
    ])
      .then(async ([examplesRes, catalogRes]) => {
        if (examplesRes.status === 401 || catalogRes.status === 401) {
          handleUnauthorized()
          return
        }
        if (!examplesRes.ok || !catalogRes.ok) throw new Error('bootstrap-unavailable')
        const payload = (await examplesRes.json()) as { questions?: string[] }
        const nextCatalog = (await catalogRes.json()) as CatalogResponse
        if (payload.questions?.length) setExamples(payload.questions)
        setCatalog(nextCatalog)
        setCatalogError(null)
      })
      .catch(() => {
        setExamples(fallbackExamples)
        setCatalog(null)
        setCatalogError('Catalogue indisponible')
      })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken])

  // Operational data: health + audit trail, refreshed every 15s
  useEffect(() => {
    if (!authToken) return
    void refreshOperationalData()
    const interval = window.setInterval(() => {
      void refreshOperationalData({ quiet: true })
    }, 15000)
    return () => window.clearInterval(interval)
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken])

  // Load alerts once per session
  useEffect(() => {
    if (!authToken) return
    void refreshAlerts()
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken])

  // Load admin users if role=admin
  useEffect(() => {
    if (!authToken || currentUser?.role !== 'admin') return
    fetch(`${API_BASE}/api/admin/users`, { headers: authHeaders() })
      .then((r) => r.json())
      .then((data: { users?: AdminUser[] }) => setAdminUsers(data.users ?? []))
      .catch(() => { /* non-critical */ })
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken, currentUser?.role])

  // Auto-run first example once per session
  useEffect(() => {
    if (!authToken) return
    if (bootstrapped.current) return
    bootstrapped.current = true
    void ask(fallbackExamples[1])
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authToken])

  async function ask(nextQuestion: string) {
    const trimmed = nextQuestion.trim()
    if (!trimmed) return

    setLoading(true)
    setError(null)
    setQuestion(trimmed)

    try {
      const response = await fetch(`${API_BASE}/api/ask`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify({ question: trimmed }),
      })

      if (response.status === 401) { handleUnauthorized(); return }
      if (response.status === 429) {
        addToast('Trop de requêtes — veuillez patienter quelques secondes.', 'error')
        return
      }
      if (!response.ok) throw new Error(`HTTP ${response.status}`)

      const payload = (await response.json()) as AskResponse
      setResult(payload)
      void refreshOperationalData({ quiet: true })
    } catch {
      setError("Impossible de joindre l'API FabriQ sur le port 8000.")
    } finally {
      setLoading(false)
    }
  }

  async function refreshOperationalData(options: { quiet?: boolean; page?: number; intent?: string; status?: string } = {}) {
    if (!options.quiet) setOpsLoading(true)
    const page = options.page ?? auditPage
    const intent = options.intent !== undefined ? options.intent : auditFilterIntent
    const status = options.status !== undefined ? options.status : auditFilterStatus

    const auditParams = new URLSearchParams({ page: String(page), limit: '10' })
    if (intent) auditParams.set('intent', intent)
    if (status === 'ok') auditParams.set('validation_ok', 'true')
    if (status === 'failed') auditParams.set('validation_ok', 'false')

    try {
      const [healthRes, auditRes] = await Promise.all([
        fetch(`${API_BASE}/api/health`),
        fetch(`${API_BASE}/api/audit/recent?${auditParams.toString()}`, { headers: authHeaders() }),
      ])

      if (auditRes.status === 401) { handleUnauthorized(); return }
      if (!healthRes.ok || !auditRes.ok) throw new Error('ops-unavailable')

      const nextHealth = (await healthRes.json()) as HealthResponse
      const auditPayload = (await auditRes.json()) as { events?: AuditEvent[]; total?: number; page?: number }
      setHealth(nextHealth)
      setAuditEvents(auditPayload.events ?? [])
      setAuditTotal(auditPayload.total ?? 0)
      setAuditPage(auditPayload.page ?? page)
      setOpsError(null)
    } catch {
      setHealth(null)
      setAuditEvents([])
      setOpsError('API indisponible')
    } finally {
      setOpsLoading(false)
    }
  }

  function handleAuditPageChange(newPage: number) {
    setAuditPage(newPage)
    void refreshOperationalData({ page: newPage })
  }

  function handleAuditFilterChange(intent: string, status: '' | 'ok' | 'failed') {
    setAuditFilterIntent(intent)
    setAuditFilterStatus(status)
    setAuditPage(1)
    void refreshOperationalData({ page: 1, intent, status })
  }

  async function refreshAlerts(eventsPage = alertEventsPage) {
    try {
      const [rulesRes, eventsRes] = await Promise.all([
        fetch(`${API_BASE}/api/alerts`, { headers: authHeaders() }),
        fetch(`${API_BASE}/api/alerts/events?page=${eventsPage}&limit=10`, { headers: authHeaders() }),
      ])
      if (rulesRes.status === 401 || eventsRes.status === 401) { handleUnauthorized(); return }
      if (!rulesRes.ok || !eventsRes.ok) throw new Error('alerts-unavailable')
      const { rules } = (await rulesRes.json()) as { rules: AlertRule[] }
      const payload = (await eventsRes.json()) as { events: AlertEvent[]; total?: number; page?: number }
      setAlertRules(rules)
      setAlertEvents(payload.events ?? [])
      setAlertEventsTotal(payload.total ?? 0)
      setAlertEventsPage(payload.page ?? eventsPage)
      setAlertsError(null)
    } catch {
      setAlertsError('Alertes indisponibles')
    }
  }

  function handleAlertEventsPageChange(newPage: number) {
    setAlertEventsPage(newPage)
    void refreshAlerts(newPage)
  }

  async function handleToggleUser(email: string, disable: boolean) {
    const action = disable ? 'disable' : 'enable'
    try {
      const res = await fetch(`${API_BASE}/api/admin/users/${encodeURIComponent(email)}/${action}`, {
        method: 'POST',
        headers: authHeaders(),
      })
      if (res.status === 401) { handleUnauthorized(); return }
      if (!res.ok) { addToast(`Impossible de ${disable ? 'désactiver' : 'réactiver'} ${email}.`, 'error'); return }
      setAdminUsers((prev) => prev.map((u) => u.email === email ? { ...u, disabled: disable } : u))
      addToast(`${email} ${disable ? 'désactivé' : 'réactivé'}.`, 'success')
    } catch {
      addToast('Erreur réseau.', 'error')
    }
  }

  async function createAlert(draft: Omit<AlertRule, 'id' | 'tenant_id'>) {
    try {
      const res = await fetch(`${API_BASE}/api/alerts`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(draft),
      })
      if (res.status === 401) { handleUnauthorized(); return }
      if (!res.ok) { addToast("Impossible de créer l'alerte.", 'error'); return }
      await refreshAlerts()
      addToast('Alerte créée.', 'success')
    } catch {
      addToast("Impossible de créer l'alerte.", 'error')
    }
  }

  async function deleteAlert(ruleId: string) {
    try {
      const res = await fetch(`${API_BASE}/api/alerts/${ruleId}`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (res.status === 401) { handleUnauthorized(); return }
      await refreshAlerts()
      addToast('Alerte supprimée.', 'success')
    } catch {
      addToast("Impossible de supprimer l'alerte.", 'error')
    }
  }

  async function handleExportXlsx() {
    try {
      const res = await fetch(`${API_BASE}/api/audit/export.xlsx`, { headers: authHeaders() })
      if (res.status === 401) { handleUnauthorized(); return }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'audit.xlsx'
      a.click()
      URL.revokeObjectURL(url)
      addToast('Export Excel téléchargé.', 'success')
    } catch {
      addToast("Erreur lors de l'export Excel.", 'error')
    }
  }

  async function handleExportCsv() {
    try {
      const res = await fetch(`${API_BASE}/api/audit/export`, { headers: authHeaders() })
      if (res.status === 401) { handleUnauthorized(); return }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'audit.csv'
      a.click()
      URL.revokeObjectURL(url)
      addToast('Export audit téléchargé.', 'success')
    } catch {
      addToast('Erreur lors de l\'export.', 'error')
    }
  }

  async function handleExportAlertsCsv() {
    try {
      const res = await fetch(`${API_BASE}/api/alerts/events/export`, { headers: authHeaders() })
      if (res.status === 401) { handleUnauthorized(); return }
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = 'alert_events.csv'
      a.click()
      URL.revokeObjectURL(url)
      addToast('Export alertes téléchargé.', 'success')
    } catch {
      addToast("Erreur lors de l'export.", 'error')
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void ask(question)
  }

  if (!authToken) {
    return <LoginPage onLogin={handleLogin} />
  }

  return (
    <>
    <main className="app-shell">
      <header className="topbar">
        <div className="brand-lockup">
          <span className="brand-mark">FQ</span>
          <div>
            <h1>FabriQ</h1>
            <p>Assistant NL - SQL industriel</p>
          </div>
        </div>
        <div className="status-strip">
          <span>
            <Server size={16} />
            {health?.status === 'ok' ? 'API ok' : 'API'}
          </span>
          <span>
            <Database size={16} />
            {health?.database ?? 'database'}
          </span>
          <span>
            <ShieldCheck size={16} />
            Read-only
          </span>
          <span>
            <Activity size={16} />
            {formatLlmStatus(health)}
          </span>
          <span>{health?.version ?? APP_VERSION}</span>
          {currentUser && (
            <span className="tenant-badge" title={`role: ${currentUser.role}`}>
              <User size={14} />
              {currentUser.tenant_id}
            </span>
          )}
          <button
            type="button"
            className="dark-toggle"
            onClick={() => setDarkMode((d) => !d)}
            title={darkMode ? 'Passer en mode clair' : 'Passer en mode sombre'}
            aria-pressed={darkMode}
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
          <button
            type="button"
            className="logout-btn"
            onClick={handleLogout}
            title="Se déconnecter"
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>

      <section className="workspace">
        <aside className="query-panel">
          <div className="panel-heading">
            <MessageSquare size={18} />
            <h2>Question</h2>
          </div>

          <form onSubmit={handleSubmit} className="question-form">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={6}
              aria-label="Question en langage naturel"
            />
            <button type="submit" disabled={loading}>
              {loading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
              Analyser
            </button>
          </form>

          <div className="examples-list">
            {examples.slice(0, 10).map((example) => (
              <button key={example} type="button" onClick={() => void ask(example)}>
                {example}
              </button>
            ))}
          </div>

          <ObservabilityPanel
            events={auditEvents}
            health={health}
            loading={opsLoading}
            error={opsError}
            onRefresh={() => void refreshOperationalData()}
            onExportCsv={() => void handleExportCsv()}
            onExportXlsx={() => void handleExportXlsx()}
            page={auditPage}
            total={auditTotal}
            pageSize={10}
            onPageChange={handleAuditPageChange}
            filterIntent={auditFilterIntent}
            filterStatus={auditFilterStatus}
            onFilterChange={handleAuditFilterChange}
          />

          <SemanticCatalogPanel
            catalog={catalog}
            activeTab={catalogTab}
            error={catalogError}
            onSelectTab={setCatalogTab}
            onAsk={(nextQuestion) => void ask(nextQuestion)}
          />

          <AlertsPanel
            rules={alertRules}
            events={alertEvents}
            eventsTotal={alertEventsTotal}
            eventsPage={alertEventsPage}
            error={alertsError}
            onRefresh={() => void refreshAlerts()}
            onDelete={(id) => void deleteAlert(id)}
            onCreateAlert={(draft) => void createAlert(draft)}
            onExportEvents={() => void handleExportAlertsCsv()}
            onEventsPageChange={handleAlertEventsPageChange}
          />

          {currentUser?.role === 'admin' && (
            <AdminPanel users={adminUsers} onToggleUser={(email, disable) => void handleToggleUser(email, disable)} />
          )}
        </aside>

        <section className="result-panel">
          <div className="metric-row">
            <div className="metric">
              <Activity size={18} />
              <span>{result?.intent ?? 'En attente'}</span>
            </div>
            <div className={result?.validation.ok ? 'metric ok' : 'metric'}>
              {result?.validation.ok ? <ShieldCheck size={18} /> : <AlertTriangle size={18} />}
              <span>{result?.validation.ok ? 'SQL valide' : 'Validation'}</span>
            </div>
            <div className="metric">
              <Table2 size={18} />
              <span>{result ? `${result.rows.length} lignes` : '0 ligne'}</span>
            </div>
            <div className="metric">
              <Activity size={18} />
              <span>{result?.routing_strategy ?? 'routing'}</span>
            </div>
          </div>

          {error && <div className="notice error">{error}</div>}

          {!result && !error && (
            <div className="empty-state">
              <BarChart3 size={42} />
              <p>Pose une question industrielle pour lancer la boucle FabriQ.</p>
            </div>
          )}

          {result && (
            <div className="analysis-grid">
              <div className="export-bar">
                <button
                  type="button"
                  className="export-pdf-btn"
                  onClick={() => window.print()}
                  title="Exporter l'analyse en PDF"
                >
                  Exporter PDF
                </button>
              </div>

              <section className="answer-block">
                <h2>Reponse</h2>
                <p>{result.answer}</p>
                {result.needs_clarification && result.clarification && (
                  <div className="notice">{result.clarification}</div>
                )}
                {result.needs_clarification && result.clarification_options.length > 0 && (
                  <div className="clarification-options">
                    {result.clarification_options.map((option) => (
                      <button
                        key={option.intent_id}
                        type="button"
                        onClick={() => void ask(option.question)}
                        title={option.reason}
                      >
                        <strong>{option.label}</strong>
                        <span>{option.question}</span>
                      </button>
                    ))}
                  </div>
                )}
                <p className="explanation">{result.explanation}</p>
                {result.llm_reason && <p className="explanation">LLM: {result.llm_reason}</p>}
              </section>

              <section className="orchestration-block">
                <div className="section-title">
                  <Activity size={18} />
                  <h2>Pipeline</h2>
                </div>
                <OrchestrationTimeline steps={result.orchestration} />
              </section>

              <section className="chart-block">
                <div className="section-title">
                  <BarChart3 size={18} />
                  <h2>{result.chart?.title ?? 'Graphique'}</h2>
                </div>
                <ResultChart result={result} data={visibleRows} />
              </section>

              <section className="table-block">
                <div className="section-title">
                  <Table2 size={18} />
                  <h2>Resultats</h2>
                </div>
                <ResultTable columns={result.columns} rows={visibleRows} />
              </section>

              <section className="sql-block">
                <div className="section-title">
                  <Terminal size={18} />
                  <h2>SQL</h2>
                </div>
                <pre>{result.sql ?? 'Aucune requete generee.'}</pre>
                {result.trace_id && <p className="trace-id">Trace: {result.trace_id}</p>}
                <ValidationList validation={result.validation} />
              </section>
            </div>
          )}
        </section>
      </section>
    </main>

    <ToastContainer toasts={toasts} onDismiss={dismiss} />
    </>
  )
}

// ─── Sub-components (unchanged) ───────────────────────────────────────────────

function SemanticCatalogPanel({
  catalog,
  activeTab,
  error,
  onSelectTab,
  onAsk,
}: {
  catalog: CatalogResponse | null
  activeTab: CatalogTab
  error: string | null
  onSelectTab: (tab: CatalogTab) => void
  onAsk: (question: string) => void
}) {
  return (
    <section className="catalog-panel">
      <div className="panel-heading compact">
        <Layers3 size={18} />
        <h2>Catalogue</h2>
      </div>

      <div className="catalog-tabs" role="tablist" aria-label="Catalogue semantique">
        <button
          type="button"
          className={activeTab === 'intents' ? 'active' : undefined}
          onClick={() => onSelectTab('intents')}
        >
          Intentions
        </button>
        <button
          type="button"
          className={activeTab === 'tables' ? 'active' : undefined}
          onClick={() => onSelectTab('tables')}
        >
          Tables
        </button>
      </div>

      {error && <div className="ops-error">{error}</div>}
      {!catalog && !error && <div className="catalog-empty">Chargement...</div>}

      {catalog && activeTab === 'intents' && (
        <div className="catalog-list">
          {catalog.intents.map((intent) => (
            <article key={intent.id} className="catalog-item">
              <div className="catalog-item-title">
                <strong>{intent.label}</strong>
                <span>{intent.chart.type}</span>
              </div>
              <p>{intent.description}</p>
              <div className="keyword-row">
                {intent.keywords.slice(0, 5).map((keyword) => (
                  <span key={keyword}>{keyword}</span>
                ))}
              </div>
              <button type="button" onClick={() => onAsk(intent.example_question)}>
                {intent.example_question}
              </button>
            </article>
          ))}
        </div>
      )}

      {catalog && activeTab === 'tables' && (
        <div className="catalog-list">
          {catalog.tables.map((table) => (
            <article key={table.name} className="catalog-item">
              <div className="catalog-item-title">
                <strong>{table.label}</strong>
                <span>{table.columns.length} colonnes</span>
              </div>
              <p>{table.description}</p>
              <div className="column-list">
                {table.columns.slice(0, 6).map((column) => (
                  <span key={column.name} title={column.description}>
                    {column.name}
                  </span>
                ))}
              </div>
            </article>
          ))}
        </div>
      )}
    </section>
  )
}

const AUDIT_INTENTS = [
  { id: '', label: 'Toutes intentions' },
  { id: 'margin_trend', label: 'Tendance marge' },
  { id: 'stockout_risk', label: 'Rupture stock' },
  { id: 'supplier_delays', label: 'Retards fournisseur' },
  { id: 'production_efficiency', label: 'Efficacite prod.' },
  { id: 'revenue_trend', label: 'Tendance CA' },
  { id: 'stock_aging', label: 'Vieillissement stock' },
  { id: 'logistics_cost', label: 'Cout logistique' },
  { id: 'returns_rate', label: 'Retours' },
  { id: 'customer_concentration', label: 'Clients' },
  { id: 'anomaly_detection', label: 'Anomalie' },
]

function ObservabilityPanel({
  events,
  health,
  loading,
  error,
  onRefresh,
  onExportCsv,
  onExportXlsx,
  page,
  total,
  pageSize,
  onPageChange,
  filterIntent,
  filterStatus,
  onFilterChange,
}: {
  events: AuditEvent[]
  health: HealthResponse | null
  loading: boolean
  error: string | null
  onRefresh: () => void
  onExportCsv: () => void
  onExportXlsx: () => void
  page: number
  total: number
  pageSize: number
  onPageChange: (p: number) => void
  filterIntent: string
  filterStatus: '' | 'ok' | 'failed'
  onFilterChange: (intent: string, status: '' | 'ok' | 'failed') => void
}) {
  const latest = events[0]
  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  return (
    <section className="observability-panel">
      <div className="panel-heading compact">
        <Activity size={18} />
        <h2>Observabilite</h2>
        <button type="button" onClick={onRefresh} aria-label="Rafraichir">
          <RefreshCw className={loading ? 'spin' : undefined} size={16} />
        </button>
        <button type="button" onClick={onExportCsv} className="export-btn" title="Exporter en CSV">
          CSV ↓
        </button>
        <button type="button" onClick={onExportXlsx} className="export-btn" title="Exporter en Excel">
          XLSX ↓
        </button>
      </div>

      <div className="ops-grid">
        <div className={health?.status === 'ok' ? 'ops-pill ok' : 'ops-pill'}>
          <Server size={15} />
          {health?.service ?? 'API'}
        </div>
        <div className="ops-pill">
          <Database size={15} />
          {health?.database ?? 'inconnue'}
        </div>
        <div className={llmPillClass(health)} title={health?.llm_error ?? undefined}>
          <Activity size={15} />
          {formatLlmStatus(health)}
        </div>
        <div className="ops-pill">
          <Clock3 size={15} />
          {formatLlmLatency(health)}
        </div>
      </div>

      <div className="audit-filters">
        <select
          value={filterIntent}
          onChange={(e) => onFilterChange(e.target.value, filterStatus)}
          aria-label="Filtrer par intention"
        >
          {AUDIT_INTENTS.map((opt) => (
            <option key={opt.id} value={opt.id}>{opt.label}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => onFilterChange(filterIntent, e.target.value as '' | 'ok' | 'failed')}
          aria-label="Filtrer par statut"
        >
          <option value="">Tous statuts</option>
          <option value="ok">Valides</option>
          <option value="failed">Bloques</option>
        </select>
      </div>

      {error && <div className="ops-error">{error}</div>}

      {latest && (
        <div className="latest-trace">
          <span>Derniere trace</span>
          <strong>{latest.trace_id}</strong>
        </div>
      )}

      <div className="audit-list">
        {events.map((event) => (
          <article key={event.trace_id} className="audit-item">
            <div>
              <span className={event.validation_ok ? 'audit-dot ok' : 'audit-dot blocked'} />
              <strong>{event.intent ?? 'clarification'}</strong>
            </div>
            <p>{event.question}</p>
            <footer>
              <span>
                <Clock3 size={13} />
                {formatTime(event.created_at)}
              </span>
              <span>{event.row_count} lignes</span>
            </footer>
          </article>
        ))}
        {!events.length && !error && <div className="audit-empty">Aucune trace recente.</div>}
      </div>

      {totalPages > 1 && (
        <div className="audit-pagination">
          <button
            type="button"
            disabled={page <= 1}
            onClick={() => onPageChange(page - 1)}
          >
            ‹
          </button>
          <span>{page} / {totalPages}</span>
          <button
            type="button"
            disabled={page >= totalPages}
            onClick={() => onPageChange(page + 1)}
          >
            ›
          </button>
        </div>
      )}
    </section>
  )
}

function ResultChart({
  result,
  data,
}: {
  result: AskResponse
  data: AskResponse['rows']
}) {
  if (!result.chart || data.length === 0) {
    return <div className="chart-empty">Aucune donnee graphique.</div>
  }

  const chartProps = {
    data,
    margin: { top: 8, right: 12, bottom: 20, left: 0 },
  }

  if (result.chart.type === 'line') {
    return (
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart {...chartProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={result.chart.x} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} width={48} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey={result.chart.y}
              stroke="#1f6feb"
              strokeWidth={2}
              dot={{ r: 3 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }

  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart {...chartProps}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={result.chart.x} tick={{ fontSize: 12 }} interval={0} />
          <YAxis tick={{ fontSize: 12 }} width={48} />
          <Tooltip />
          <Bar
            dataKey={result.chart.y}
            fill="#0f9f6e"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

function ResultTable({
  columns,
  rows,
}: {
  columns: string[]
  rows: AskResponse['rows']
}) {
  if (!columns.length || !rows.length) {
    return <div className="table-empty">Aucune ligne.</div>
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${index}-${columns[0]}`}>
              {columns.map((column) => (
                <td key={column}>{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function OrchestrationTimeline({ steps }: { steps: OrchestrationStep[] }) {
  if (!steps.length) {
    return <div className="timeline-empty">Aucune trace de pipeline.</div>
  }

  return (
    <div className="timeline-list">
      {steps.map((step, index) => (
        <article key={`${step.node}-${index}`} className={`timeline-step ${step.status}`}>
          <span className="timeline-dot" />
          <div>
            <strong>{formatNode(step.node)}</strong>
            <p>{step.detail}</p>
          </div>
          <span className="timeline-status">{step.status}</span>
        </article>
      ))}
    </div>
  )
}

function ValidationList({ validation }: { validation: ValidationReport }) {
  return (
    <div className="validation-list">
      {validation.checks.map((check) => (
        <span key={check} className="check ok">
          {check}
        </span>
      ))}
      {validation.blocked.map((blocked) => (
        <span key={blocked} className="check blocked">
          {blocked}
        </span>
      ))}
    </div>
  )
}

// ─── AlertsPanel ─────────────────────────────────────────────────────────────

function AlertsPanel({
  rules,
  events,
  eventsTotal,
  eventsPage,
  error,
  onRefresh,
  onDelete,
  onCreateAlert,
  onExportEvents,
  onEventsPageChange,
}: {
  rules: AlertRule[]
  events: AlertEvent[]
  eventsTotal: number
  eventsPage: number
  error: string | null
  onRefresh: () => void
  onDelete: (id: string) => void
  onCreateAlert: (draft: Omit<AlertRule, 'id' | 'tenant_id'>) => void
  onExportEvents: () => void
  onEventsPageChange: (p: number) => void
}) {
  const [showForm, setShowForm] = useState(false)
  const [formName, setFormName] = useState('')
  const [formIntentId, setFormIntentId] = useState('supplier_delays')
  const [formColumn, setFormColumn] = useState('avg_delay_days')
  const [formValue, setFormValue] = useState('3')
  const [formOp, setFormOp] = useState<AlertRule['operator']>('gt')
  const [formCron, setFormCron] = useState('0 8 * * *')
  const [formWebhook, setFormWebhook] = useState('')
  const [formSlack, setFormSlack] = useState('')
  const [formEmail, setFormEmail] = useState('')

  const INTENT_OPTIONS = [
    { id: 'supplier_delays', label: 'Retards fournisseurs', column: 'avg_delay_days' },
    { id: 'stockout_risk', label: 'Risque rupture', column: 'days_of_coverage' },
    { id: 'margin_trend', label: 'Tendance marge', column: 'margin' },
    { id: 'returns_rate', label: 'Taux retours', column: 'return_rate_pct' },
    { id: 'anomaly_detection', label: 'Anomalie stock', column: 'variance_from_avg' },
  ]

  function handleCreate(e: React.FormEvent) {
    e.preventDefault()
    if (!formName.trim()) return
    onCreateAlert({
      name: formName.trim(),
      intent_id: formIntentId,
      threshold_column: formColumn,
      threshold_value: parseFloat(formValue) || 0,
      operator: formOp,
      cron: formCron,
      enabled: true,
      webhook_url: formWebhook.trim() || undefined,
      slack_webhook_url: formSlack.trim() || undefined,
      email_to: formEmail.trim() ? formEmail.split(',').map(e => e.trim()).filter(Boolean) : undefined,
    })
    setShowForm(false)
    setFormName('')
    setFormWebhook('')
    setFormSlack('')
    setFormEmail('')
  }

  return (
    <section className="alerts-panel">
      <div className="panel-heading compact">
        <Bell size={18} />
        <h2>Alertes</h2>
        <button type="button" onClick={onRefresh} aria-label="Rafraichir">
          <RefreshCw size={16} />
        </button>
        <button type="button" onClick={onExportEvents} className="export-btn" title="Exporter evenements CSV">
          CSV ↓
        </button>
        <button type="button" onClick={() => setShowForm((v) => !v)} aria-label="Nouvelle alerte">
          <Plus size={16} />
        </button>
      </div>

      {error && <div className="ops-error">{error}</div>}

      {showForm && (
        <form className="alert-form" onSubmit={handleCreate}>
          <input
            placeholder="Nom de l'alerte"
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            required
          />
          <select
            value={formIntentId}
            onChange={(e) => {
              const opt = INTENT_OPTIONS.find((o) => o.id === e.target.value)
              setFormIntentId(e.target.value)
              if (opt) setFormColumn(opt.column)
            }}
          >
            {INTENT_OPTIONS.map((o) => (
              <option key={o.id} value={o.id}>{o.label}</option>
            ))}
          </select>
          <div className="alert-form-row">
            <select value={formOp} onChange={(e) => setFormOp(e.target.value as AlertRule['operator'])}>
              <option value="gt">&gt; supérieur à</option>
              <option value="lt">&lt; inférieur à</option>
              <option value="gte">≥ supérieur ou égal</option>
              <option value="lte">≤ inférieur ou égal</option>
            </select>
            <input
              type="number"
              value={formValue}
              onChange={(e) => setFormValue(e.target.value)}
              style={{ width: 80 }}
            />
          </div>
          <input
            placeholder="Cron (ex: 0 8 * * *)"
            value={formCron}
            onChange={(e) => setFormCron(e.target.value)}
          />
          <input
            placeholder="Webhook URL (optionnel)"
            type="url"
            value={formWebhook}
            onChange={(e) => setFormWebhook(e.target.value)}
          />
          <input
            placeholder="Slack Webhook URL (optionnel)"
            type="url"
            value={formSlack}
            onChange={(e) => setFormSlack(e.target.value)}
          />
          <input
            placeholder="Emails destinataires (optionnel, séparés par virgule)"
            type="text"
            value={formEmail}
            onChange={(e) => setFormEmail(e.target.value)}
          />
          <button type="submit">Créer</button>
        </form>
      )}

      <div className="alert-rules-list">
        {rules.length === 0 && !error && (
          <div className="audit-empty">Aucune règle. Cliquez sur + pour en créer une.</div>
        )}
        {rules.map((rule) => (
          <article key={rule.id} className="alert-rule-item">
            <div className="alert-rule-header">
              <span className={rule.enabled ? 'audit-dot ok' : 'audit-dot'} />
              <strong>{rule.name}</strong>
              <button type="button" onClick={() => onDelete(rule.id)} title="Supprimer">
                <Trash2 size={13} />
              </button>
            </div>
            <p className="alert-rule-desc">
              {rule.intent_id} · {rule.threshold_column} {rule.operator} {rule.threshold_value}
            </p>
            <p className="alert-rule-cron">⏱ {rule.cron}</p>
          </article>
        ))}
      </div>

      <div className="alert-events-list">
        <p className="alert-events-title">Declenchements ({eventsTotal})</p>
        {events.length === 0 && (
          <div className="audit-empty">Aucun evenement.</div>
        )}
        {events.map((ev, i) => (
          <article key={`${ev.rule_id}-${i}`} className="alert-event-item">
            <strong>{ev.rule_name}</strong>
            <span>valeur: {ev.triggered_value.toFixed(2)}</span>
            <span>{formatTime(ev.fired_at)}</span>
          </article>
        ))}
        {eventsTotal > 10 && (() => {
          const totalPages = Math.ceil(eventsTotal / 10)
          return (
            <div className="audit-pagination">
              <button type="button" disabled={eventsPage <= 1} onClick={() => onEventsPageChange(eventsPage - 1)}>‹</button>
              <span>{eventsPage} / {totalPages}</span>
              <button type="button" disabled={eventsPage >= totalPages} onClick={() => onEventsPageChange(eventsPage + 1)}>›</button>
            </div>
          )
        })()}
      </div>
    </section>
  )
}

// ─── Formatters ───────────────────────────────────────────────────────────────

function formatNode(value: string) {
  return value.replaceAll('_', ' ')
}

function formatLlmStatus(health: HealthResponse | null) {
  if (!health) return 'LLM'
  if (health.llm_status === 'ready') return 'LLM ready'
  if (health.llm_status === 'model_missing') return 'Model missing'
  if (health.llm_status === 'unreachable') return 'LLM unreachable'
  if (health.llm_status === 'disabled' || health.llm_mode === 'disabled') return 'LLM off'
  return health.llm_mode === 'optional-router' ? 'LLM optional' : 'LLM'
}

function formatLlmLatency(health: HealthResponse | null) {
  if (!health) return 'LLM --'
  if (health.llm_status === 'disabled') return 'LLM off'
  if (typeof health.llm_latency_ms === 'number') return `${health.llm_latency_ms} ms`
  return 'LLM --'
}

function llmPillClass(health: HealthResponse | null) {
  if (health?.llm_status === 'ready') return 'ops-pill ok'
  if (health?.llm_status === 'model_missing') return 'ops-pill warning'
  if (health?.llm_status === 'unreachable') return 'ops-pill blocked'
  return 'ops-pill'
}

function formatCell(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') return new Intl.NumberFormat('fr-FR').format(value)
  return value
}

function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--:--'
  return new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' }).format(date)
}

// ─── AdminPanel ───────────────────────────────────────────────────────────────

function AdminPanel({
  users,
  onToggleUser,
}: {
  users: AdminUser[]
  onToggleUser: (email: string, disable: boolean) => void
}) {
  return (
    <section className="admin-panel">
      <div className="panel-heading compact">
        <User size={18} />
        <h2>Utilisateurs ({users.length})</h2>
      </div>
      {users.length === 0 ? (
        <div className="audit-empty">Aucun utilisateur charge.</div>
      ) : (
        <table className="admin-table">
          <thead>
            <tr>
              <th>Email</th>
              <th>Tenant</th>
              <th>Role</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {users.map((u) => (
              <tr key={u.email} className={u.disabled ? 'admin-row-disabled' : ''}>
                <td>{u.email}</td>
                <td><span className="tenant-badge" style={{ fontSize: '0.75rem' }}>{u.tenant_id}</span></td>
                <td><span className={`role-badge ${u.role}`}>{u.role}</span></td>
                <td>
                  <button
                    type="button"
                    className={u.disabled ? 'admin-toggle-btn enable' : 'admin-toggle-btn disable'}
                    onClick={() => onToggleUser(u.email, !u.disabled)}
                    title={u.disabled ? 'Réactiver' : 'Désactiver'}
                  >
                    {u.disabled ? 'Activer' : 'Désactiver'}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  )
}

export default App
