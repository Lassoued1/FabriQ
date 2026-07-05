export type CurrentUser = {
  email: string
  tenant_id: string
  role: string
}

export type ChartSpec = {
  type: 'bar' | 'line' | 'area' | 'table'
  x: string
  y: string
  title: string
}

export type ValidationReport = {
  ok: boolean
  checks: string[]
  blocked: string[]
}

export type OrchestrationStep = {
  node: string
  status: 'done' | 'blocked' | 'skipped' | 'waiting'
  detail: string
}

export type ClarificationOption = {
  intent_id: string
  label: string
  question: string
  reason: string
}

export type AskResponse = {
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

export type HealthResponse = {
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

export type AdminUser = {
  email: string
  tenant_id: string
  role: string
  disabled: boolean
}

export type AuditEvent = {
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

export type CatalogIntent = {
  id: string
  label: string
  description: string
  keywords: string[]
  example_question: string
  chart: ChartSpec
}

export type CatalogColumn = {
  name: string
  label: string
  description: string
}

export type CatalogTable = {
  name: string
  label: string
  description: string
  columns: CatalogColumn[]
}

export type CatalogResponse = {
  intents: CatalogIntent[]
  tables: CatalogTable[]
}

export type CatalogTab = 'intents' | 'tables'

export type AlertRule = {
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

export type AlertEvent = {
  rule_id: string
  rule_name: string
  fired_at: string
  tenant_id: string
  triggered_value: number
  rows_snapshot: Record<string, string | number | null>[]
}
