import type { AskResponse } from '../types'
import { formatCell } from '../format'

export function ResultTable({
  columns,
  rows,
}: {
  columns: string[]
  rows: AskResponse['rows']
}) {
  if (!columns.length || !rows.length) {
    return <div className="table-empty">Aucune ligne.</div>
  }

  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={`${index}-${columns[0]}`}>
              {columns.map((column) => (
                <td key={column}>{formatCell(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
