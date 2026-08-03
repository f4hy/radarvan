// 1v1 bracket tournament helpers. Like auth.ts/voting.ts these use
// relative-URL, same-origin fetch so the session cookie identifies the admin
// (the generated API-key client in Client.ts is cross-origin in dev and
// can't carry the cookie).

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
  total_predictions: number
  my_pick: string | null
  open: boolean
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

export async function fetchBracketPredictions(): Promise<
  BracketMatchPrediction[]
> {
  const resp = await fetch("/api/bracket_predictions", {
    credentials: "same-origin",
  })
  return handle<BracketMatchPrediction[]>(resp, "get predictions")
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
