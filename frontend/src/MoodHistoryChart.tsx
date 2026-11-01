import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { MOODS } from './moods'
import type { Emotion } from './types'

type MoodCount = {
  emotion: Emotion
  label: string
  count: number
}

type MoodHistoryChartProps = {
  counts: MoodCount[]
}

function MoodHistoryChart({ counts }: MoodHistoryChartProps) {
  return (
    <ResponsiveContainer width="100%" height="100%">
      <BarChart data={counts} margin={{ top: 10, right: 4, bottom: 0, left: -20 }}>
        <CartesianGrid strokeDasharray="3 5" vertical={false} stroke="rgba(135,135,170,.18)" />
        <XAxis dataKey="label" axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'currentColor' }} />
        <YAxis allowDecimals={false} axisLine={false} tickLine={false} tick={{ fontSize: 11, fill: 'currentColor' }} />
        <Tooltip cursor={{ fill: 'rgba(255,255,255,.08)' }} contentStyle={{ borderRadius: 14, border: '1px solid rgba(140,130,180,.2)', background: 'rgba(19,20,39,.94)', color: '#fff' }} />
        <Bar dataKey="count" name="Check-ins" radius={[8, 8, 2, 2]} maxBarSize={44}>
          {counts.map((entry) => <Cell key={entry.emotion} fill={MOODS[entry.emotion].color} />)}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

export default MoodHistoryChart
