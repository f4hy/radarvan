import EditCalendarIcon from "@mui/icons-material/EditCalendar"
import Button from "@mui/material/Button"
import IconButton from "@mui/material/IconButton"
import Paper from "@mui/material/Paper"
import Popover from "@mui/material/Popover"
import Stack from "@mui/material/Stack"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import { DateTimePicker } from "@mui/x-date-pickers/DateTimePicker"
import dayjs, { Dayjs } from "dayjs"
import * as React from "react"
import { useIsTournamentAdmin } from "./AuthContext"
import { BracketMatchOutput, BracketTournamentOutput } from "./bracketApi"
import {
  formatCountdown,
  formatScheduledAt,
  playerLabel,
  shortMatchLabel,
  useCountdownMs,
} from "./bracketFormat"

// Uses the same shared per-second countdown ticker as Bracket.tsx's
// RevealCountdown, so only this row re-renders each second, not the whole
// list.
function AgendaCountdown({ scheduledAt }: { scheduledAt: string }) {
  const remaining = useCountdownMs(scheduledAt)
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

// Admin-only "set the time" control for one row - a calendar icon (rather
// than a labelled button) so it reads as an admin affordance at a glance,
// same idiom as MatchBox's edit-pencil icon in Bracket.tsx, which is also
// only ever rendered for admins. Opens a popover with a full calendar +
// clock DateTimePicker (see App.tsx's LocalizationProvider) rather than the
// bare native datetime-local input the removed MatchEditor date field and
// the tournament reveal-time dialog used to rely on.
function ScheduleMatchButton({
  match,
  onSchedule,
}: {
  match: BracketMatchOutput
  onSchedule: (matchId: string, scheduledAt: string | null) => Promise<void>
}) {
  const [anchorEl, setAnchorEl] = React.useState<HTMLElement | null>(null)
  const [value, setValue] = React.useState<Dayjs | null>(null)
  const [saving, setSaving] = React.useState(false)

  const handleOpen = (e: React.MouseEvent<HTMLElement>) => {
    setValue(match.scheduled_at ? dayjs(match.scheduled_at) : null)
    setAnchorEl(e.currentTarget)
  }
  const handleClose = () => setAnchorEl(null)

  const commit = async (scheduledAt: string | null) => {
    setSaving(true)
    try {
      await onSchedule(match.match_id, scheduledAt)
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
          <DateTimePicker
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
            {match.scheduled_at && (
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
              onClick={() => commit(value ? value.toISOString() : null)}
            >
              Save
            </Button>
          </Stack>
        </Stack>
      </Popover>
    </>
  )
}

function AgendaRow({
  match,
  onSchedule,
}: {
  match: BracketMatchOutput
  onSchedule: (matchId: string, scheduledAt: string | null) => Promise<void>
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
            {match.round_name} ({shortMatchLabel(match)})
          </Typography>
          <Typography variant="subtitle1">
            {playerLabel(match, "a")} vs {playerLabel(match, "b")}
          </Typography>
        </Stack>
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
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
          {isAdmin && (
            <ScheduleMatchButton match={match} onSchedule={onSchedule} />
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
  return (bracketData?.matches ?? [])
    .filter(
      (m) => m.status === "ready" && m.player_a !== null && m.player_b !== null,
    )
    .sort((a, b) => {
      // Unscheduled matches (nothing to sort by) sort after all scheduled
      // ones, which are soonest-first.
      if (a.scheduled_at === null) return b.scheduled_at === null ? 0 : 1
      if (b.scheduled_at === null) return -1
      return (
        new Date(a.scheduled_at).getTime() - new Date(b.scheduled_at).getTime()
      )
    })
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
  onSchedule: (matchId: string, scheduledAt: string | null) => Promise<void>
}) {
  const matches = agendaMatches(bracketData)

  return (
    <>
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
            <AgendaRow key={m.match_id} match={m} onSchedule={onSchedule} />
          ))}
        </Stack>
      )}
    </>
  )
}
