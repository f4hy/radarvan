import Box from "@mui/material/Box"
import Paper from "@mui/material/Paper"
import Skeleton from "@mui/material/Skeleton"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import { useTheme } from "@mui/material/styles"
import * as React from "react"
import { MatchNarrative as MatchNarrativeData, NarrativeBeat } from "./api"
import { Client } from "./Client"
import { usePlayerAccentColor } from "./PlayerColorsContext"
import { useErrorSnackbar } from "./useErrorSnackbar"

/**
 * The match retold as a timeline of sentences.
 *
 * Entirely deterministic — every beat is a fact already in the parsed replay,
 * assembled server-side (`radarvan/match_narrative.py`). No model call, so this
 * is free to render anywhere and identical on every load.
 */

// `kind` is a stable backend slug. An unknown one falls back to a plain bullet
// rather than breaking the row, so a new beat type server-side is safe to ship
// before the frontend knows about it.
const BEAT_ICONS: { [key: string]: string } = {
  setup: "🎬",
  first_blood: "🩸",
  milestone: "🎖️",
  superweapon: "☢️",
  collapse: "🚜",
  damage: "💥",
  economy: "💰",
  tempo: "🚀",
  result: "🏁",
}

function minuteLabel(minute: number | null | undefined): string {
  if (minute === null || minute === undefined) return ""
  const total = Math.round(minute * 60)
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`
}

function Beat(props: { beat: NarrativeBeat }) {
  const theme = useTheme()
  const { beat } = props
  // usePlayerAccentColor is a hook, so it can't be called conditionally — pass
  // the empty string for a beat about nobody and ignore the result.
  const accent = usePlayerAccentColor(beat.playerName ?? "")
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: "baseline" }}>
      <Typography
        variant="caption"
        sx={{
          minWidth: 42,
          textAlign: "right",
          fontVariantNumeric: "tabular-nums",
          color: theme.palette.text.secondary,
          flexShrink: 0,
        }}
      >
        {minuteLabel(beat.atMinute)}
      </Typography>
      <Typography sx={{ fontSize: 14, flexShrink: 0 }}>
        {BEAT_ICONS[beat.kind] ?? "•"}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          borderLeft: beat.playerName ? `3px solid ${accent}` : "none",
          pl: beat.playerName ? 1 : 0,
        }}
      >
        {beat.text}
      </Typography>
    </Stack>
  )
}

export function NarrativeBody(props: { narrative: MatchNarrativeData }) {
  const beats = props.narrative.beats ?? []
  if (beats.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No parsed replay for this match yet.
      </Typography>
    )
  }
  return (
    <Stack spacing={0.75}>
      {beats.map((beat, index) => (
        <Beat key={`${beat.kind}-${index}`} beat={beat} />
      ))}
    </Stack>
  )
}

/** Fetches and renders one match's narrative, headline included. */
export default function MatchNarrative(props: {
  matchId: number
  showHeadline?: boolean
}) {
  const [narrative, setNarrative] = React.useState<MatchNarrativeData | null>(
    null,
  )
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    setNarrative(null)
    Client.getMatchNarrativeApiNarrativeMatchIdGet({ matchId: props.matchId })
      .then(setNarrative)
      .catch(showError)
  }, [props.matchId, showError])

  if (narrative === null) {
    return (
      <Box>
        {errorSnackbar}
        <Skeleton variant="rounded" height={120} animation="wave" />
      </Box>
    )
  }

  return (
    // App.css centers page text; a timeline of sentences must not inherit it.
    <Paper variant="outlined" sx={{ p: 1.5, textAlign: "left" }}>
      {errorSnackbar}
      {props.showHeadline !== false && (
        <Typography variant="subtitle2" sx={{ mb: 1 }}>
          {narrative.headline}
        </Typography>
      )}
      <NarrativeBody narrative={narrative} />
    </Paper>
  )
}
