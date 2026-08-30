import type { Page, Route } from "@playwright/test"
import * as fx from "./fixtures"

/**
 * Serves `/api/**` from fixtures, so the suite needs no backend and no database.
 *
 * Two properties matter more than the fixtures themselves:
 *
 * 1. **Nothing reaches the network.** Every `/api` request is fulfilled here, so
 *    a test can't accidentally pass because a real server happened to be up, and
 *    CI needs no Postgres.
 * 2. **An unmocked endpoint is visible, not silent.** Anything unmatched gets an
 *    empty body *and* is recorded, so `expectNoUnmockedCalls` can fail a test
 *    that quietly started calling something new. A page that fetches an endpoint
 *    nobody wrote a fixture for is exactly the drift this suite exists to catch.
 */

type Body = unknown

/** Longest-prefix-wins, so `/api/map_vote/players` beats `/api/map_vote/`. */
const ROUTES: [pattern: string, body: Body][] = [
  ["/api/auth/me", fx.LOGGED_OUT.body],
  ["/api/dates/", fx.DATES],
  ["/api/matches/by_date/", fx.MATCHES.body],
  ["/api/match/", fx.MATCH],
  ["/api/team_stats/", fx.TEAM_STATS.body],
  ["/api/superlatives", fx.SUPERLATIVES.body],
  ["/api/duration_distribution/", fx.DURATIONS.body],
  ["/api/map_vote/player_counts", [4, 6, 8]],
  ["/api/map_vote/players", ["Skip", "CoreDawg"]],
  ["/api/map_vote/", fx.MAP_VOTE_PAGE.body],
  ["/api/player_colors/", { Skip: "red", CoreDawg: "blue" }],
  ["/api/player_profile/eligible_players", ["Skip", "CoreDawg"]],
  ["/api/player_game_counts/team/", []],
  ["/api/player_game_counts/", [{ name: "Skip", count: 10 }]],
  ["/api/playerstats", { player_stats: [] }],
  ["/api/generalstats", { general_stats: [] }],
  ["/api/ffastats", { total_games: 0, player_stats: [], distinct_players: 0 }],
  ["/api/map_stats/", fx.MAP_STATS.body],
  ["/api/map_match_counts", []],
  ["/api/maps_by_player_count", {}],
  ["/api/power_stats/", { players: [], profile: null }],
  ["/api/player_ratings/synergy/", []],
  ["/api/player_ratings/daily_changes/", []],
  ["/api/player_ratings/upsets", []],
  ["/api/player_ratings/head_to_head", {}],
  ["/api/player_ratings/", fx.PLAYER_RATINGS.body],
  ["/api/player_skills", []],
  ["/api/tournament_results/", []],
  ["/api/tournament_report/", { stats: [] }],
  ["/api/game_night/", fx.GAME_NIGHT.body],
  ["/api/bracket_eligible_players", ["Skip", "CoreDawg"]],
  ["/api/bracket_map_records", []],
  ["/api/bracket_predictions", []],
  ["/api/bracket_prediction_leaderboard", []],
  ["/api/bracket", null],
  ["/api/predict/faction_matrix", null],
  ["/api/map_data/", { supply: [], extent: null, player_starts: [] }],
]

export interface ApiMock {
  /** Paths that were requested but had no fixture. */
  unmocked: string[]
  /** Every `/api` path requested, in order — for asserting cache behaviour. */
  calls: string[]
  /**
   * The same requests with their query strings, for asserting that a filter the
   * page shows is a filter the server was actually asked for. `calls` stays
   * path-only because the cache assertions want to count requests, not
   * distinguish them.
   */
  urls: string[]
}

export async function mockApi(
  page: Page,
  overrides: Record<string, Body> = {},
): Promise<ApiMock> {
  const state: ApiMock = { unmocked: [], calls: [], urls: [] }

  await page.route("**/api/**", async (route: Route) => {
    const url = new URL(route.request().url())
    const path = url.pathname
    state.calls.push(path)
    state.urls.push(path + url.search)

    // Map images are binary and irrelevant to every assertion here; a 404 is a
    // shape the app already handles (it draws its placeholder).
    if (path.startsWith("/api/map_image/")) {
      return route.fulfill({ status: 404, body: "" })
    }

    const override = Object.entries(overrides).find(([p]) => path.startsWith(p))
    if (override) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(override[1]),
      })
    }

    const match = ROUTES.filter(([p]) => path.startsWith(p)).sort(
      (a, b) => b[0].length - a[0].length,
    )[0]
    if (!match) {
      state.unmocked.push(path)
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: "null",
      })
    }
    return route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(match[1]),
    })
  })

  return state
}

/** Fails the test if a page reached for an endpoint with no fixture. */
export function unmockedReport(mock: ApiMock): string {
  return [...new Set(mock.unmocked)].join(", ")
}
