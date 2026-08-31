// 1v1 bracket tournament helpers over the generated client.
//
// The session cookie identifies the tournament admin; `Client.ts` sends it
// because the client's base path is relative and so same-origin.
// `scheduledAt` and `revealAt` arrive as `Date`, not an ISO string, because
// the generated converters parse them.

import { BracketClient } from "./clients/bracket"
import type {
  BracketMatchGames,
  BracketMatchPrediction,
  BracketPlayerEntry,
  BracketPredictionLeaderboardEntry,
  BracketTournamentOutput,
  MapPlayerRecords,
  SetBracketMatchRequest,
  SourceA,
  SourceB,
} from "./api"

export type {
  BracketMatchOutput,
  BracketMatchPrediction,
  BracketPlayerEntry,
  BracketPredictionLeaderboardEntry,
  BracketTournamentOutput,
  MapPlayerRecords,
  MapPlayerWL,
  SetBracketMatchRequest,
  SetBracketRevealAtRequest,
} from "./api"

// The generator emits a separate (structurally identical) union per slot;
// callers that just want "where does this slot come from" take either.
export type MatchSource = SourceA | SourceB

// `bracket` and `status` are generated as enum objects plus a value union; the
// value union is what call sites compare against ("W", "completed", …).
export type {
  BracketMatchOutputBracketEnum as BracketSide,
  BracketMatchOutputStatusEnum as BracketMatchStatus,
} from "./api"

// TS twin of radarvan/replay_files.py's map_key - the two must agree for a
// pool map name to line up with the map recorded on a match.
export function mapKey(name: string): string {
  const base = name.split("/").pop() ?? name
  return base
    .replace(/\.map$/, "")
    .replace(/\s+/g, "")
    .toLowerCase()
}

export async function fetchBracket(
  preview = false,
): Promise<BracketTournamentOutput | null> {
  return BracketClient.getBracketApiBracketGet({ preview })
}

export async function fetchEligiblePlayers(): Promise<string[]> {
  const players =
    await BracketClient.eligiblePlayersApiBracketEligiblePlayersGet()
  return players.filter((p): p is string => p != null)
}

export async function createBracket(
  players: BracketPlayerEntry[],
): Promise<BracketTournamentOutput> {
  return BracketClient.createBracketApiBracketPost({
    createBracketRequest: { players },
  })
}

export async function setBracketRevealAt(
  revealAt: Date | null,
): Promise<BracketTournamentOutput> {
  return BracketClient.setBracketRevealAtApiBracketRevealAtPost({
    setBracketRevealAtRequest: { revealAt },
  })
}

// PATCH semantics: only the keys present in `req` change. The generated
// serializer emits every field, but `JSON.stringify` drops the ones left
// `undefined`, so omitting a key still means "leave it alone" and passing an
// explicit `null` still means "clear it" — same contract as before.
export async function setBracketMatch(
  matchId: string,
  req: SetBracketMatchRequest,
): Promise<BracketTournamentOutput> {
  return BracketClient.setBracketMatchApiBracketMatchIdPost({
    matchId,
    setBracketMatchRequest: req,
  })
}

// Set the games played for a bracket match (tournament admin only). Written
// as `manual` links the backend's auto-detector won't overwrite.
export async function setBracketGames(
  matchId: string,
  gameMatchIds: number[],
): Promise<BracketMatchGames> {
  return BracketClient.setBracketGamesApiBracketGamesMatchIdPost({
    matchId,
    setBracketGamesRequest: { matchIds: gameMatchIds },
  })
}

// Each map's per-player records over the tournament's linked games. Empty
// before the bracket is revealed (the session cookie is what lets an admin
// previewing early see anything).
export async function fetchBracketMapRecords(): Promise<MapPlayerRecords[]> {
  return BracketClient.getBracketMapRecordsApiBracketMapRecordsGet()
}

export async function fetchBracketPredictions(): Promise<
  BracketMatchPrediction[]
> {
  return BracketClient.getBracketPredictionsApiBracketPredictionsGet()
}

export async function fetchBracketPredictionLeaderboard(): Promise<
  BracketPredictionLeaderboardEntry[]
> {
  return BracketClient.getBracketPredictionLeaderboardApiBracketPredictionLeaderboardGet()
}

// `predictedWinner: null` clears the caller's pick for this match.
export async function setBracketPrediction(
  matchId: string,
  predictedWinner: string | null,
): Promise<BracketMatchPrediction> {
  return BracketClient.setBracketPredictionApiBracketPredictionsMatchIdPost({
    matchId,
    setMatchPredictionRequest: { predictedWinner },
  })
}
