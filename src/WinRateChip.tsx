import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Tooltip from "@mui/material/Tooltip"
import LinearProgress from "@mui/material/LinearProgress"
import { CHART_LOSS, CHART_WIN } from "./theme"
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

/**
 * Wins and losses as one bar whose *length* is how many games there were.
 *
 * `WinRateBar` above fills by rate, so 3-0 and 30-0 draw an identical bar.
 * This one is for where the sample size is the point: the split says how the
 * games went, the length says how many of them there were, so "great on this
 * general" and "played it twice" can't look the same.
 *
 * `max` is the length a full-width bar means. Pick it from the set being
 * compared — across a row of players a global max is right, but for one
 * player's twelve generals it should be that player's own busiest, or a light
 * player's whole chart collapses to slivers.
 */
export function WinLossVolumeBar(props: {
  wins: number
  losses: number
  max: number
}) {
  const total = props.wins + props.losses
  const length = props.max > 0 ? (total / props.max) * 100 : 0
  const winShare = total > 0 ? (props.wins / total) * 100 : 0
  return (
    <Tooltip
      title={`${total} game${total === 1 ? "" : "s"}: ${props.wins}W-${props.losses}L`}
    >
      <Box
        sx={{
          flexGrow: 1,
          minWidth: 40,
          height: 12,
          borderRadius: 4,
          bgcolor: "action.hover",
          overflow: "hidden",
        }}
      >
        <Box sx={{ display: "flex", width: `${length}%`, height: "100%" }}>
          <Box sx={{ width: `${winShare}%`, bgcolor: CHART_WIN }} />
          <Box sx={{ flexGrow: 1, bgcolor: CHART_LOSS }} />
        </Box>
      </Box>
    </Tooltip>
  )
}
