// Map-voting helpers over the generated client.
//
// The session cookie identifies the voter; `Client.ts` sends it because the
// client's base path is relative and so same-origin. The response types are the
// generated ones — the hand-written snake_case copies that used to live here
// duplicated `MapVotePage`, `MapVoteOption`, `ChooseMapCandidate` and
// `ChooseMapResult`, all of which the generator already emits from the same
// backend models.

import { MapVoteClient } from "./Client"
import type { MapVotePage, ChooseMapResult } from "./api"

export type {
  MapVotePage,
  MapVoteOption,
  ChooseMapCandidate,
  ChooseMapResult,
} from "./api"

export type MapVoteChoice = "vote" | "veto"

// The player-count and player lists come back as `Array<number | null>` /
// `Array<string | null>` because the backend's response models don't forbid a
// null element; nothing ever sends one, so they're filtered here rather than
// making every call site carry the null.
export async function fetchPlayerCounts(): Promise<number[]> {
  const counts = await MapVoteClient.playerCountsApiMapVotePlayerCountsGet()
  return counts.filter((c): c is number => c != null)
}

export async function fetchVotePage(playerCount: number): Promise<MapVotePage> {
  return MapVoteClient.getVotePageApiMapVotePlayerCountGet({ playerCount })
}

// In-game names that have an account — the selectable draw participants.
export async function fetchVotingPlayers(): Promise<string[]> {
  const players = await MapVoteClient.votingPlayersApiMapVotePlayersGet()
  return players.filter((p): p is string => p != null)
}

// Runs the authoritative weighted-random draw on the backend, counting only
// the votes of the given participating players.
export async function chooseMap(
  playerCount: number,
  players: string[],
): Promise<ChooseMapResult> {
  return MapVoteClient.chooseMapApiMapVotePlayerCountChoosePost({
    playerCount,
    chooseMapRequest: { players },
  })
}

export async function setVote(
  playerCount: number,
  mapName: string,
  choice: MapVoteChoice | null,
): Promise<MapVotePage> {
  return MapVoteClient.setVoteApiMapVotePlayerCountPost({
    playerCount,
    setMapVoteRequest: { mapName, choice },
  })
}
