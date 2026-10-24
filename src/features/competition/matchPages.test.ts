import { describe, expect, it } from "vitest"
import type { BracketMatchOutput } from "./bracketApi"
import { matchPageLink } from "./matchPages"

const match = (
  match_id: string,
  player_a: string | null,
  player_b: string | null,
  status: BracketMatchOutput["status"] = "ready",
) => ({ match_id, player_a, player_b, status }) as BracketMatchOutput

describe("matchPageLink", () => {
  it("finds a preview in either player order", () => {
    const href = "/hype/modus-wildcard/index.html"
    expect(matchPageLink(match("LB5-1", "Modus", "WildCard"))).toEqual({
      kind: "preview",
      href,
    })
    expect(matchPageLink(match("LB5-1", "WildCard", "Modus"))?.href).toBe(href)
  })

  it("switches a played match to its recap", () => {
    expect(
      matchPageLink(match("LB4-1", "Modus", "Tytan", "completed")),
    ).toEqual({ kind: "recap", href: "/recap/modus-tytan/index.html" })
  })

  it("drops the preview once played when there's no recap", () => {
    expect(
      matchPageLink(match("LB3-1", "CoreDawg", "Modus", "completed")),
    ).toBeNull()
  })

  it("needs both the match and the pair to agree", () => {
    expect(matchPageLink(match("LB5-1", "Modus", "Gorn"))).toBeNull()
    expect(matchPageLink(match("GF-1", "Modus", "WildCard"))).toBeNull()
    expect(matchPageLink(match("LB5-1", "Modus", null))).toBeNull()
  })
})
