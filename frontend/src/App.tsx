import { useEffect, useMemo, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useToast } from './useToast'
import { ToastContainer } from './ToastContainer'
import {
  Activity,
  AlertTriangle,
  BarChart3,
  Database,
  Loader2,
  LogOut,
  MessageSquare,
  Send,
  Server,
  ShieldCheck,
  Table2,
  Terminal,
  User,
} from 'lucide-react'
import './App.css'
import type {
  AdminUser,
  AlertEvent,
  AlertRule,
  AskResponse,
  AuditEvent,
  CatalogResponse,
  CatalogTab,
  CurrentUser,
  HealthResponse,
  WebhookDelivery,
  WebhookSubscription,
} from './types'
import { API_BASE, APP_VERSION, examplesByLang, fallbackExamples } from './config'
import { useLang } from './i18n'
import type { Lang } from './i18n'
import { formatLlmStatus } from './format'
import { LoginPage } from './components/LoginPage'
import { SemanticCatalogPanel } from './components/SemanticCatalogPanel'
import { ObservabilityPanel } from './components/ObservabilityPanel'
import { ResultChart } from './components/ResultChart'
import { ResultTable } from './components/ResultTable'
import { OrchestrationTimeline } from './components/OrchestrationTimeline'
import { ValidationList } from './components/ValidationList'
import { AlertsPanel } from './components/AlertsPanel'
import { WebhooksPanel } from './components/WebhooksPanel'
import { AdminPanel } from './components/AdminPanel'

// ─── App ──────────────────────────────────────────────────────────────────────

function App() {
  const [authToken, setAuthToken] = useState<string | null>(
    () => localStorage.getItem('fabriq_token'),
  )
  const [currentUser, setCurrentUser] = useState<CurrentUser | null>(null)

  const { lang, setLang, t } = useLang()
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
  const [webhooks, setWebhooks] = useState<WebhookSubscription[]>([])
  const [webhookEventTypes, setWebhookEventTypes] = useState<string[]>([])
  const [webhookDeliveries, setWebhookDeliveries] = useState<Record<string, WebhookDelivery[]>>({})
  const [webhooksError, setWebhooksError] = useState<string | null>(null)
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
        setCatalogError(t.errors.catalog)
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

  // Load webhooks + event types once per session
  useEffect(() => {
    if (!authToken) return
    void refreshWebhooks()
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
        addToast(t.toasts.rateLimit, 'error')
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
      setOpsError(t.errors.api)
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
      setAlertsError(t.errors.alerts)
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
      if (!res.ok) { addToast(t.toasts.userToggleFail(email, disable), 'error'); return }
      setAdminUsers((prev) => prev.map((u) => u.email === email ? { ...u, disabled: disable } : u))
      addToast(t.toasts.userToggled(email, disable), 'success')
    } catch {
      addToast(t.toasts.networkError, 'error')
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
      if (!res.ok) { addToast(t.toasts.alertCreateFail, 'error'); return }
      await refreshAlerts()
      addToast(t.toasts.alertCreated, 'success')
    } catch {
      addToast(t.toasts.alertCreateFail, 'error')
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
      addToast(t.toasts.alertDeleted, 'success')
    } catch {
      addToast(t.toasts.alertDeleteFail, 'error')
    }
  }

  async function refreshWebhooks() {
    try {
      const [hooksRes, typesRes] = await Promise.all([
        fetch(`${API_BASE}/api/webhooks`, { headers: authHeaders() }),
        fetch(`${API_BASE}/api/webhooks/event-types`, { headers: authHeaders() }),
      ])
      if (hooksRes.status === 401 || typesRes.status === 401) { handleUnauthorized(); return }
      if (!hooksRes.ok || !typesRes.ok) throw new Error('webhooks-unavailable')
      const { webhooks: hooks } = (await hooksRes.json()) as { webhooks: WebhookSubscription[] }
      const { event_types } = (await typesRes.json()) as { event_types: string[] }
      setWebhooks(hooks)
      setWebhookEventTypes(event_types)
      setWebhooksError(null)
    } catch {
      setWebhooksError(t.errors.webhooks)
    }
  }

  async function createWebhook(draft: { name: string; url: string; events: string[] }) {
    try {
      const res = await fetch(`${API_BASE}/api/webhooks`, {
        method: 'POST',
        headers: authHeaders(),
        body: JSON.stringify(draft),
      })
      if (res.status === 401) { handleUnauthorized(); return }
      if (!res.ok) {
        const detail = res.status === 400
          ? 'URL non autorisée (adresse interne ou schéma invalide).'
          : "Impossible de créer le webhook."
        addToast(detail, 'error')
        return
      }
      await refreshWebhooks()
      addToast(t.toasts.webhookCreated, 'success')
    } catch {
      addToast(t.toasts.webhookCreateFail, 'error')
    }
  }

  async function deleteWebhook(id: string) {
    try {
      const res = await fetch(`${API_BASE}/api/webhooks/${id}`, {
        method: 'DELETE',
        headers: authHeaders(),
      })
      if (res.status === 401) { handleUnauthorized(); return }
      await refreshWebhooks()
      addToast(t.toasts.webhookDeleted, 'success')
    } catch {
      addToast(t.toasts.webhookDeleteFail, 'error')
    }
  }

  async function testWebhook(id: string) {
    try {
      const res = await fetch(`${API_BASE}/api/webhooks/${id}/test`, {
        method: 'POST',
        headers: authHeaders(),
      })
      if (res.status === 401) { handleUnauthorized(); return }
      if (!res.ok) { addToast(t.toasts.testFail, 'error'); return }
      const { delivered } = (await res.json()) as { delivered: boolean }
      addToast(delivered ? t.toasts.pingDelivered : t.toasts.pingNotDelivered, delivered ? 'success' : 'error')
      await loadWebhookDeliveries(id)
    } catch {
      addToast(t.toasts.testFail, 'error')
    }
  }

  async function loadWebhookDeliveries(id: string) {
    try {
      const res = await fetch(`${API_BASE}/api/webhooks/${id}/deliveries?limit=10`, { headers: authHeaders() })
      if (res.status === 401) { handleUnauthorized(); return }
      if (!res.ok) return
      const { deliveries } = (await res.json()) as { deliveries: WebhookDelivery[] }
      setWebhookDeliveries((prev) => ({ ...prev, [id]: deliveries }))
    } catch {
      /* non-critical */
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
      addToast(t.toasts.exportExcel, 'success')
    } catch {
      addToast(t.toasts.exportExcelFail, 'error')
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
      addToast(t.toasts.exportAudit, 'success')
    } catch {
      addToast(t.toasts.exportFail, 'error')
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
      addToast(t.toasts.exportAlerts, 'success')
    } catch {
      addToast(t.toasts.exportFail, 'error')
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
            <p>{t.header.subtitle}</p>
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
            {t.header.readonly}
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
            title={darkMode ? t.header.toLight : t.header.toDark}
            aria-pressed={darkMode}
          >
            {darkMode ? '☀️' : '🌙'}
          </button>
          <button
            type="button"
            className="logout-btn"
            onClick={handleLogout}
            title={t.header.logout}
          >
            <LogOut size={16} />
          </button>
        </div>
      </header>

      <section className="workspace">
        <aside className="query-panel">
          <div className="panel-heading">
            <MessageSquare size={18} />
            <h2>{t.query.heading}</h2>
            <div className="lang-toggle" role="group" aria-label={t.header.langAria}>
              {(['fr', 'en'] as Lang[]).map((code) => (
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

          <form onSubmit={handleSubmit} className="question-form">
            <textarea
              value={question}
              onChange={(event) => setQuestion(event.target.value)}
              rows={6}
              aria-label={t.query.ariaLabel}
              placeholder={t.query.placeholder}
            />
            <button type="submit" disabled={loading}>
              {loading ? <Loader2 className="spin" size={18} /> : <Send size={18} />}
              {loading ? t.query.analyzing : t.query.analyze}
            </button>
          </form>

          <div className="examples-list">
            {(lang === 'en' ? examplesByLang.en : examples).slice(0, 10).map((example) => (
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

          <WebhooksPanel
            subscriptions={webhooks}
            eventTypes={webhookEventTypes}
            deliveries={webhookDeliveries}
            error={webhooksError}
            onRefresh={() => void refreshWebhooks()}
            onCreate={(draft) => void createWebhook(draft)}
            onDelete={(id) => void deleteWebhook(id)}
            onTest={(id) => void testWebhook(id)}
            onLoadDeliveries={(id) => void loadWebhookDeliveries(id)}
          />

          {currentUser?.role === 'admin' && (
            <AdminPanel users={adminUsers} onToggleUser={(email, disable) => void handleToggleUser(email, disable)} />
          )}
        </aside>

        <section className="result-panel">
          <div className="metric-row">
            <div className="metric">
              <Activity size={18} />
              <span>{result?.intent ?? t.result.pending}</span>
            </div>
            <div className={result?.validation.ok ? 'metric ok' : 'metric'}>
              {result?.validation.ok ? <ShieldCheck size={18} /> : <AlertTriangle size={18} />}
              <span>{result?.validation.ok ? t.result.sqlValid : t.result.validation}</span>
            </div>
            <div className="metric">
              <Table2 size={18} />
              <span>{result ? `${result.rows.length} ${t.result.rows}` : t.result.rowsZero}</span>
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
              <p>{t.result.emptyState}</p>
            </div>
          )}

          {result && (
            <div className="analysis-grid">
              <div className="export-bar">
                <button
                  type="button"
                  className="export-pdf-btn"
                  onClick={() => window.print()}
                  title={t.result.exportPdfTitle}
                >
                  {t.result.exportPdf}
                </button>
              </div>

              <section className="answer-block">
                <h2>{t.result.answer}</h2>
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
                  <h2>{t.result.pipeline}</h2>
                </div>
                <OrchestrationTimeline steps={result.orchestration} />
              </section>

              <section className="chart-block">
                <div className="section-title">
                  <BarChart3 size={18} />
                  <h2>{result.chart?.title ?? t.result.chart}</h2>
                </div>
                <ResultChart result={result} data={visibleRows} />
              </section>

              <section className="table-block">
                <div className="section-title">
                  <Table2 size={18} />
                  <h2>{t.result.results}</h2>
                </div>
                <ResultTable columns={result.columns} rows={visibleRows} />
              </section>

              <section className="sql-block">
                <div className="section-title">
                  <Terminal size={18} />
                  <h2>SQL</h2>
                </div>
                <pre>{result.sql ?? t.result.noQuery}</pre>
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

export default App
