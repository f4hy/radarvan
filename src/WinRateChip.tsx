import * as React from "react"
import Chip from "@mui/material/Chip"
import Tooltip from "@mui/material/Tooltip"
import LinearProgress from "@mui/material/LinearProgress"
import { formatPercent, winRateTone } from "./utils"

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

  const color: "success" | "error" | "default" =
    tone === "positive" ? "success" : tone === "negative" ? "error" : "default"

  const title =
    n === 0
      ? "No games yet"
      : `${formatPercent(rate)} win rate over ${n} game${n === 1 ? "" : "s"}` +
        ` — 95% CI ${formatPercent(low)}–${formatPercent(high)}` +
        (lowSample ? " (small sample — treat as noise)" : "")

  return (
    <Tooltip title={title}>
      <Chip
        label={`${formatPercent(rate)} (${wins}W-${losses}L)`}
        size={props.size ?? "small"}
        color={color}
        variant={props.variant ?? "outlined"}
        sx={lowSample ? { opacity: 0.5 } : undefined}
      />
    </Tooltip>
  )
}

/**
 * The same verdict as a bar: fill is the win rate, color is the shared tone,
 * and the whole bar fades with `confidence` so a 3-0 record reads quieter than
 * a 21-8 one.
 *
 * TeamStats and MapStats each had this block character-for-character —
 * `winRateTone` centralized the *rule* but left the rendering copied, which is
 * how the 0.55/0.45 thresholds it replaced drifted apart in the first place.
 */
export function WinRateBar(props: { wins: number; losses: number }) {
  const { rate, confidence, hex } = winRateTone(props.wins, props.losses)
  return (
    <LinearProgress
      variant="determinate"
      value={rate * 100}
      sx={{
        height: 7,
        borderRadius: 4,
        opacity: 0.45 + 0.55 * confidence,
        bgcolor: "action.hover",
        "& .MuiLinearProgress-bar": { bgcolor: hex },
      }}
    />
  )
}
