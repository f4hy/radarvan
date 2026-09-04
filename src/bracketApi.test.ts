import { describe, expect, it } from "vitest"
import {
  AdminUserFromJSON,
  AuthStatusFromJSON,
  MapVotePageFromJSON,
  SetBracketMatchRequestToJSON,
} from "./api"

/**
 * These pin the two things the move onto the generated client depends on, both
 * of which used to be guaranteed by hand-written code that no longer exists.
 */

describe("SetBracketMatchRequest PATCH semantics", () => {
  // routes/bracket.py's set_bracket_match only changes the keys present in the
  // body. The generated serializer names all four fields unconditionally, so
  // the omission has to survive JSON.stringify rather than the object literal —
  // which is what the runtime actually sends.
  const sent = (req: Parameters<typeof SetBracketMatchRequestToJSON>[0]) =>
    JSON.parse(JSON.stringify(SetBracketMatchRequestToJSON(req)))

  it("sends only the field the caller set", () => {
    const at = new Date("2026-08-05T19:00:00.000Z")
    expect(sent({ scheduledAt: at })).toEqual({
      scheduled_at: "2026-08-05T19:00:00.000Z",
    })
  })

  it("keeps an explicit null, which is how a field is cleared", () => {
    expect(sent({ scheduledAt: null })).toEqual({ scheduled_at: null })
  })

  it("sends a score update without touching the schedule", () => {
    expect(sent({ bestOf: 5, scoreA: 3, scoreB: 2 })).toEqual({
      best_of: 5,
      score_a: 3,
      score_b: 2,
    })
  })
})

describe("wire snake_case maps to the camelCase models", () => {
  it("reads an admin user association", () => {
    const user = AdminUserFromJSON({
      id: 7,
      discord_id: "123456789",
      discord_username: "discord-name",
      player_name: "Modus",
      created_at: "2026-06-14T12:00:00Z",
    })
    expect(user.discordId).toBe("123456789")
    expect(user.discordUsername).toBe("discord-name")
    expect(user.playerName).toBe("Modus")
    expect(user.createdAt.toISOString()).toBe("2026-06-14T12:00:00.000Z")
  })

  // The app reads `status.user.isAdmin`; the backend sends `is_admin`. Nothing
  // else checks that these line up.
  it("reads an auth status", () => {
    const status = AuthStatusFromJSON({
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
    expect(status.loggedIn).toBe(true)
    expect(status.user?.isAdmin).toBe(true)
    expect(status.user?.isOpsAdmin).toBe(true)
    expect(status.user?.isTournamentAdmin).toBe(false)
    expect(status.user?.playerName).toBe("Skip")
    expect(status.availablePlayers).toEqual(["Skip"])
  })

  // A null user arrives as undefined, not null — which is why the logged-out
  // check is `!status.user` rather than `status.user === null`.
  it("turns a null user into undefined", () => {
    const status = AuthStatusFromJSON({
      logged_in: false,
      user: null,
      available_players: [],
    })
    expect(status.user).toBeUndefined()
    expect(status.loggedIn).toBe(false)
  })

  it("reads a map vote page", () => {
    const page = MapVotePageFromJSON({
      player_count: 6,
      logged_in: true,
      vote_limit: 3,
      veto_limit: 1,
      votes_used: 2,
      vetoes_used: 0,
      maps: [
        {
          map_name: "maps/defcon6",
          game_count: 41,
          last_played: "2026-08-01T00:00:00Z",
          days_since_last_played: 28,
          my_choice: "vote",
        },
      ],
    })
    expect(page.playerCount).toBe(6)
    expect(page.loggedIn).toBe(true)
    expect(page.votesUsed).toBe(2)
    expect(page.voteLimit).toBe(3)
    expect(page.maps?.[0].mapName).toBe("maps/defcon6")
    expect(page.maps?.[0].daysSinceLastPlayed).toBe(28)
    expect(page.maps?.[0].myChoice).toBe("vote")
  })
})
