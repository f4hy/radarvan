import * as React from "react"
import Chip from "@mui/material/Chip"
import Tooltip from "@mui/material/Tooltip"
import { winRateTone } from "./utils"

// A win-rate chip that is honest about uncertainty. Color is driven by the 95%
// Wilson confidence interval rather than the raw rate:
//   - green  when we're confident the rate is above 50% (lower bound > 0.5)
//   - red    when we're confident it's below 50% (upper bound < 0.5)
//   - grey   when the interval straddles 50% — i.e. the sample can't tell us,
//            which is exactly the "this cell is noise" case.
// Tiny samples are additionally dimmed, and the CI is shown on hover.
export default function WinRateChip(props: {
  wins: number
  losses: number
  size?: "small" | "medium"
  variant?: "outlined" | "filled"
}) {
  const { wins, losses } = props
  const { rate, low, high, n, lowSample, tone } = winRateTone(wins, losses)

  const pct = (x: number) => `${(x * 100).toFixed(0)}%`

  const color: "success" | "error" | "default" =
    tone === "positive" ? "success" : tone === "negative" ? "error" : "default"

  const title =
    n === 0
      ? "No games yet"
      : `${pct(rate)} win rate over ${n} game${n === 1 ? "" : "s"}` +
        ` — 95% CI ${pct(low)}–${pct(high)}` +
        (lowSample ? " (small sample — treat as noise)" : "")

  return (
    <Tooltip title={title}>
      <Chip
        label={`${pct(rate)} (${wins}W-${losses}L)`}
        size={props.size ?? "small"}
        color={color}
        variant={props.variant ?? "outlined"}
        sx={lowSample ? { opacity: 0.5 } : undefined}
      />
    </Tooltip>
  )
}
