import type { ValidationReport } from '../types'

export function ValidationList({ validation }: { validation: ValidationReport }) {
  return (
    <div className="validation-list">
      {validation.checks.map((check) => (
        <span key={check} className="check ok">
          {check}
        </span>
      ))}
      {validation.blocked.map((blocked) => (
        <span key={blocked} className="check blocked">
          {blocked}
        </span>
      ))}
    </div>
  )
}
