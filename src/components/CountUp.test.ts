import { describe, expect, it } from "vitest"
import { parseNumericText } from "./CountUp"

describe("parseNumericText", () => {
  it("keeps the text around a single number", () => {
    expect(parseNumericText("was at 97.9% to win")).toEqual({
      prefix: "was at ",
      target: 97.9,
      suffix: "% to win",
      decimals: 1,
      grouped: false,
    })
    expect(parseNumericText("$12,345")?.target).toBe(12345)
    expect(parseNumericText("$12,345")?.grouped).toBe(true)
  })

  it("leaves text that is not one quantity alone", () => {
    for (const text of ["12:34", "3-0", "USA Laser", "—", ""]) {
      expect(parseNumericText(text)).toBeNull()
    }
  })
})
