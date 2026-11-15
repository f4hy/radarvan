import { describe, expect, it } from "vitest"
import type { BracketMatchOutput } from "./bracketApi"
import { championPageLinks, matchPageLink } from "./matchPages"

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

  it("links the Grand Final preview", () => {
    expect(matchPageLink(match("GF-1", "Gorn", "Modus"))).toEqual({
      kind: "preview",
      href: "/hype/modus-gorn/index.html",
    })
  })

  it("links the Grand Final Reset preview", () => {
    expect(matchPageLink(match("GF-2", "Gorn", "Modus"))).toEqual({
      kind: "preview",
      href: "/hype/modus-gorn-reset/index.html",
    })
  })

  it("switches a played match to its recap", () => {
    expect(
      matchPageLink(match("LB4-1", "Modus", "Tytan", "completed")),
    ).toEqual({ kind: "recap", href: "/recap/modus-tytan/index.html" })
    expect(
      matchPageLink(match("LB5-1", "WildCard", "Modus", "completed")),
    ).toEqual({ kind: "recap", href: "/recap/modus-wildcard/index.html" })
    expect(matchPageLink(match("GF-1", "Gorn", "Modus", "completed"))).toEqual({
      kind: "recap",
      href: "/recap/modus-gorn/index.html",
    })
  })

  it("links the final recap and the story from a finished bracket", () => {
    const gf = (id: string, status: BracketMatchOutput["status"]) =>
      ({
        ...match(id, "Gorn", "Modus", status),
        bracket: "GF",
      }) as BracketMatchOutput
    expect(
      championPageLinks([gf("GF-1", "completed"), gf("GF-2", "completed")]),
    ).toEqual({
      finalRecap: "/recap/modus-gorn-reset/index.html",
      story: "/recap/2026-1v1-bracket/index.html",
    })
    expect(championPageLinks([gf("GF-1", "completed")])).toEqual({
      finalRecap: "/recap/modus-gorn/index.html",
      story: null,
    })
    expect(championPageLinks([gf("GF-1", "ready")])).toBeNull()
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
