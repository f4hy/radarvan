// Map-voting helpers. Like auth.ts these use relative-URL, same-origin fetch so
// the session cookie identifies the voter (the generated API-key client in
// Client.ts is cross-origin in dev and can't carry the cookie).

export type MapVoteChoice = "vote" | "veto"

export interface MapVoteOption {
  map_name: string
  game_count: number
  last_played: string | null
  days_since_last_played: number | null
  my_choice: MapVoteChoice | null
}

export interface MapVotePage {
  player_count: number
  logged_in: boolean
  vote_limit: number
  veto_limit: number
  votes_used: number
  vetoes_used: number
  maps: MapVoteOption[]
}

export async function fetchPlayerCounts(): Promise<number[]> {
  const resp = await fetch("/api/map_vote/player_counts", {
    credentials: "same-origin",
  })
  if (!resp.ok) throw new Error(`player_counts failed (${resp.status})`)
  return (await resp.json()) as number[]
}

export async function fetchVotePage(playerCount: number): Promise<MapVotePage> {
  const resp = await fetch(`/api/map_vote/${playerCount}`, {
    credentials: "same-origin",
  })
  if (!resp.ok) throw new Error(`map_vote failed (${resp.status})`)
  return (await resp.json()) as MapVotePage
}

export interface ChooseMapCandidate {
  map_name: string
  votes: number
  vetoes: number
  weight: number
  eligible: boolean
}

export interface ChooseMapResult {
  player_count: number
  chosen_map: string | null
  candidates: ChooseMapCandidate[]
}

// In-game names that have an account — the selectable draw participants.
export async function fetchVotingPlayers(): Promise<string[]> {
  const resp = await fetch("/api/map_vote/players", {
    credentials: "same-origin",
  })
  if (!resp.ok) throw new Error(`players failed (${resp.status})`)
  return (await resp.json()) as string[]
}

// Runs the authoritative weighted-random draw on the backend, counting only
// the votes of the given participating players.
export async function chooseMap(
  playerCount: number,
  players: string[],
): Promise<ChooseMapResult> {
  const resp = await fetch(`/api/map_vote/${playerCount}/choose`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ players }),
  })
  if (!resp.ok) throw new Error(`choose failed (${resp.status})`)
  return (await resp.json()) as ChooseMapResult
}

export async function setVote(
  playerCount: number,
  mapName: string,
  choice: MapVoteChoice | null,
): Promise<MapVotePage> {
  const resp = await fetch(`/api/map_vote/${playerCount}`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ map_name: mapName, choice }),
  })
  if (!resp.ok) {
    // Surface the server's detail (e.g. the 409 limit message) when present.
    let detail = `Vote failed (${resp.status})`
    try {
      const body = (await resp.json()) as { detail?: string }
      if (body?.detail) detail = body.detail
    } catch {
      // non-JSON error body; keep the generic message
    }
    throw new Error(detail)
  }
  return (await resp.json()) as MapVotePage
}
