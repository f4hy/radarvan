// 1v1 bracket tournament helpers. Like auth.ts/voting.ts these use
// relative-URL, same-origin fetch so the session cookie identifies the admin
// (the generated API-key client in Client.ts is cross-origin in dev and
// can't carry the cookie).

import { BracketMatchGames, BracketMatchGamesFromJSON } from "./api"

export type BracketSide = "W" | "L" | "GF"
export type BracketMatchStatus =
  | "pending"
  | "ready"
  | "completed"
  | "not_applicable"

export interface BracketPlayerEntry {
  seed: number
  player_name: string
}

// Where a match's two slots come from — a raw seed number, or the
// winner/loser of an earlier match. Drives the frontend's bracket-tree
// layout so it doesn't need its own copy of the (now player-count-dependent)
// topology-generation logic.
export type MatchSource =
  | { kind: "seed"; seed: number }
  | { kind: "winner"; match_id: string }
  | { kind: "loser"; match_id: string }

export interface BracketMatchOutput {
  match_id: string
  bracket: BracketSide
  round_number: number
  round_name: string
  player_a: string | null
  player_b: string | null
  scheduled_at: string | null
  best_of: number | null
  score_a: number | null
  score_b: number | null
  winner: string | null
  status: BracketMatchStatus
  source_a: MatchSource
  source_b: MatchSource
}

export interface BracketTournamentOutput {
  // Alphabetical roster (names only) - always populated regardless of
  // `revealed`, unlike `players`/`matches[*].player_a/b`/`bye_advances`/
  // `champion`/`runner_up`, which the backend withholds pre-reveal.
  participant_names: string[]
  players: BracketPlayerEntry[]
  matches: BracketMatchOutput[]
  bye_advances: BracketPlayerEntry[]
  champion: string | null
  runner_up: string | null
  needs_reset: boolean
  // Server-computed - true once reveal_at has passed (or it's unset).
  revealed: boolean
  reveal_at: string | null
}

// All fields optional: the backend applies PATCH semantics (only keys
// present in the JSON body change - see set_bracket_match) so a caller that
// only wants to touch e.g. scheduled_at can omit best_of/score_a/score_b
// entirely rather than resending their current values.
export interface SetBracketMatchRequest {
  scheduled_at?: string | null
  best_of?: 3 | 5 | 7 | 9 | null
  score_a?: number | null
  score_b?: number | null
}

export interface SetBracketRevealAtRequest {
  reveal_at: string | null
}

// Community "who wins this match" prediction tally - a hype feature, not
// the authoritative result (BracketMatchOutput.winner is). `open` is false
// once the match started (scheduled_at passed) or was scored, so the UI can
// stop accepting new picks without needing its own clock/status logic.
export interface BracketMatchPrediction {
  match_id: string
  tally: Record<string, number>
  my_pick: string | null
  open: boolean
  // Display names of users who predicted the actual winner. Only populated
  // once the match is completed (null beforehand); an empty array means the
  // match completed but nobody called it, not "not completed yet".
  correct_picks: string[] | null
}

// One row of the "who's called the most winners" standings - only counts
// predictions against matches that have completed.
export interface BracketPredictionLeaderboardEntry {
  user_name: string
  correct: number
  total: number
}

export interface MapPlayerWL {
  player: string
  wins: number
  losses: number
}

// One map and everyone who played it in the tournament. `map_key` is the
// backend's normalized join key (path, ".map" suffix, whitespace and case
// stripped - see replay_files.map_key); match it with mapKey() below rather
// than comparing display names, which differ in case between the map pool
// and match history. `total_games` counts games, so it is not the sum of the
// per-player records.
export interface MapPlayerRecords {
  map_key: string
  map_name: string
  total_games: number
  players: MapPlayerWL[]
}

// TS twin of radarvan/replay_files.py's map_key - the two must agree for a
// pool map name to line up with the map recorded on a match.
export function mapKey(name: string): string {
  const base = name.split("/").pop() ?? name
  return base
    .replace(/\.map$/, "")
    .replace(/\s+/g, "")
    .toLowerCase()
}

async function handle<T>(resp: Response, action: string): Promise<T> {
  if (!resp.ok) {
    let detail = `${action} failed (${resp.status})`
    try {
      const body = (await resp.json()) as { detail?: string }
      if (body?.detail) detail = body.detail
    } catch {
      // non-JSON error body; keep the generic message
    }
    throw new Error(detail)
  }
  return (await resp.json()) as T
}

export async function fetchBracket(
  preview = false,
): Promise<BracketTournamentOutput | null> {
  const resp = await fetch(`/api/bracket${preview ? "?preview=true" : ""}`, {
    credentials: "same-origin",
  })
  return handle<BracketTournamentOutput | null>(resp, "get bracket")
}

export async function fetchEligiblePlayers(): Promise<string[]> {
  const resp = await fetch("/api/bracket_eligible_players", {
    credentials: "same-origin",
  })
  return handle<string[]>(resp, "eligible players")
}

export async function createBracket(
  players: BracketPlayerEntry[],
): Promise<BracketTournamentOutput> {
  const resp = await fetch("/api/bracket", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ players }),
  })
  return handle<BracketTournamentOutput>(resp, "create bracket")
}

export async function setBracketRevealAt(
  req: SetBracketRevealAtRequest,
): Promise<BracketTournamentOutput> {
  const resp = await fetch("/api/bracket/reveal_at", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  })
  return handle<BracketTournamentOutput>(resp, "set reveal time")
}

export async function setBracketMatch(
  matchId: string,
  req: SetBracketMatchRequest,
): Promise<BracketTournamentOutput> {
  const resp = await fetch(`/api/bracket/${encodeURIComponent(matchId)}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(req),
  })
  return handle<BracketTournamentOutput>(resp, "set match")
}

// Set the games played for a bracket match (tournament admin only). Written
// as `manual` links the backend's auto-detector won't overwrite. Goes through
// same-origin fetch for the session cookie, then reuses the generated
// converter so the MatchInfos come back in the same camelCase shape every
// other component consumes.
export async function setBracketGames(
  matchId: string,
  gameMatchIds: number[],
): Promise<BracketMatchGames> {
  const resp = await fetch(
    `/api/bracket_games/${encodeURIComponent(matchId)}`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ match_ids: gameMatchIds }),
    },
  )
  return BracketMatchGamesFromJSON(await handle<unknown>(resp, "set games"))
}

// Each map's per-player records over the tournament's linked games. Empty
// before the bracket is revealed (and same-origin so an admin previewing
// early is recognized by their session cookie).
export async function fetchBracketMapRecords(): Promise<MapPlayerRecords[]> {
  const resp = await fetch("/api/bracket_map_records", {
    credentials: "same-origin",
  })
  return handle<MapPlayerRecords[]>(resp, "get map records")
}

export async function fetchBracketPredictions(): Promise<
  BracketMatchPrediction[]
> {
  const resp = await fetch("/api/bracket_predictions", {
    credentials: "same-origin",
  })
  return handle<BracketMatchPrediction[]>(resp, "get predictions")
}

export async function fetchBracketPredictionLeaderboard(): Promise<
  BracketPredictionLeaderboardEntry[]
> {
  const resp = await fetch("/api/bracket_prediction_leaderboard", {
    credentials: "same-origin",
  })
  return handle<BracketPredictionLeaderboardEntry[]>(resp, "get leaderboard")
}

// `predictedWinner: null` clears the caller's pick for this match.
export async function setBracketPrediction(
  matchId: string,
  predictedWinner: string | null,
): Promise<BracketMatchPrediction> {
  const resp = await fetch(
    `/api/bracket_predictions/${encodeURIComponent(matchId)}`,
    {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ predicted_winner: predictedWinner }),
    },
  )
  return handle<BracketMatchPrediction>(resp, "set prediction")
}
