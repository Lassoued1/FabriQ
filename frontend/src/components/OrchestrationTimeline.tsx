import type { OrchestrationStep } from '../types'
import { formatNode } from '../format'
import { useLang } from '../i18n'

export function OrchestrationTimeline({ steps }: { steps: OrchestrationStep[] }) {
  const { t } = useLang()
  if (!steps.length) {
    return <div className="timeline-empty">{t.result.noPipeline}</div>
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
