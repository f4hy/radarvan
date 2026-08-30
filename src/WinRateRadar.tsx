import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import { BRAND_COLOR } from "./theme"

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
          fill={BRAND_COLOR}
          fillOpacity={0.4}
          stroke={BRAND_COLOR}
        />
        <Tooltip
          formatter={(value) => [`${(value as number) ?? 0}%`, "Win Rate"]}
        />
      </RadarChart>
    </ResponsiveContainer>
  )
}
