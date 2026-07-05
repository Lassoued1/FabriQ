import { describe, expect, it } from 'vitest'
import {
  formatCell,
  formatLlmLatency,
  formatLlmStatus,
  formatNode,
  formatTime,
  llmPillClass,
} from './format'
import type { HealthResponse } from './types'

function health(overrides: Partial<HealthResponse>): HealthResponse {
  return { status: 'ok', service: 'fabriq-api', database: 'sqlite', ...overrides }
}

describe('formatNode', () => {
  it('remplace les underscores par des espaces', () => {
    expect(formatNode('route_intent')).toBe('route intent')
    expect(formatNode('execute_readonly')).toBe('execute readonly')
  })
})

describe('formatCell', () => {
  it('affiche un tiret pour les valeurs absentes', () => {
    expect(formatCell(null)).toBe('-')
    expect(formatCell(undefined)).toBe('-')
  })

  it('formate les nombres en convention francaise', () => {
    expect(formatCell(7)).toBe('7')
    expect(formatCell(1234)).toBe(new Intl.NumberFormat('fr-FR').format(1234))
  })

  it('laisse passer les chaines telles quelles', () => {
    expect(formatCell('FX-700')).toBe('FX-700')
  })
})

describe('formatTime', () => {
  it('retourne un placeholder pour une date invalide', () => {
    expect(formatTime('pas-une-date')).toBe('--:--')
  })

  it('formate une date valide en heures:minutes', () => {
    expect(formatTime('2026-07-03T08:30:00')).toMatch(/^\d{2}:\d{2}$/)
  })
})

describe('formatLlmStatus', () => {
  it('couvre les statuts connus', () => {
    expect(formatLlmStatus(null)).toBe('LLM')
    expect(formatLlmStatus(health({ llm_status: 'ready' }))).toBe('LLM ready')
    expect(formatLlmStatus(health({ llm_status: 'model_missing' }))).toBe('Model missing')
    expect(formatLlmStatus(health({ llm_status: 'unreachable' }))).toBe('LLM unreachable')
    expect(formatLlmStatus(health({ llm_status: 'disabled' }))).toBe('LLM off')
    expect(formatLlmStatus(health({ llm_mode: 'optional-router' }))).toBe('LLM optional')
  })
})

describe('formatLlmLatency', () => {
  it('affiche la latence quand elle est mesuree', () => {
    expect(formatLlmLatency(null)).toBe('LLM --')
    expect(formatLlmLatency(health({ llm_status: 'disabled' }))).toBe('LLM off')
    expect(formatLlmLatency(health({ llm_latency_ms: 42 }))).toBe('42 ms')
  })
})

describe('llmPillClass', () => {
  it('reflete le statut dans la classe CSS', () => {
    expect(llmPillClass(null)).toBe('ops-pill')
    expect(llmPillClass(health({ llm_status: 'ready' }))).toBe('ops-pill ok')
    expect(llmPillClass(health({ llm_status: 'model_missing' }))).toBe('ops-pill warning')
    expect(llmPillClass(health({ llm_status: 'unreachable' }))).toBe('ops-pill blocked')
  })
})
