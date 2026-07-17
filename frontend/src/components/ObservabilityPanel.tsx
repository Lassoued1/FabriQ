import { Activity, Clock3, Database, RefreshCw, Server } from 'lucide-react'
import type { AuditEvent, HealthResponse } from '../types'
import { formatLlmLatency, formatLlmStatus, formatTime, llmPillClass } from '../format'
import { useLang } from '../i18n'

const AUDIT_INTENT_IDS = [
  '',
  'margin_trend',
  'stockout_risk',
  'supplier_delays',
  'production_efficiency',
  'revenue_trend',
  'stock_aging',
  'logistics_cost',
  'returns_rate',
  'customer_concentration',
  'anomaly_detection',
] as const

export function ObservabilityPanel({
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
  const { t } = useLang()
  const latest = events[0]
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const intentLabel = (id: string) =>
    id === '' ? t.obs.intents.all : (t.obs.intents as Record<string, string>)[id] ?? id

  return (
    <section className="observability-panel">
      <div className="panel-heading compact">
        <Activity size={18} />
        <h2>{t.obs.heading}</h2>
        <button type="button" onClick={onRefresh} aria-label={t.obs.refresh}>
          <RefreshCw className={loading ? 'spin' : undefined} size={16} />
        </button>
        <button type="button" onClick={onExportCsv} className="export-btn" title={t.obs.exportCsv}>
          CSV ↓
        </button>
        <button type="button" onClick={onExportXlsx} className="export-btn" title={t.obs.exportXlsx}>
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
          {health?.database ?? t.obs.unknown}
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
          aria-label={t.obs.filterIntent}
        >
          {AUDIT_INTENT_IDS.map((id) => (
            <option key={id} value={id}>{intentLabel(id)}</option>
          ))}
        </select>
        <select
          value={filterStatus}
          onChange={(e) => onFilterChange(filterIntent, e.target.value as '' | 'ok' | 'failed')}
          aria-label={t.obs.filterStatus}
        >
          <option value="">{t.obs.allStatuses}</option>
          <option value="ok">{t.obs.valid}</option>
          <option value="failed">{t.obs.blocked}</option>
        </select>
      </div>

      {error && <div className="ops-error">{error}</div>}

      {latest && (
        <div className="latest-trace">
          <span>{t.obs.latestTrace}</span>
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
              <span>{event.row_count} {t.obs.rows}</span>
            </footer>
          </article>
        ))}
        {!events.length && !error && <div className="audit-empty">{t.obs.noTrace}</div>}
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
