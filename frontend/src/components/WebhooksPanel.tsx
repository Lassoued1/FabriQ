import { useState } from 'react'
import type { FormEvent } from 'react'
import { Webhook, Plus, RefreshCw, Trash2, Send } from 'lucide-react'
import type { WebhookDelivery, WebhookSubscription } from '../types'
import { formatTime } from '../format'
import { useLang } from '../i18n'

export function WebhooksPanel({
  subscriptions,
  eventTypes,
  deliveries,
  error,
  onRefresh,
  onCreate,
  onDelete,
  onTest,
  onLoadDeliveries,
}: {
  subscriptions: WebhookSubscription[]
  eventTypes: string[]
  deliveries: Record<string, WebhookDelivery[]>
  error: string | null
  onRefresh: () => void
  onCreate: (draft: { name: string; url: string; events: string[] }) => void
  onDelete: (id: string) => void
  onTest: (id: string) => void
  onLoadDeliveries: (id: string) => void
}) {
  const [showForm, setShowForm] = useState(false)
  const [formName, setFormName] = useState('')
  const [formUrl, setFormUrl] = useState('')
  const [formEvents, setFormEvents] = useState<string[]>([])
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const { t } = useLang()

  function toggleEvent(type: string) {
    setFormEvents((prev) =>
      prev.includes(type) ? prev.filter((t) => t !== type) : [...prev, type],
    )
  }

  function handleCreate(e: FormEvent) {
    e.preventDefault()
    if (!formName.trim() || !formUrl.trim() || formEvents.length === 0) return
    onCreate({ name: formName.trim(), url: formUrl.trim(), events: formEvents })
    setShowForm(false)
    setFormName('')
    setFormUrl('')
    setFormEvents([])
  }

  function toggleDeliveries(id: string) {
    if (expandedId === id) {
      setExpandedId(null)
      return
    }
    setExpandedId(id)
    onLoadDeliveries(id)
  }

  return (
    <section className="webhooks-panel">
      <div className="panel-heading compact">
        <Webhook size={18} />
        <h2>{t.webhooks.heading}</h2>
        <button type="button" onClick={onRefresh} aria-label={t.webhooks.refresh}>
          <RefreshCw size={16} />
        </button>
        <button type="button" onClick={() => setShowForm((v) => !v)} aria-label={t.webhooks.newWebhook}>
          <Plus size={16} />
        </button>
      </div>

      {error && <div className="ops-error">{error}</div>}

      {showForm && (
        <form className="alert-form" onSubmit={handleCreate}>
          <input
            placeholder={t.webhooks.name}
            value={formName}
            onChange={(e) => setFormName(e.target.value)}
            required
          />
          <input
            placeholder={t.webhooks.url}
            type="url"
            value={formUrl}
            onChange={(e) => setFormUrl(e.target.value)}
            required
          />
          <fieldset className="webhook-events-fieldset">
            <legend>{t.webhooks.events}</legend>
            {eventTypes.map((type) => (
              <label key={type} className="webhook-event-check">
                <input
                  type="checkbox"
                  checked={formEvents.includes(type)}
                  onChange={() => toggleEvent(type)}
                />
                {type}
              </label>
            ))}
          </fieldset>
          <button type="submit" disabled={formEvents.length === 0}>{t.webhooks.create}</button>
        </form>
      )}

      <div className="alert-rules-list">
        {subscriptions.length === 0 && !error && (
          <div className="audit-empty">{t.webhooks.noWebhooks}</div>
        )}
        {subscriptions.map((hook) => (
          <article key={hook.id} className="alert-rule-item">
            <div className="alert-rule-header">
              <span className={hook.enabled ? 'audit-dot ok' : 'audit-dot'} />
              <strong>{hook.name}</strong>
              <button type="button" onClick={() => onTest(hook.id)} title={t.webhooks.testPing}>
                <Send size={13} />
              </button>
              <button type="button" onClick={() => onDelete(hook.id)} title={t.webhooks.delete}>
                <Trash2 size={13} />
              </button>
            </div>
            <p className="alert-rule-desc webhook-url">{hook.url}</p>
            <p className="alert-rule-cron">{hook.events.join(' · ')}</p>
            <button
              type="button"
              className="webhook-deliveries-toggle"
              onClick={() => toggleDeliveries(hook.id)}
            >
              {expandedId === hook.id ? '▾' : '▸'} {t.webhooks.deliveries}
            </button>
            {expandedId === hook.id && (
              <div className="webhook-deliveries">
                {(deliveries[hook.id] ?? []).length === 0 && (
                  <div className="audit-empty">{t.webhooks.noDeliveries}</div>
                )}
                {(deliveries[hook.id] ?? []).map((d, i) => (
                  <div key={`${d.event_id}-${d.attempt}-${i}`} className="webhook-delivery-item">
                    <span className={d.ok ? 'audit-dot ok' : 'audit-dot'} />
                    <span className="webhook-delivery-type">{d.event_type}</span>
                    <span>{d.status_code ?? d.error ?? '—'}</span>
                    <span>#{d.attempt}</span>
                    <span>{formatTime(d.delivered_at)}</span>
                  </div>
                ))}
              </div>
            )}
          </article>
        ))}
      </div>
    </section>
  )
}
