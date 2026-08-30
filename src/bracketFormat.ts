// Pure bracket-display formatting shared between Bracket.tsx (the bracket
// tree / match editor) and Agenda.tsx (the Agenda tab) - kept in their own
// module, rather than exported from Bracket.tsx, so Agenda.tsx doesn't need
// a circular import back into the page that renders it.
import * as React from "react"
import type { BracketMatchOutput } from "./bracketApi"

// Losers Round N isn't listed here since N is dynamic — see roundCode's fallback.
const ROUND_CODE: Record<string, { code: string; singleton: boolean }> = {
  "Winners Round 1": { code: "WR1", singleton: false },
  "Winners Round 2": { code: "WR2", singleton: false },
  "Winners Semifinal": { code: "WSF", singleton: false },
  "Winners Final": { code: "WF", singleton: true },
  "Losers Final": { code: "LF", singleton: true },
  "Grand Final": { code: "GF", singleton: true },
  "Grand Final Reset": { code: "GFR", singleton: true },
}

function roundCode(match: BracketMatchOutput): {
  code: string
  singleton: boolean
} {
  return (
    ROUND_CODE[match.roundName] ??
    (match.bracket === "L"
      ? { code: `LR${match.roundNumber}`, singleton: false }
      : { code: match.roundName, singleton: false })
  )
}

// match_id's trailing "-N" is already the match's 1-based position within
// its round (WB1-1, WB1-2, ..., LB2-1, ...) — reuse it rather than deriving
// position independently, so the letter always agrees with the match_id.
function indexToLetter(idx: number): string {
  return String.fromCharCode("a".charCodeAt(0) + idx - 1)
}

export function shortMatchLabel(match: BracketMatchOutput): string {
  const { code, singleton } = roundCode(match)
  if (singleton) return code
  const suffix = match.matchId.match(/-(\d+)$/)
  const idx = suffix ? Number(suffix[1]) : 1
  return `${code}-${indexToLetter(idx)}`
}

// Shared by Bracket.tsx's buildChild (leaf-ref label) and playerLabel's TBD
// fallback below: both describe an unresolved slot the same way ("Winner of
// WR1-a"), resolvable immediately from a match's source_a/source_b - no
// games need to have been played yet.
export function sourceMatchLabel(
  matchId: string,
  matchesById: Map<string, BracketMatchOutput>,
): string {
  const refMatch = matchesById.get(matchId)
  return refMatch ? shortMatchLabel(refMatch) : matchId
}

// `matchesById` is optional: passing it turns an unresolved slot's fallback
// from a bare "TBD" into "Winner of WR1-a" / "Loser of WR1-a" — resolvable
// immediately from source_a/source_b, no games need to have been played.
// Omitted by the few callers (MatchEditor, dialog title) that only need a
// short label and don't have matchesById in scope.
export function playerLabel(
  match: BracketMatchOutput,
  side: "a" | "b",
  matchesById?: Map<string, BracketMatchOutput>,
): string {
  const name = side === "a" ? match.playerA : match.playerB
  if (name) return name
  if (match.status === "not_applicable") return "—"
  const source = side === "a" ? match.sourceA : match.sourceB
  if (matchesById && source.kind !== "seed") {
    const refLabel = sourceMatchLabel(source.matchId, matchesById)
    return `${source.kind === "winner" ? "Winner" : "Loser"} of ${refLabel}`
  }
  return "TBD"
}

// Compact "Aug 5, 3:00 PM" rendering for a match card's caption / the
// Agenda list - full date + time, in the viewer's local timezone, without
// the verbosity of a full toLocaleString() (no year, no seconds).
export function formatScheduledAt(at: Date): string {
  return at.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  })
}

// Renders a countdown as HH:MM:SS, with a "Nd " day prefix once the
// remaining time crosses a day - the tournament reveal is set days out, and
// nobody needs second-precision digits for a multi-day wait.
export function formatCountdown(remainingMs: number): string {
  const totalSeconds = Math.max(Math.floor(remainingMs / 1000), 0)
  const days = Math.floor(totalSeconds / 86400)
  const hours = Math.floor((totalSeconds % 86400) / 3600)
  const minutes = Math.floor((totalSeconds % 3600) / 60)
  const seconds = totalSeconds % 60
  const pad = (n: number) => String(n).padStart(2, "0")
  const clock = `${pad(hours)}:${pad(minutes)}:${pad(seconds)}`
  return days > 0 ? `${days}d ${clock}` : clock
}

// "YYYYMMDDTHHMMSSZ" - Google Calendar's `dates=` param format, UTC.
function toGoogleCalendarStamp(at: Date): string {
  return at.toISOString().replace(/[-:]|\.\d{3}/g, "")
}

// Default event length: match durations vary with best_of and neither side
// tracks actual play time up front, so a fixed 1-hour block is a reasonable
// calendar placeholder rather than an attempt at precision.
const DEFAULT_EVENT_DURATION_MS = 60 * 60 * 1000

// "Add to Google Calendar" link for one Agenda row - opens Google's event
// creation UI pre-filled, no API/auth needed since it's just a URL the
// browser navigates to.
export function googleCalendarUrl(match: BracketMatchOutput): string | null {
  if (!match.scheduledAt) return null
  const start = match.scheduledAt
  const end = new Date(start.getTime() + DEFAULT_EVENT_DURATION_MS)
  const title = `${playerLabel(match, "a")} vs ${playerLabel(match, "b")} (${shortMatchLabel(match)})`
  const details = [
    match.roundName,
    match.bestOf ? `Best of ${match.bestOf}` : null,
  ]
    .filter(Boolean)
    .join(" - ")
  const params = new URLSearchParams({
    action: "TEMPLATE",
    text: title,
    dates: `${toGoogleCalendarStamp(start)}/${toGoogleCalendarStamp(end)}`,
    details,
  })
  return `https://calendar.google.com/calendar/render?${params.toString()}`
}

// Milliseconds remaining until `target`, ticking once a second - shared by
// RevealCountdown (Bracket.tsx) and AgendaCountdown (Agenda.tsx). Own
// interval (rather than a `nowMs` prop from the parent) so only the
// component calling this re-renders each second, not its parent.
// An unscheduled match has no target, and callers rely on that yielding NaN:
// `remaining <= 0` is false for NaN, which is what keeps an unscheduled match's
// prediction poll open. That used to be spelled `new Date("")` at the call
// site; it's explicit here instead.
export function useCountdownMs(target: Date | null | undefined): number {
  const [nowMs, setNowMs] = React.useState(() => Date.now())
  React.useEffect(() => {
    const id = setInterval(() => setNowMs(Date.now()), 1000)
    return () => clearInterval(id)
  }, [])
  return target == null ? Number.NaN : target.getTime() - nowMs
}
