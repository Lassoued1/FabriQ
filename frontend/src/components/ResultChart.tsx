import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import type { AskResponse } from '../types'

export function ResultChart({
  result,
  data,
}: {
  result: AskResponse
  data: AskResponse['rows']
}) {
  if (!result.chart || data.length === 0) {
    return <div className="chart-empty">Aucune donnee graphique.</div>
  }

  const chartProps = {
    data,
    margin: { top: 8, right: 12, bottom: 20, left: 0 },
  }

  if (result.chart.type === 'line') {
    return (
      <div className="chart-frame">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart {...chartProps}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis dataKey={result.chart.x} tick={{ fontSize: 12 }} />
            <YAxis tick={{ fontSize: 12 }} width={48} />
            <Tooltip />
            <Line
              type="monotone"
              dataKey={result.chart.y}
              stroke="#1f6feb"
              strokeWidth={2}
              dot={{ r: 3 }}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    )
  }

  return (
    <div className="chart-frame">
      <ResponsiveContainer width="100%" height="100%">
        <BarChart {...chartProps}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={result.chart.x} tick={{ fontSize: 12 }} interval={0} />
          <YAxis tick={{ fontSize: 12 }} width={48} />
          <Tooltip />
          <Bar
            dataKey={result.chart.y}
            fill="#0f9f6e"
            radius={[4, 4, 0, 0]}
            isAnimationActive={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
