import { describe, expect, it } from "vitest"
import { ResponseError } from "./api"
import { errorMessage, responseErrorMessage } from "./apiError"

/**
 * The generated runtime throws every HTTP failure as a `ResponseError` carrying
 * the fixed text "Response returned an error code". Everything a person can
 * usefully read is in the response body, so this is what stands between a
 * failed request and a useless error panel.
 */

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

describe("errorMessage", () => {
  it("pulls FastAPI's detail out of a raised HTTPException", async () => {
    const err = new ResponseError(
      jsonResponse(409, { detail: "You have used all 3 votes." }),
      "Response returned an error code",
    )
    expect(await errorMessage(err)).toBe("You have used all 3 votes.")
  })

  it("renders a validation error's field and message", async () => {
    const err = new ResponseError(
      jsonResponse(422, {
        detail: [
          { loc: ["body", "player_name"], msg: "Field required" },
          { loc: ["query", "limit"], msg: "Input should be a valid integer" },
        ],
      }),
      "Response returned an error code",
    )
    expect(await errorMessage(err)).toBe(
      "player_name: Field required; limit: Input should be a valid integer",
    )
  })

  it("falls back to the status when the body isn't JSON", async () => {
    const err = new ResponseError(
      new Response("<html>502 Bad Gateway</html>", { status: 502 }),
      "Response returned an error code",
    )
    expect(await errorMessage(err)).toBe("Request failed (502)")
  })

  it("falls back to the status when the body has no detail", async () => {
    const err = new ResponseError(jsonResponse(500, { oops: true }), "x")
    expect(await errorMessage(err)).toBe("Request failed (500)")
  })

  it("leaves the response body readable for the caller", async () => {
    // It clones before reading, so a caller that catches the same error can
    // still inspect the body itself.
    const response = jsonResponse(400, { detail: "nope" })
    const err = new ResponseError(response, "x")
    expect(await errorMessage(err)).toBe("nope")
    await expect(response.json()).resolves.toEqual({ detail: "nope" })
  })

  it("passes an ordinary Error through", async () => {
    expect(await errorMessage(new Error("network down"))).toBe("network down")
  })

  it("stringifies anything else", async () => {
    expect(await errorMessage("just a string")).toBe("just a string")
  })
})

describe("responseErrorMessage", () => {
  it("reads a Response directly, for the hand-built map upload", async () => {
    const resp = jsonResponse(413, { detail: "That zip is too large." })
    expect(await responseErrorMessage(resp)).toBe("That zip is too large.")
  })
})

describe("the generated converter does not descend into dict-valued models", () => {
  // PlayerRatingData.playerRatingOvertime is `{ [name]: ShortPlayerRating[] }`,
  // and the generator emits `json['player_rating_overtime']` with no per-item
  // mapping — so `atdate` is declared `Date` and is a *string* at runtime.
  //
  // This is pinned because the type lies in a way that reads as safe: a call
  // site that did `entry.atdate.toISOString()` typechecked and then threw on
  // the live page. If a future regen makes the converter descend properly, this
  // test fails and the defensive `new Date(...)` wrappers in PlayerRatings.tsx
  // can go — but that has to be a deliberate change, not an assumption.
  it("leaves player_rating_overtime dates as strings", async () => {
    const { PlayerRatingDataFromJSON } = await import("./api")
    const parsed = PlayerRatingDataFromJSON({
      player_rating: [],
      player_form: {},
      player_rating_overtime: {
        Skip: [{ mu: 30, sigma: 2, atdate: "2026-08-28" }],
      },
    })
    const entry = parsed.playerRatingOvertime?.Skip?.[0]
    expect(entry).toBeDefined()
    expect(entry?.atdate).toBe("2026-08-28")
    expect(entry?.atdate).not.toBeInstanceOf(Date)
  })

  it("does convert a plain array of models, which is why brackets are safe", async () => {
    const { BracketTournamentOutputFromJSON } = await import("./api")
    const parsed = BracketTournamentOutputFromJSON({
      participant_names: [],
      players: [],
      matches: [
        {
          match_id: "WB1-1",
          bracket: "W",
          round_number: 1,
          round_name: "Winners Round 1",
          status: "pending",
          source_a: { kind: "seed", seed: 1 },
          source_b: { kind: "seed", seed: 2 },
          scheduled_at: "2026-08-28T19:00:00Z",
        },
      ],
      bye_advances: [],
      needs_reset: false,
      revealed: true,
    })
    expect(parsed.matches[0].scheduledAt).toBeInstanceOf(Date)
  })
})
