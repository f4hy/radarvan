import EventIcon from "@mui/icons-material/Event"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { useIsTournamentAdmin } from "./AuthContext"
import {
  BRACKET_VISIBLE_TO_ALL,
  formatCountdown,
  formatScheduledAt,
  playerLabel,
  shortMatchLabel,
} from "./Bracket"
import {
  BracketMatchOutput,
  BracketTournamentOutput,
  fetchBracket,
} from "./bracketApi"
import Loading from "./Loading"
import { useErrorSnackbar } from "./useErrorSnackbar"

// Self-contained ticking countdown for one agenda row - own setInterval (like
// Bracket.tsx's RevealCountdown) so only this row re-renders each second,
// not the whole list.
function AgendaCountdown({ scheduledAt }: { scheduledAt: string }) {
  const [nowMs, setNowMs] = React.useState(() => Date.now())
  React.useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  const remaining = new Date(scheduledAt).getTime() - nowMs
  return (
    <Typography
      variant="body2"
      sx={{
        fontFamily: "monospace",
        color: remaining > 0 ? "text.secondary" : "warning.main",
      }}
    >
      {remaining > 0 ? formatCountdown(remaining) : "Overdue"}
    </Typography>
  )
}

function AgendaRow({ match }: { match: BracketMatchOutput }) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack
        direction="row"
        sx={{
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 1,
        }}
      >
        <Stack spacing={0.25}>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {match.round_name} ({shortMatchLabel(match)})
          </Typography>
          <Typography variant="subtitle1">
            {playerLabel(match, "a")} vs {playerLabel(match, "b")}
          </Typography>
        </Stack>
        <Stack sx={{ alignItems: "flex-end" }} spacing={0.25}>
          {match.scheduled_at ? (
            <>
              <Typography variant="body2">
                {formatScheduledAt(match.scheduled_at)}
              </Typography>
              <AgendaCountdown scheduledAt={match.scheduled_at} />
            </>
          ) : (
            <Typography
              variant="body2"
              sx={{ color: "text.secondary", fontStyle: "italic" }}
            >
              Not yet scheduled
            </Typography>
          )}
        </Stack>
      </Stack>
    </Paper>
  )
}

// Every match that's ready to be played (both players known, no result
// recorded yet) - excludes TBD matches (still waiting on an earlier result),
// completed matches, and the Grand Final Reset when it isn't needed.
// Scheduled matches sort soonest-first; unscheduled ones (nothing to sort by)
// trail behind them.
function agendaMatches(
  bracketData: BracketTournamentOutput | null,
): BracketMatchOutput[] {
  const ready = (bracketData?.matches ?? []).filter(
    (m) => m.status === "ready" && m.player_a !== null && m.player_b !== null,
  )
  const scheduled = ready
    .filter((m) => m.scheduled_at !== null)
    .sort(
      (a, b) =>
        new Date(a.scheduled_at as string).getTime() -
        new Date(b.scheduled_at as string).getTime(),
    )
  const unscheduled = ready.filter((m) => m.scheduled_at === null)
  return [...scheduled, ...unscheduled]
}

export default function DisplayAgenda() {
  const [bracketData, setBracketData] =
    React.useState<BracketTournamentOutput | null>(null)
  const [loading, setLoading] = React.useState(true)
  const isTournamentAdmin = useIsTournamentAdmin()
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    setLoading(true)
    fetchBracket()
      .then(setBracketData)
      .catch(showError)
      .finally(() => setLoading(false))
  }, [showError])

  if (!BRACKET_VISIBLE_TO_ALL && !isTournamentAdmin) {
    return (
      <Paper sx={{ p: 2 }}>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1 }}>
          <EventIcon color="primary" />
          <Typography variant="h4">Agenda</Typography>
        </Stack>
        <Typography sx={{ color: "text.secondary" }}>
          This page isn&apos;t open yet — check back soon.
        </Typography>
      </Paper>
    )
  }

  if (loading) {
    return (
      <>
        <Loading />
        {errorSnackbar}
      </>
    )
  }

  const matches = agendaMatches(bracketData)

  return (
    <Paper sx={{ p: 2 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 2 }}>
        <EventIcon color="primary" />
        <Typography variant="h4">Agenda</Typography>
      </Stack>
      {!bracketData && (
        <Typography sx={{ color: "text.secondary" }}>
          No tournament has been created yet.
        </Typography>
      )}
      {bracketData && matches.length === 0 && (
        <Typography sx={{ color: "text.secondary" }}>
          No matches are ready to be played yet.
        </Typography>
      )}
      {matches.length > 0 && (
        <Stack spacing={1.5}>
          {matches.map((m) => (
            <AgendaRow key={m.match_id} match={m} />
          ))}
        </Stack>
      )}
      {errorSnackbar}
    </Paper>
  )
}
