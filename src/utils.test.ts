import { describe, it, expect } from "vitest"
import {
  winRate,
  displayMapName,
  getColorHex,
  playerColor,
  buildPlayerColorMap,
} from "./utils"

describe("winRate", () => {
  it("computes the ratio of wins to total games", () => {
    expect(winRate(3, 1)).toBe(0.75)
    expect(winRate(1, 1)).toBe(0.5)
    expect(winRate(5, 0)).toBe(1)
  })

  it("returns 0 when there are no games (no divide by zero)", () => {
    expect(winRate(0, 0)).toBe(0)
  })
})

describe("displayMapName", () => {
  it("strips directory path and .map extension", () => {
    expect(displayMapName("maps/Tournament Desert.map")).toBe(
      "Tournament Desert",
    )
  })

  it("handles nested paths and is case-insensitive on the extension", () => {
    expect(displayMapName("a/b/c/Foo.MAP")).toBe("Foo")
  })

  it("leaves a plain name without path or extension untouched", () => {
    expect(displayMapName("Bare Name")).toBe("Bare Name")
  })

  it("strips only the path when there is no extension", () => {
    expect(displayMapName("dir/Some Map")).toBe("Some Map")
  })
})

describe("getColorHex", () => {
  it("maps known color names to hex (case-insensitive)", () => {
    expect(getColorHex("red")).toBe("#FF0000")
    expect(getColorHex("Blue")).toBe("#0000FF")
    expect(getColorHex("VIOLET")).toBe("#7F00FF")
  })

  it("maps the sentinel '-1' to black", () => {
    expect(getColorHex("-1")).toBe("#000000")
  })

  it("passes through valid hex strings", () => {
    expect(getColorHex("#abc")).toBe("#abc")
    expect(getColorHex("#A1B2C3")).toBe("#A1B2C3")
  })

  it("passes through css color function strings", () => {
    expect(getColorHex("rgb(1,2,3)")).toBe("rgb(1,2,3)")
    expect(getColorHex("hsla(1, 2%, 3%, 0.5)")).toBe("hsla(1, 2%, 3%, 0.5)")
  })

  it("falls back to grey for unknown input", () => {
    expect(getColorHex("not-a-color")).toBe("#808080")
    expect(getColorHex("#12")).toBe("#808080")
  })
})

describe("playerColor", () => {
  it("is deterministic for the same name across calls", () => {
    expect(playerColor("Skip")).toBe(playerColor("Skip"))
  })

  it("returns a color from the fixed palette", () => {
    const palette = [
      "#2f6df0",
      "#7c4dff",
      "#00897b",
      "#e0457b",
      "#f5871f",
      "#3949ab",
      "#0b8043",
      "#c2185b",
      "#00838f",
      "#5e35b1",
      "#d81b60",
      "#1565c0",
    ]
    expect(palette).toContain(playerColor("anyone"))
  })

  it("handles the empty string without throwing", () => {
    expect(typeof playerColor("")).toBe("string")
  })
})

describe("buildPlayerColorMap", () => {
  it("maps player names to their colors", () => {
    const summaries = [
      { name: "Alice", color: "red" },
      { name: "Bob", color: "#abc" },
    ]
    expect(buildPlayerColorMap(summaries)).toEqual({
      Alice: "red",
      Bob: "#abc",
    })
  })

  it("applies the optional transform to each color", () => {
    const summaries = [
      { name: "Alice", color: "red" },
      { name: "Bob", color: "blue" },
    ]
    expect(buildPlayerColorMap(summaries, getColorHex)).toEqual({
      Alice: "#FF0000",
      Bob: "#0000FF",
    })
  })

  it("returns an empty object for no players", () => {
    expect(buildPlayerColorMap([])).toEqual({})
  })
})
