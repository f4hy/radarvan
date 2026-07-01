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

export interface BracketMatchOutput {
  match_id: string
  bracket: BracketSide
  round_number: number
  round_name: string
  player_a: string | null
  player_b: string | null
  scheduled_date: string | null
  best_of: number | null
  score_a: number | null
  score_b: number | null
  winner: string | null
  status: BracketMatchStatus
}

export interface BracketTournamentOutput {
  players: BracketPlayerEntry[]
  matches: BracketMatchOutput[]
  bye_advances: BracketPlayerEntry[]
  champion: string | null
  runner_up: string | null
  needs_reset: boolean
}

export interface SetBracketMatchRequest {
  scheduled_date: string | null
  best_of: 3 | 5 | 7 | 9 | null
  score_a: number | null
  score_b: number | null
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

export async function fetchBracket(): Promise<BracketTournamentOutput | null> {
  const resp = await fetch("/api/bracket", { credentials: "same-origin" })
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
