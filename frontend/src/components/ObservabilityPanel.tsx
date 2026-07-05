import { Activity, Clock3, Database, RefreshCw, Server } from 'lucide-react'
import type { AuditEvent, HealthResponse } from '../types'
import { formatLlmLatency, formatLlmStatus, formatTime, llmPillClass } from '../format'

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
