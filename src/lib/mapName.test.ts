import { describe, expect, it } from "vitest"
import cases from "../../tests/map_name_cases.json"
import { mapDisplayName, mapKey } from "./mapName"

describe("mapName parity with radarvan/replay_files.py", () => {
  it.each(cases.cases)("$input", ({ input, key, display }) => {
    expect(mapKey(input)).toBe(key)
    expect(mapDisplayName(input)).toBe(display)
  })
})
