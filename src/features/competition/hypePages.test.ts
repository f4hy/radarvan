import { describe, expect, it } from "vitest"
import type { BracketMatchOutput } from "./bracketApi"
import { hypePageHref } from "./hypePages"

const match = (
  match_id: string,
  player_a: string | null,
  player_b: string | null,
) => ({ match_id, player_a, player_b }) as BracketMatchOutput

describe("hypePageHref", () => {
  it("finds a page in either player order", () => {
    expect(hypePageHref(match("LB5-1", "Modus", "WildCard"))).toBe(
      "/hype/modus-wildcard/index.html",
    )
    expect(hypePageHref(match("LB5-1", "WildCard", "Modus"))).toBe(
      "/hype/modus-wildcard/index.html",
    )
  })

  it("needs both the match and the pair to agree", () => {
    expect(hypePageHref(match("LB5-1", "Modus", "Gorn"))).toBeNull()
    expect(hypePageHref(match("GF-1", "Modus", "WildCard"))).toBeNull()
    expect(hypePageHref(match("LB5-1", "Modus", null))).toBeNull()
  })
})
