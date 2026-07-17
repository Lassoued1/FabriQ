import { useState } from 'react'
import type { FormEvent } from 'react'
import { Bell, Plus, RefreshCw, Trash2 } from 'lucide-react'
import type { AlertEvent, AlertRule } from '../types'
import { formatTime } from '../format'
import { useLang } from '../i18n'

export function AlertsPanel({
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
  const { t } = useLang()

  const INTENT_OPTIONS = [
    { id: 'supplier_delays', label: t.alerts.intents.supplier_delays, column: 'avg_delay_days' },
    { id: 'stockout_risk', label: t.alerts.intents.stockout_risk, column: 'days_of_coverage' },
    { id: 'margin_trend', label: t.alerts.intents.margin_trend, column: 'margin' },
    { id: 'returns_rate', label: t.alerts.intents.returns_rate, column: 'return_rate_pct' },
    { id: 'anomaly_detection', label: t.alerts.intents.anomaly_detection, column: 'variance_from_avg' },
  ]

  function handleCreate(e: FormEvent) {
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
        <h2>{t.alerts.heading}</h2>
        <button type="button" onClick={onRefresh} aria-label={t.alerts.refresh}>
          <RefreshCw size={16} />
        </button>
        <button type="button" onClick={onExportEvents} className="export-btn" title={t.alerts.exportCsv}>
          CSV ↓
        </button>
        <button type="button" onClick={() => setShowForm((v) => !v)} aria-label={t.alerts.newAlert}>
          <Plus size={16} />
        </button>
      </div>

      {error && <div className="ops-error">{error}</div>}

      {showForm && (
        <form className="alert-form" onSubmit={handleCreate}>
          <input
            placeholder={t.alerts.name}
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
              <option value="gt">{t.alerts.opGt}</option>
              <option value="lt">{t.alerts.opLt}</option>
              <option value="gte">{t.alerts.opGte}</option>
              <option value="lte">{t.alerts.opLte}</option>
            </select>
            <input
              type="number"
              value={formValue}
              onChange={(e) => setFormValue(e.target.value)}
              style={{ width: 80 }}
            />
          </div>
          <input
            placeholder={t.alerts.cronPh}
            value={formCron}
            onChange={(e) => setFormCron(e.target.value)}
          />
          <input
            placeholder={t.alerts.webhookPh}
            type="url"
            value={formWebhook}
            onChange={(e) => setFormWebhook(e.target.value)}
          />
          <input
            placeholder={t.alerts.slackPh}
            type="url"
            value={formSlack}
            onChange={(e) => setFormSlack(e.target.value)}
          />
          <input
            placeholder={t.alerts.emailPh}
            type="text"
            value={formEmail}
            onChange={(e) => setFormEmail(e.target.value)}
          />
          <button type="submit">{t.alerts.create}</button>
        </form>
      )}

      <div className="alert-rules-list">
        {rules.length === 0 && !error && (
          <div className="audit-empty">{t.alerts.noRules}</div>
        )}
        {rules.map((rule) => (
          <article key={rule.id} className="alert-rule-item">
            <div className="alert-rule-header">
              <span className={rule.enabled ? 'audit-dot ok' : 'audit-dot'} />
              <strong>{rule.name}</strong>
              <button type="button" onClick={() => onDelete(rule.id)} title={t.alerts.delete}>
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
        <p className="alert-events-title">{t.alerts.triggers} ({eventsTotal})</p>
        {events.length === 0 && (
          <div className="audit-empty">{t.alerts.noEvents}</div>
        )}
        {events.map((ev, i) => (
          <article key={`${ev.rule_id}-${i}`} className="alert-event-item">
            <strong>{ev.rule_name}</strong>
            <span>{t.alerts.value}: {ev.triggered_value.toFixed(2)}</span>
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
