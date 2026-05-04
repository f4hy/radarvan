import * as React from "react"
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts"

export default function WinRateRadar(props: {
  data: { name: string; winRate: number }[]
  aspect?: number
}) {
  return (
    <ResponsiveContainer width="99%" aspect={props.aspect ?? 1}>
      <RadarChart data={props.data}>
        <PolarGrid />
        <PolarAngleAxis dataKey="name" tick={{ fontSize: 11 }} />
        <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
        <Radar
          dataKey="winRate"
          name="Win Rate"
          fill="#42A5F5"
          fillOpacity={0.4}
          stroke="#42A5F5"
        />
        <Tooltip
          formatter={(value) => [`${(value as number) ?? 0}%`, "Win Rate"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
