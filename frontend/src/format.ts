import type { HealthResponse } from './types'

export function formatNode(value: string) {
  return value.replaceAll('_', ' ')
}

export function formatLlmStatus(health: HealthResponse | null) {
  if (!health) return 'LLM'
  if (health.llm_status === 'ready') return 'LLM ready'
  if (health.llm_status === 'model_missing') return 'Model missing'
  if (health.llm_status === 'unreachable') return 'LLM unreachable'
  if (health.llm_status === 'disabled' || health.llm_mode === 'disabled') return 'LLM off'
  return health.llm_mode === 'optional-router' ? 'LLM optional' : 'LLM'
}

export function formatLlmLatency(health: HealthResponse | null) {
  if (!health) return 'LLM --'
  if (health.llm_status === 'disabled') return 'LLM off'
  if (typeof health.llm_latency_ms === 'number') return `${health.llm_latency_ms} ms`
  return 'LLM --'
}

export function llmPillClass(health: HealthResponse | null) {
  if (health?.llm_status === 'ready') return 'ops-pill ok'
  if (health?.llm_status === 'model_missing') return 'ops-pill warning'
  if (health?.llm_status === 'unreachable') return 'ops-pill blocked'
  return 'ops-pill'
}

export function formatCell(value: string | number | null | undefined) {
  if (value === null || value === undefined) return '-'
  if (typeof value === 'number') return new Intl.NumberFormat('fr-FR').format(value)
  return value
}

export function formatTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) return '--:--'
  return new Intl.DateTimeFormat('fr-FR', { hour: '2-digit', minute: '2-digit' }).format(date)
}
