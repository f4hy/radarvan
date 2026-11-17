import { describe, expect, it } from "vitest"
import type { BracketFactionGame } from "../../api/types.gen"
import { General } from "../../lib/General"
import { matchups, setLoserRecords } from "./factionMatchups"

let nextId = 1
function game(
  winner: string,
  winnerGeneral: General,
  loser: string,
  loserGeneral: General,
  winnerLostSet: boolean | null = false,
): BracketFactionGame {
  return {
    matchId: nextId++,
    stage: "WB1-1",
    winner,
    winnerGeneral,
    loser,
    loserGeneral,
    winnerLostSet,
  }
}

describe("matchups", () => {
  it("folds both orientations of a pairing into one row", () => {
    const rows = matchups(
      [
        game("Gorn", General.STEALTH, "Modus", General.LASER),
        game("Modus", General.LASER, "Gorn", General.STEALTH, true),
        game("Neo", General.LASER, "Syn", General.STEALTH),
      ],
      "general",
    )
    expect(rows).toHaveLength(1)
    // LASER precedes STEALTH in faction order, so it is side a.
    expect(rows[0]).toMatchObject({
      a: General.LASER,
      b: General.STEALTH,
      aWins: 2,
      bWins: 1,
    })
  })

  it("groups generals into factions at the faction grain", () => {
    const rows = matchups(
      [
        game("Gorn", General.AIR, "Modus", General.TOXIN),
        game("Gorn", General.DEMO, "Modus", General.LASER),
        game("Gorn", General.NUKE, "Modus", General.TANK),
      ],
      "faction",
    )
    expect(rows.map((r) => [r.a, r.b, r.aWins, r.bWins])).toEqual([
      ["USA", "GLA", 1, 1],
      ["CHINA", "CHINA", 1, 0],
    ])
  })
})

describe("setLoserRecords", () => {
  it("counts the set loser's side whether they won or lost the game", () => {
    const rows = setLoserRecords(
      [
        // Skip lost the set but won this game on Air.
        game("Skip", General.AIR, "Neo", General.TANK, true),
        // Skip lost this game on Air too.
        game("Neo", General.NUKE, "Skip", General.AIR, false),
        // Syn lost the set; lost this game on Toxin.
        game("Neo", General.AIR, "Syn", General.TOXIN, false),
        // Unscored set: ignored.
        game("Syn", General.AIR, "Neo", General.AIR, null),
      ],
      "general",
    )
    expect(rows).toEqual([
      {
        side: General.AIR,
        wins: 1,
        losses: 1,
        players: [{ player: "Skip", wins: 1, losses: 1 }],
      },
      {
        side: General.TOXIN,
        wins: 0,
        losses: 1,
        players: [{ player: "Syn", wins: 0, losses: 1 }],
      },
    ])
  })
})
