// 1v1 bracket tournament helpers over the generated client.
//
// The session cookie identifies the tournament admin; it rides along because
// the client's base URL is relative. `scheduled_at` and `reveal_at` arrive as
// `Date`, not an ISO string, because the response transformers parse them.

import { queryOptions } from "@tanstack/react-query"
import {
  eligiblePlayersApiBracketEligiblePlayersGetOptions,
  getBracketApiBracketGetOptions,
  getBracketApiBracketGetQueryKey,
} from "../../api/@tanstack/react-query.gen"
import {
  createBracketApiBracketPost,
  setBracketGamesApiBracketGamesMatchIdPost,
  setBracketMatchApiBracketMatchIdPost,
  setBracketPredictionApiBracketPredictionsMatchIdPost,
  setBracketRevealAtApiBracketRevealAtPost,
} from "../../api/sdk.gen"
import type {
  BracketMatchGames,
  BracketMatchOutput,
  BracketMatchPrediction,
  BracketPlayerEntry,
  BracketTournamentOutput,
  SetBracketMatchRequest,
} from "../../api/types.gen"

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
} from "../../api/types.gen"

// Where a slot's player comes from; `source_a` and `source_b` share the shape.
export type MatchSource = BracketMatchOutput["source_a"]
export type BracketSide = BracketMatchOutput["bracket"]
export type BracketMatchStatus = BracketMatchOutput["status"]

export const bracketQuery = (preview: boolean) =>
  getBracketApiBracketGetOptions({ query: { preview } })

export const bracketQueryKey = (preview: boolean) =>
  getBracketApiBracketGetQueryKey({ query: { preview } })

export const eligiblePlayersQuery = () =>
  queryOptions({
    ...eligiblePlayersApiBracketEligiblePlayersGetOptions(),
    select: (players) => players.filter((p): p is string => p != null),
  })

export async function createBracket(
  players: BracketPlayerEntry[],
): Promise<BracketTournamentOutput> {
  const { data } = await createBracketApiBracketPost({ body: { players } })
  return data
}

export async function setBracketRevealAt(
  revealAt: Date | null,
): Promise<BracketTournamentOutput> {
  const { data } = await setBracketRevealAtApiBracketRevealAtPost({
    body: { reveal_at: revealAt },
  })
  return data
}

// PATCH semantics: only the keys present in `req` change. The body goes out
// through `JSON.stringify`, which drops keys left `undefined`, so omitting a
// key means "leave it alone" and an explicit `null` means "clear it".
export async function setBracketMatch(
  matchId: string,
  req: SetBracketMatchRequest,
): Promise<BracketTournamentOutput> {
  const { data } = await setBracketMatchApiBracketMatchIdPost({
    path: { match_id: matchId },
    body: req,
  })
  return data
}

// Set the games played for a bracket match (tournament admin only). Written
// as `manual` links the backend's auto-detector won't overwrite.
export async function setBracketGames(
  matchId: string,
  gameMatchIds: number[],
): Promise<BracketMatchGames> {
  const { data } = await setBracketGamesApiBracketGamesMatchIdPost({
    path: { match_id: matchId },
    body: { match_ids: gameMatchIds },
  })
  return data
}

// `predictedWinner: null` clears the caller's pick for this match.
export async function setBracketPrediction(
  matchId: string,
  predictedWinner: string | null,
): Promise<BracketMatchPrediction> {
  const { data } = await setBracketPredictionApiBracketPredictionsMatchIdPost({
    path: { match_id: matchId },
    body: { predicted_winner: predictedWinner },
  })
  return data
}
