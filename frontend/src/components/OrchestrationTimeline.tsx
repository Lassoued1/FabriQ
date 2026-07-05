import type { OrchestrationStep } from '../types'
import { formatNode } from '../format'

export function OrchestrationTimeline({ steps }: { steps: OrchestrationStep[] }) {
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
