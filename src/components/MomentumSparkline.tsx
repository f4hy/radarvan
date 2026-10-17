import { WIN_COLOR } from "../lib/theme"

/** The eventual winner's win-prob at each point, oriented so a comeback dips
 * then recovers regardless of which side "team A" was. Null if the match
 * has no decisive two-team curve. */
export function winnerProbSeries(wpot: {
  actual_winner?: string | null
  points: Array<{ prob_team_a: number }>
}): number[] | null {
  if (!wpot.actual_winner || wpot.points.length < 2) return null
  const winnerIsA = wpot.actual_winner === "team_a"
  return wpot.points.map((p) => (winnerIsA ? p.prob_team_a : 1 - p.prob_team_a))
}

export default function MomentumSparkline(props: {
  points: number[]
  width?: number
  height?: number
}) {
  const width = props.width ?? 72
  const height = props.height ?? 28
  const { points } = props
  const path = points
    .map((p, i) => {
      const x = (i / (points.length - 1)) * width
      const y = height - p * height
      return `${i === 0 ? "M" : "L"}${x.toFixed(1)},${y.toFixed(1)}`
    })
    .join(" ")
  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      aria-hidden="true"
      style={{ flexShrink: 0 }}
    >
      <line
        x1={0}
        y1={height / 2}
        x2={width}
        y2={height / 2}
        stroke="currentColor"
        strokeOpacity={0.25}
        strokeDasharray="2,2"
      />
      <path d={path} fill="none" stroke={WIN_COLOR} strokeWidth={1.75} />
    </svg>
  )
}
