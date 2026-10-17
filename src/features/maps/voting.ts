// Map-voting helpers over the generated client. The session cookie identifies
// the voter; it rides along because the client's base URL is relative.

import { queryOptions } from "@tanstack/react-query"
import {
  playerCountsApiMapVotePlayerCountsGetOptions,
  votingPlayersApiMapVotePlayersGetOptions,
} from "../../api/@tanstack/react-query.gen"
import {
  chooseMapApiMapVotePlayerCountChoosePost,
  setVoteApiMapVotePlayerCountPost,
} from "../../api/sdk.gen"
import type { ChooseMapResult, MapVotePage } from "../../api/types.gen"

export type {
  MapVotePage,
  MapVoteOption,
  ChooseMapCandidate,
  ChooseMapResult,
} from "../../api/types.gen"

export type MapVoteChoice = "vote" | "veto"

// The player-count and player lists come back as `Array<number | null>` /
// `Array<string | null>` because the backend's response models don't forbid a
// null element; nothing ever sends one, so they're filtered here rather than
// making every call site carry the null.
export const playerCountsQuery = () =>
  queryOptions({
    ...playerCountsApiMapVotePlayerCountsGetOptions(),
    select: (counts) => counts.filter((c): c is number => c != null),
  })

// In-game names that have an account — the selectable draw participants.
export const votingPlayersQuery = () =>
  queryOptions({
    ...votingPlayersApiMapVotePlayersGetOptions(),
    select: (players) => players.filter((p): p is string => p != null),
  })

// Runs the authoritative weighted-random draw on the backend, counting only
// the votes of the given participating players.
export async function chooseMap(
  playerCount: number,
  players: string[],
): Promise<ChooseMapResult> {
  const { data } = await chooseMapApiMapVotePlayerCountChoosePost({
    path: { player_count: playerCount },
    body: { players },
  })
  return data
}

export async function setVote(
  playerCount: number,
  mapName: string,
  choice: MapVoteChoice | null,
): Promise<MapVotePage> {
  const { data } = await setVoteApiMapVotePlayerCountPost({
    path: { player_count: playerCount },
    body: { map_name: mapName, choice },
  })
  return data
}
