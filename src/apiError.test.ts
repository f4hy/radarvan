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
