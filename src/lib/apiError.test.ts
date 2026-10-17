import { describe, expect, it } from "vitest"
import {
  getBracketApiBracketGetResponseTransformer,
  getPlayerRatingsApiPlayerRatingsGetResponseTransformer,
} from "../api/transformers.gen"
import { ApiError, errorMessage, readApiError } from "./apiError"

/**
 * Every non-2xx reaches callers as an `ApiError` built by `readApiError`.
 * Everything a person can usefully read is in the response body, so this is
 * what stands between a failed request and a useless error panel.
 */

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json" },
  })
}

describe("readApiError", () => {
  it("pulls FastAPI's detail out of a raised HTTPException", async () => {
    const err = await readApiError(
      jsonResponse(409, { detail: "You have used all 3 votes." }),
    )
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(409)
    expect(errorMessage(err)).toBe("You have used all 3 votes.")
  })

  it("renders a validation error's field and message", async () => {
    const err = await readApiError(
      jsonResponse(422, {
        detail: [
          { loc: ["body", "player_name"], msg: "Field required" },
          { loc: ["query", "limit"], msg: "Input should be a valid integer" },
        ],
      }),
    )
    expect(err.message).toBe(
      "player_name: Field required; limit: Input should be a valid integer",
    )
  })

  it("falls back to the status when the body isn't JSON", async () => {
    const err = await readApiError(
      new Response("<html>502 Bad Gateway</html>", { status: 502 }),
    )
    expect(err.message).toBe("Request failed (502)")
  })

  it("falls back to the status when the body has no detail", async () => {
    const err = await readApiError(jsonResponse(500, { oops: true }))
    expect(err.message).toBe("Request failed (500)")
  })

  it("leaves the response body readable for the caller", async () => {
    const response = jsonResponse(400, { detail: "nope" })
    expect((await readApiError(response)).message).toBe("nope")
    await expect(response.json()).resolves.toEqual({ detail: "nope" })
  })
})

describe("errorMessage", () => {
  it("passes an ordinary Error through", () => {
    expect(errorMessage(new Error("network down"))).toBe("network down")
  })

  it("stringifies anything else", () => {
    expect(errorMessage("just a string")).toBe("just a string")
  })
})

describe("the response transformers parse dates", () => {
  // The previous generator skipped dict-valued fields, so `atdate` here was
  // declared `Date` and arrived as a string. Pinned so a regen that regresses
  // that fails here rather than on the ratings page.
  it("descends into dict-valued player_rating_overtime", async () => {
    const parsed = await getPlayerRatingsApiPlayerRatingsGetResponseTransformer(
      {
        player_rating: [],
        player_form: {},
        player_rating_overtime: {
          Skip: [{ mu: 30, sigma: 2, atdate: "2026-08-28" }],
        },
      },
    )
    expect(parsed.player_rating_overtime?.Skip?.[0]?.atdate).toBeInstanceOf(
      Date,
    )
  })

  it("converts a plain array of models", async () => {
    const parsed = await getBracketApiBracketGetResponseTransformer({
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
    expect(parsed?.matches[0]?.scheduled_at).toBeInstanceOf(Date)
  })
})
