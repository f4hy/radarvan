import CheckCircleIcon from "@mui/icons-material/CheckCircle"
import EditCalendarIcon from "@mui/icons-material/EditCalendar"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import EventAvailableIcon from "@mui/icons-material/EventAvailable"
import HowToVoteIcon from "@mui/icons-material/HowToVote"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import ButtonBase from "@mui/material/ButtonBase"
import Chip from "@mui/material/Chip"
import IconButton from "@mui/material/IconButton"
import Paper from "@mui/material/Paper"
import Popover from "@mui/material/Popover"
import Stack from "@mui/material/Stack"
import { alpha, keyframes, type Theme } from "@mui/material/styles"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import DateTimeField from "./DateTimeField"
import dayjs, { type Dayjs } from "dayjs"
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query"
import * as React from "react"
import { useAuth, useIsTournamentAdmin } from "./AuthContext"
import { startDiscordLogin } from "./auth"
import {
  type BracketMatchOutput,
  type BracketMatchPrediction,
  type BracketTournamentOutput,
  fetchBracketPredictionLeaderboard,
  fetchBracketPredictions,
  setBracketPrediction,
} from "./bracketApi"
import {
  formatCountdown,
  formatScheduledAt,
  googleCalendarUrl,
  playerLabel,
  shortMatchLabel,
  useCountdownMs,
} from "./bracketFormat"
import { WIN_COLOR } from "./theme"
import { useErrorSnackbar } from "./useErrorSnackbar"

// Escalating hype thresholds for AgendaCountdown - calm and quiet until a
// match is a week out, then increasingly loud so the countdown itself
// signals "go watch this" without anyone needing to read the clock digits.
const WEEK_MS = 7 * 24 * 60 * 60 * 1000
const DAY_MS = 24 * 60 * 60 * 1000
const HOUR_MS = 60 * 60 * 1000

type HypeLevel = "calm" | "week" | "day" | "hour"

function hypeLevel(remainingMs: number): HypeLevel {
  if (remainingMs <= HOUR_MS) return "hour"
  if (remainingMs <= DAY_MS) return "day"
  if (remainingMs <= WEEK_MS) return "week"
  return "calm"
}

const pulseGlow = keyframes`
  0%, 100% { box-shadow: 0 0 4px 0 currentColor; transform: scale(1); }
  50% { box-shadow: 0 0 14px 3px currentColor; transform: scale(1.06); }
`

const flashLive = keyframes`
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
`

// Uses the same shared per-second countdown ticker as Bracket.tsx's
// RevealCountdown, so only this row re-renders each second, not the whole
// list. Exported for Bracket.tsx's hero "next match" banner, which reuses
// the same escalating hype styling rather than a second copy of it.
export function AgendaCountdown({ scheduledAt }: { scheduledAt: Date }) {
  const remaining = useCountdownMs(scheduledAt)

  if (remaining <= 0) {
    return (
      <Chip
        size="small"
        label="LIVE NOW"
        sx={{
          fontWeight: 800,
          letterSpacing: 0.5,
          color: "error.contrastText",
          bgcolor: "error.main",
          animation: `${flashLive} 1s ease-in-out infinite`,
        }}
      />
    )
  }

  const level = hypeLevel(remaining)

  return (
    <Chip
      size="small"
      variant={level === "calm" ? "outlined" : "filled"}
      label={`${level === "hour" ? "🔥 " : ""}${formatCountdown(remaining)}`}
      sx={{
        fontFamily: "monospace",
        letterSpacing: 0.5,
        fontWeight:
          level === "hour"
            ? 800
            : level === "day"
              ? 700
              : level === "week"
                ? 600
                : 500,
        color: {
          hour: "error.contrastText",
          day: "warning.contrastText",
          week: "info.contrastText",
          calm: "text.secondary",
        }[level],
        bgcolor: {
          hour: "error.main",
          day: "warning.main",
          week: "info.main",
          calm: "transparent",
        }[level],
        borderColor: level === "week" ? "info.main" : undefined,
        transition: "background-color 0.3s ease, color 0.3s ease",
        animation:
          level === "hour"
            ? `${pulseGlow} 0.9s ease-in-out infinite`
            : undefined,
      }}
    />
  )
}

// Admin-only "set the time" control for one row - a calendar icon (rather
// than a labelled button) so it reads as an admin affordance at a glance,
// same idiom as MatchBox's edit-pencil icon in Bracket.tsx, which is also
// only ever rendered for admins. Opens a popover with a full calendar +
// clock picker (DateTimeField, which carries its own LocalizationProvider)
// rather than the
// bare native datetime-local input the removed MatchEditor date field and
// the tournament reveal-time dialog used to rely on.
function ScheduleMatchButton({
  match,
  onSchedule,
}: {
  match: BracketMatchOutput
  onSchedule: (matchId: string, scheduledAt: Date | null) => Promise<void>
}) {
  const [anchorEl, setAnchorEl] = React.useState<HTMLElement | null>(null)
  const [value, setValue] = React.useState<Dayjs | null>(null)
  const [saving, setSaving] = React.useState(false)

  const handleOpen = (e: React.MouseEvent<HTMLElement>) => {
    setValue(match.scheduledAt ? dayjs(match.scheduledAt) : null)
    setAnchorEl(e.currentTarget)
  }
  const handleClose = () => setAnchorEl(null)

  const commit = async (scheduledAt: Date | null) => {
    setSaving(true)
    try {
      await onSchedule(match.matchId, scheduledAt)
    } finally {
      setSaving(false)
      handleClose()
    }
  }

  return (
    <>
      <Tooltip title="Schedule match (admin only)">
        <IconButton size="small" onClick={handleOpen}>
          <EditCalendarIcon fontSize="small" color="primary" />
        </IconButton>
      </Tooltip>
      <Popover
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        onClose={handleClose}
        anchorOrigin={{ vertical: "bottom", horizontal: "right" }}
        transformOrigin={{ vertical: "top", horizontal: "right" }}
      >
        <Stack spacing={1.5} sx={{ p: 2, minWidth: 260 }}>
          <DateTimeField
            label="Scheduled date/time"
            value={value}
            onChange={(newValue) => setValue(newValue)}
            slotProps={{ textField: { size: "small", autoFocus: true } }}
          />
          <Stack
            direction="row"
            spacing={1}
            sx={{ justifyContent: "flex-end" }}
          >
            {match.scheduledAt && (
              <Button
                size="small"
                disabled={saving}
                onClick={() => commit(null)}
              >
                Clear
              </Button>
            )}
            <Button
              size="small"
              variant="contained"
              disabled={saving}
              onClick={() => commit(value ? value.toDate() : null)}
            >
              Save
            </Button>
          </Stack>
        </Stack>
      </Popover>
    </>
  )
}

// Community "who wins this match" prediction poll. Real Button-ish click
// targets (ButtonBase + hover states), not just clickable text, so it reads
// as an interactive poll rather than a static stat bar. Percentages default
// to a 50/50 split with no tally yet so the bar isn't empty/blank before
// anyone's voted; the total-prediction count is always shown (even at zero)
// so the feature itself is discoverable.
function PredictionBar({
  prediction,
  playerA,
  playerB,
  scheduledAt,
  onPick,
}: {
  prediction: BracketMatchPrediction | undefined
  playerA: string
  playerB: string
  scheduledAt: Date | null
  onPick: (winner: string | null) => Promise<void>
}) {
  const { status } = useAuth()
  const loggedIn = status?.loggedIn ?? false
  const [pending, setPending] = React.useState(false)

  const tally = prediction?.tally ?? {}
  const countA = tally[playerA] ?? 0
  const countB = tally[playerB] ?? 0
  const total = countA + countB
  const pctA = total > 0 ? Math.round((countA / total) * 100) : 50
  const pctB = 100 - pctA
  const myPick = prediction?.myPick ?? null
  // `prediction.open` is a snapshot from whenever the list was fetched, so a
  // page left open past tip-off would keep offering picks (the POST would 409
  // - _prediction_is_open in routes/bracket.py is the real gate). Re-check the
  // start time against the shared per-second ticker so the poll closes itself
  // the moment the match starts. Unscheduled matches (NaN remaining) stay open.
  const remainingMs = useCountdownMs(scheduledAt)
  const started = scheduledAt != null && remainingMs <= 0
  const open = (prediction?.open ?? false) && !started

  // Logged out isn't a dead end: clicking either side sends the visitor
  // straight into Discord login instead of silently doing nothing, so the
  // poll doubles as a login funnel rather than a tease. `pending` is held
  // until onPick's request actually resolves (not just kicked off), so a
  // fast double-click can't fire two POSTs for the same pick.
  const handlePick = async (winner: string) => {
    if (!open || pending) return
    if (!loggedIn) {
      startDiscordLogin()
      return
    }
    setPending(true)
    try {
      await onPick(myPick === winner ? null : winner)
    } finally {
      setPending(false)
    }
  }

  const segmentSx = (picked: boolean) => ({
    py: 0.75,
    px: 1.25,
    transition: "all 0.2s ease",
    color: picked ? "primary.contrastText" : "text.primary",
    bgcolor: picked
      ? "primary.main"
      : (theme: Theme) => alpha(theme.palette.primary.main, 0.1),
    "&:hover": open
      ? {
          bgcolor: picked
            ? "primary.dark"
            : (theme: Theme) => alpha(theme.palette.primary.main, 0.22),
        }
      : undefined,
    "&.Mui-disabled": { opacity: 0.6 },
  })

  return (
    <Stack spacing={0.5} sx={{ width: "100%", maxWidth: 420 }}>
      <Stack
        direction="row"
        sx={{ alignItems: "center", justifyContent: "space-between" }}
      >
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
            display: "flex",
            alignItems: "center",
            gap: 0.5,
          }}
        >
          <HowToVoteIcon sx={{ fontSize: 14 }} /> Predict the winner
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          {total > 0
            ? `${total} prediction${total === 1 ? "" : "s"}`
            : "no predictions yet"}
        </Typography>
      </Stack>
      <Stack
        direction="row"
        sx={{
          borderRadius: 1.5,
          overflow: "hidden",
          border: (theme) => `1px solid ${theme.palette.divider}`,
        }}
      >
        <ButtonBase
          disabled={!open || pending}
          onClick={() => handlePick(playerA)}
          sx={{
            flexBasis: `${pctA}%`,
            justifyContent: "flex-start",
            ...segmentSx(myPick === playerA),
          }}
        >
          <Typography
            variant="body2"
            noWrap
            sx={{ fontWeight: myPick === playerA ? 700 : 500 }}
          >
            {playerA}
            {total > 0 && ` · ${pctA}%`}
          </Typography>
        </ButtonBase>
        <ButtonBase
          disabled={!open || pending}
          onClick={() => handlePick(playerB)}
          sx={{
            flexBasis: `${pctB}%`,
            justifyContent: "flex-end",
            ...segmentSx(myPick === playerB),
          }}
        >
          <Typography
            variant="body2"
            noWrap
            sx={{ fontWeight: myPick === playerB ? 700 : 500 }}
          >
            {total > 0 && `${pctB}% · `}
            {playerB}
          </Typography>
        </ButtonBase>
      </Stack>
      {open && !loggedIn && (
        <Typography variant="caption" sx={{ color: "text.disabled" }}>
          Click a player to log in and lock in your pick
        </Typography>
      )}
      {!open && (
        <Typography variant="caption" sx={{ color: "text.disabled" }}>
          Predictions closed
        </Typography>
      )}
    </Stack>
  )
}

function AgendaRow({
  match,
  onSchedule,
  prediction,
  onPick,
}: {
  match: BracketMatchOutput
  onSchedule: (matchId: string, scheduledAt: Date | null) => Promise<void>
  prediction: BracketMatchPrediction | undefined
  onPick: (matchId: string, winner: string | null) => Promise<void>
}) {
  const isAdmin = useIsTournamentAdmin()
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
            {match.roundName} ({shortMatchLabel(match)})
          </Typography>
          <Typography variant="subtitle1">
            {playerLabel(match, "a")} vs {playerLabel(match, "b")}
          </Typography>
        </Stack>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <Stack sx={{ alignItems: "flex-end" }} spacing={0.25}>
            {match.scheduledAt ? (
              <>
                <Typography variant="body2">
                  {formatScheduledAt(match.scheduledAt)}
                </Typography>
                <AgendaCountdown scheduledAt={match.scheduledAt} />
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
          {match.scheduledAt && (
            <Tooltip title="Add to Google Calendar">
              <IconButton
                size="small"
                component="a"
                href={googleCalendarUrl(match) ?? undefined}
                target="_blank"
                rel="noopener noreferrer"
              >
                <EventAvailableIcon fontSize="small" />
              </IconButton>
            </Tooltip>
          )}
          {isAdmin && (
            <ScheduleMatchButton match={match} onSchedule={onSchedule} />
          )}
        </Stack>
      </Stack>
      {match.playerA && match.playerB && (
        <Box sx={{ mt: 1.5 }}>
          <PredictionBar
            prediction={prediction}
            playerA={match.playerA}
            playerB={match.playerB}
            scheduledAt={match.scheduledAt ?? null}
            onPick={(winner) => onPick(match.matchId, winner)}
          />
        </Box>
      )}
    </Paper>
  )
}

// Every match that's ready to be played (both players known, no result
// recorded yet) - excludes TBD matches (still waiting on an earlier result),
// completed matches, and the Grand Final Reset when it isn't needed.
// Scheduled matches sort soonest-first; unscheduled ones (nothing to sort by)
// trail behind them. Exported so Bracket.tsx's hero banner can pick the
// single soonest match without duplicating this filter/sort.
export function agendaMatches(
  bracketData: BracketTournamentOutput | null,
): BracketMatchOutput[] {
  return (bracketData?.matches ?? [])
    .filter(
      (m) => m.status === "ready" && m.playerA !== null && m.playerB !== null,
    )
    .sort((a, b) => {
      // Unscheduled matches (nothing to sort by) sort after all scheduled
      // ones, which are soonest-first.
      if (a.scheduledAt == null) return b.scheduledAt == null ? 0 : 1
      if (b.scheduledAt == null) return -1
      return a.scheduledAt.getTime() - b.scheduledAt.getTime()
    })
}

// Completed matches, most-recently-scheduled first (there's no separate
// "completed at" timestamp, but a match's scheduled_at is a reasonable proxy
// for when it actually happened) - unscheduled completions trail behind,
// same tiebreak idiom as agendaMatches.
function recentlyCompletedMatches(
  bracketData: BracketTournamentOutput | null,
): BracketMatchOutput[] {
  return (bracketData?.matches ?? [])
    .filter((m) => m.status === "completed")
    .sort((a, b) => {
      if (a.scheduledAt == null) return b.scheduledAt == null ? 0 : 1
      if (b.scheduledAt == null) return -1
      return b.scheduledAt.getTime() - a.scheduledAt.getTime()
    })
}

// Read-only version of PredictionBar for a completed match: the winner's
// segment is highlighted (WIN_COLOR) instead of "my pick" (there's nothing
// left to click), and a line below names who called it - the payoff for
// everyone who predicted while it was still open.
function CompletedPredictionReveal({
  match,
  prediction,
}: {
  match: BracketMatchOutput
  prediction: BracketMatchPrediction | undefined
}) {
  if (!match.playerA || !match.playerB || !match.winner) return null
  const playerA = match.playerA
  const playerB = match.playerB
  const tally = prediction?.tally ?? {}
  const countA = tally[playerA] ?? 0
  const countB = tally[playerB] ?? 0
  const total = countA + countB
  const pctA = total > 0 ? Math.round((countA / total) * 100) : 50
  const pctB = 100 - pctA
  const correctPicks = prediction?.correctPicks ?? []

  const segmentSx = (isWinnerSide: boolean) => ({
    py: 0.75,
    px: 1.25,
    color: isWinnerSide ? "success.contrastText" : "text.secondary",
    bgcolor: isWinnerSide
      ? alpha(WIN_COLOR, 0.85)
      : (theme: Theme) => alpha(theme.palette.text.primary, 0.06),
  })

  return (
    <Stack spacing={0.5} sx={{ width: "100%", maxWidth: 420 }}>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
          display: "flex",
          alignItems: "center",
          gap: 0.5,
        }}
      >
        <HowToVoteIcon sx={{ fontSize: 14 }} />
        {total > 0
          ? `${total} prediction${total === 1 ? "" : "s"}`
          : "no predictions"}
      </Typography>
      <Stack
        direction="row"
        sx={{
          borderRadius: 1.5,
          overflow: "hidden",
          border: (theme) => `1px solid ${theme.palette.divider}`,
        }}
      >
        <Box
          sx={{ flexBasis: `${pctA}%`, ...segmentSx(match.winner === playerA) }}
        >
          <Typography
            variant="body2"
            noWrap
            sx={{ fontWeight: match.winner === playerA ? 700 : 500 }}
          >
            {playerA}
            {total > 0 && ` · ${pctA}%`}
          </Typography>
        </Box>
        <Box
          sx={{
            flexBasis: `${pctB}%`,
            textAlign: "right",
            ...segmentSx(match.winner === playerB),
          }}
        >
          <Typography
            variant="body2"
            noWrap
            sx={{ fontWeight: match.winner === playerB ? 700 : 500 }}
          >
            {total > 0 && `${pctB}% · `}
            {playerB}
          </Typography>
        </Box>
      </Stack>
      {correctPicks.length > 0 ? (
        <Typography
          variant="caption"
          sx={{
            color: "success.main",
            display: "flex",
            alignItems: "center",
            gap: 0.5,
          }}
        >
          <CheckCircleIcon sx={{ fontSize: 14 }} /> Called it:{" "}
          {correctPicks.join(", ")}
        </Typography>
      ) : (
        total > 0 && (
          <Typography variant="caption" sx={{ color: "text.disabled" }}>
            Nobody predicted this one
          </Typography>
        )
      )}
    </Stack>
  )
}

function CompletedMatchRow({
  match,
  prediction,
}: {
  match: BracketMatchOutput
  prediction: BracketMatchPrediction | undefined
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={0.25} sx={{ mb: 1.5 }}>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          {match.roundName} ({shortMatchLabel(match)})
        </Typography>
        <Typography variant="subtitle1">
          <Box
            component="span"
            sx={{
              fontWeight: match.winner === match.playerA ? 700 : 400,
              color: match.winner === match.playerA ? WIN_COLOR : undefined,
            }}
          >
            {playerLabel(match, "a")}
          </Box>
          {" vs "}
          <Box
            component="span"
            sx={{
              fontWeight: match.winner === match.playerB ? 700 : 400,
              color: match.winner === match.playerB ? WIN_COLOR : undefined,
            }}
          >
            {playerLabel(match, "b")}
          </Box>
        </Typography>
        {match.scoreA !== null && match.scoreB !== null && (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            {match.scoreA} – {match.scoreB}
          </Typography>
        )}
      </Stack>
      {match.playerA && match.playerB && (
        <CompletedPredictionReveal match={match} prediction={prediction} />
      )}
    </Paper>
  )
}

// Compact top-N "who's called the most winners" standings - lives right
// alongside the prediction UI itself (rather than a separate page) so the
// same anxious-refresher crowd sees the payoff without hunting for it.
// Renders nothing until there's at least one completed, predicted-on match -
// an empty leaderboard would just be a confusing "0/0 everyone" list.
function PredictionLeaderboardPanel() {
  // Best-effort side panel: no leaderboard just means no panel.
  const { data: entries = [] } = useQuery({
    queryKey: ["bracketPredictionLeaderboard"],
    queryFn: fetchBracketPredictionLeaderboard,
  })

  if (entries.length === 0) return null
  const top = entries.slice(0, 5)

  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 1.5 }}>
      <Typography
        variant="subtitle2"
        sx={{ display: "flex", alignItems: "center", gap: 0.5, mb: 1 }}
      >
        <EmojiEventsIcon fontSize="small" sx={{ color: "warning.main" }} />
        Prediction leaderboard
      </Typography>
      <Stack spacing={0.5}>
        {top.map((entry, i) => (
          <Stack
            key={entry.userName}
            direction="row"
            spacing={1}
            sx={{ alignItems: "center" }}
          >
            <Typography
              variant="body2"
              sx={{ width: 20, color: "text.secondary" }}
            >
              #{i + 1}
            </Typography>
            <Typography
              variant="body2"
              sx={{ flexGrow: 1, fontWeight: i === 0 ? 700 : 400 }}
            >
              {entry.userName}
            </Typography>
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              {entry.correct}/{entry.total}
            </Typography>
          </Stack>
        ))}
      </Stack>
    </Paper>
  )
}

// Body of the Bracket page's "Agenda" tab - takes the tournament data the
// page already fetched (see DisplayBracket's bracketData state) rather than
// fetching its own copy. `onSchedule` is DisplayBracket's handleSaveMatch,
// scoped to just the scheduled_at field (PATCH semantics leave best_of/score
// untouched).
export default function AgendaPanel({
  bracketData,
  onSchedule,
}: {
  bracketData: BracketTournamentOutput | null
  onSchedule: (matchId: string, scheduledAt: Date | null) => Promise<void>
}) {
  const matches = agendaMatches(bracketData)
  // Re-fetch whenever the underlying tournament data changes (new/reset
  // tournament, a match getting scored, reveal_at flipping) - simplest way
  // to stay in sync without hand-diffing which matches actually need it.
  const { data: predictions = {} } = useQuery({
    queryKey: ["bracketPredictions"],
    queryFn: async () => {
      const list = await fetchBracketPredictions()
      return Object.fromEntries(list.map((p) => [p.matchId, p]))
    },
    enabled: Boolean(bracketData),
  })

  // A pick is a user action, so its failure belongs in a snackbar rather than
  // a panel — unlike a read, there is nothing on screen for an error state to
  // replace. The server's reply is written straight into the cache, so no
  // refetch is needed to show the new tally.
  const { showError, errorSnackbar } = useErrorSnackbar()
  const queryClient = useQueryClient()
  const pick = useMutation({
    mutationFn: ({
      matchId,
      winner,
    }: {
      matchId: string
      winner: string | null
    }) => setBracketPrediction(matchId, winner),
    onSuccess: (updated, { matchId }) => {
      queryClient.setQueryData<Record<string, BracketMatchPrediction>>(
        ["bracketPredictions"],
        (prev) => ({ ...(prev ?? {}), [matchId]: updated }),
      )
    },
    onError: showError,
  })
  const handlePick = React.useCallback(
    async (matchId: string, winner: string | null) => {
      await pick.mutateAsync({ matchId, winner }).catch(() => {})
    },
    [pick],
  )

  const completed = recentlyCompletedMatches(bracketData)

  return (
    <>
      <PredictionLeaderboardPanel />
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
            <AgendaRow
              key={m.matchId}
              match={m}
              onSchedule={onSchedule}
              prediction={predictions[m.matchId]}
              onPick={handlePick}
            />
          ))}
        </Stack>
      )}
      {completed.length > 0 && (
        <>
          <Typography
            variant="subtitle2"
            sx={{ color: "text.secondary", mt: 3, mb: 1.5 }}
          >
            Completed
          </Typography>
          <Stack spacing={1.5}>
            {completed.map((m) => (
              <CompletedMatchRow
                key={m.matchId}
                match={m}
                prediction={predictions[m.matchId]}
              />
            ))}
          </Stack>
        </>
      )}
      {errorSnackbar}
    </>
  )
}
