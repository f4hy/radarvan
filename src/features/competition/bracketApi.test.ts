import { afterEach, beforeAll, describe, expect, it, vi } from "vitest"
import { client } from "../../api/client.gen"
import { fetchAuthStatus } from "../../lib/auth"
import { setBracketMatch } from "./bracketApi"

/**
 * These go through the real generated client with only `fetch` stubbed, so
 * they pin what actually goes over the wire and what comes back out.
 */

function stubFetch(body: unknown) {
  const requests: Request[] = []
  vi.stubGlobal(
    "fetch",
    vi.fn(async (req: Request) => {
      requests.push(req)
      return new Response(JSON.stringify(body), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    }),
  )
  return requests
}

const EMPTY_BRACKET = {
  participant_names: [],
  players: [],
  matches: [],
  bye_advances: [],
  needs_reset: false,
  revealed: true,
}

// Node's Request, unlike a browser's, can't resolve the app's relative URLs.
beforeAll(() => {
  client.setConfig({ baseUrl: "http://localhost" })
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe("setBracketMatch PATCH semantics", () => {
  // routes/bracket.py's set_bracket_match only changes the keys present in the
  // body, so an omitted key must not be sent at all.
  async function sent(req: Parameters<typeof setBracketMatch>[1]) {
    const requests = stubFetch(EMPTY_BRACKET)
    await setBracketMatch("WB1-1", req)
    expect(requests).toHaveLength(1)
    expect(new URL(requests[0].url).pathname).toBe("/api/bracket/WB1-1")
    return requests[0].json()
  }

  it("sends only the field the caller set", async () => {
    const at = new Date("2026-08-05T19:00:00.000Z")
    expect(await sent({ scheduled_at: at })).toEqual({
      scheduled_at: "2026-08-05T19:00:00.000Z",
    })
  })

  it("keeps an explicit null, which is how a field is cleared", async () => {
    expect(await sent({ scheduled_at: null })).toEqual({ scheduled_at: null })
  })

  it("sends a score update without touching the schedule", async () => {
    expect(await sent({ best_of: 5, score_a: 3, score_b: 2 })).toEqual({
      best_of: 5,
      score_a: 3,
      score_b: 2,
    })
  })
})

describe("responses keep the wire's own field names", () => {
  // The previous generator renamed every field to camelCase and turned a null
  // into undefined; this one does neither, which is why the logged-out check
  // is `!status.user` (true either way).
  it("reads an auth status with a null user", async () => {
    stubFetch({ logged_in: false, user: null, available_players: [] })
    const status = await fetchAuthStatus()
    expect(status.logged_in).toBe(false)
    expect(status.user).toBeNull()
  })

  it("reads an auth status", async () => {
    stubFetch({
      logged_in: true,
      user: {
        discord_id: "1",
        discord_username: "someone",
        discord_avatar: null,
        player_name: "Skip",
        needs_player_selection: false,
        is_admin: true,
        is_tournament_admin: false,
        is_ops_admin: true,
      },
      available_players: ["Skip"],
    })
    const status = await fetchAuthStatus()
    expect(status.user?.is_admin).toBe(true)
    expect(status.user?.is_ops_admin).toBe(true)
    expect(status.user?.player_name).toBe("Skip")
    expect(status.available_players).toEqual(["Skip"])
  })
})
