import type {
  AuthStatus,
  DurationDistribution,
  GameNightRecap,
  MapStatsResponse,
  MapVotePage,
  MatchInfo,
  PlayerProfile,
  PlayerRatingData,
  Superlatives,
  TeamStatsResponse,
} from "../src/api"

/**
 * The smallest payloads that render each page.
 *
 * Typed against the generated client on purpose: these are the one place the
 * e2e suite asserts a wire shape, and typing them means a backend model change
 * fails `tsc` here instead of drifting until a test mysteriously goes red. They
 * are deliberately thin — these tests are about routing, links, error handling
 * and accessibility, not about whether a win rate is computed correctly, which
 * is what the Python suite is for.
 *
 * Note the wire is snake_case and the generated *models* are camelCase: mocks
 * fulfil raw HTTP, so everything here is written the way the server writes it
 * and typed via `wire<T>()`, which documents that pairing rather than hiding it.
 */

/** A raw JSON body that the generated converter will turn into `T`. */
export function wire<T>(body: unknown): { __model?: T; body: unknown } {
  return { body }
}

export const LOGGED_OUT = wire<AuthStatus>({
  logged_in: false,
  user: null,
  available_players: [],
})

export const ADMIN_USER = wire<AuthStatus>({
  logged_in: true,
  user: {
    discord_id: "1",
    discord_username: "tester",
    discord_avatar: null,
    player_name: "Skip",
    needs_player_selection: false,
    is_admin: true,
    is_tournament_admin: true,
    is_ops_admin: true,
  },
  available_players: ["Skip"],
})

/** Two nights, so the calendar has something to focus and the night list has
 * something to expand. */
export const DATES = { "2026-08-29": 6, "2026-08-28": 18 }

export const MATCH: MatchInfo = {
  id: 1,
  mapName: "maps/tournament island",
  durationMinutes: 21.5,
  players: [],
  teams: {},
  winners: ["Skip"],
  losers: ["CoreDawg"],
} as unknown as MatchInfo

export const MATCHES = wire<{ matches: MatchInfo[] }>({ matches: [] })

export const TEAM_STATS = wire<TeamStatsResponse>({
  groups: [
    {
      size: 2,
      teams: [{ players: ["Skip", "CoreDawg"], wins: 7, losses: 3 }],
    },
  ],
})

export const SUPERLATIVES = wire<Superlatives>({
  computed_at: "2026-08-29T04:00:00Z",
  stats: [
    {
      stat_name: "Most Games",
      value: "412",
      player: "Skip",
      match_id: null,
    },
  ],
})

export const DURATIONS = wire<DurationDistribution>({
  buckets: [{ start_minutes: 0, end_minutes: 2, count: 3 }],
  stats: {
    count: 3,
    median_minutes: 21,
    mean_minutes: 22,
    p10_minutes: 10,
    p90_minutes: 40,
    shortest_minutes: 5,
    longest_minutes: 55,
  },
})

export const MAP_VOTE_PAGE = wire<MapVotePage>({
  player_count: 6,
  logged_in: false,
  vote_limit: 3,
  veto_limit: 1,
  votes_used: 0,
  vetoes_used: 0,
  maps: [
    {
      map_name: "maps/tournament island",
      game_count: 41,
      last_played: "2026-08-01T00:00:00Z",
      days_since_last_played: 28,
      my_choice: null,
    },
  ],
})

// Complete rather than minimal, and that is the lesson: the first version left
// `started_at`/`ended_at` out, `clockSpan` did `new Date(undefined).toISOString()`
// and the page threw "invalid date" into the error boundary. A required field
// omitted from a fixture is a bug in the fixture, not a discovery about the app.
export const GAME_NIGHT = wire<GameNightRecap>({
  date: "2026-08-28",
  match_count: 6,
  counted_matches: 6,
  total_minutes: 128,
  median_minutes: 21,
  started_at: "2026-08-28T23:10:00Z",
  ended_at: "2026-08-29T01:18:00Z",
  formats: { "2v2": 6 },
  maps: { "maps/tournament island": 6 },
  players: [],
  highlights: [],
  ai_summary: null,
  ai_summary_provider: null,
  ai_summary_computed_at: null,
})

/** A profile that names *another* player, so the suite can click through from
 * one profile to the next — the exact case that was broken while the page kept
 * its own copy of `?player=` in component state. */
export function playerProfile(player: string, nemesis: string) {
  return wire<PlayerProfile>({
    player,
    games: 120,
    wins: 70,
    losses: 50,
    generals: [],
    general_win_rate_over_time: [],
    most_played_general: null,
    best_general: null,
    favorite_map: null,
    best_map: null,
    favorite_teammate: null,
    nemesis: { name: nemesis, wins: 4, losses: 11 },
    favorite_victim: null,
    avg_win_duration_minutes: 20,
    avg_loss_duration_minutes: 25,
    computed: null,
  })
}

/**
 * Ratings, with `player_rating_overtime` actually populated.
 *
 * The populated part is the point. That field is a dict of arrays of models,
 * which the generator passes through *raw* — no `ShortPlayerRatingFromJSON` is
 * ever called on it — so `atdate` is typed `Date` and arrives as a string. A
 * fixture that left this empty rendered the page fine and caught nothing, while
 * the real page threw `atdate.toISOString is not a function`. Dates here are
 * strings on purpose: that is what the wire sends and what the app receives.
 */
export const PLAYER_RATINGS = wire<PlayerRatingData>({
  player_rating: [
    {
      name: "Skip",
      mu: 30.2,
      sigma: 2.1,
      ordinal: 23.9,
      ordinal_high: 26,
      ordinal_low: 21,
      game_count: 120,
      recent_deltas: {},
    },
  ],
  player_form: {},
  player_rating_overtime: {
    Skip: [
      { mu: 29.0, sigma: 3.0, atdate: "2026-08-01" },
      { mu: 30.2, sigma: 2.1, atdate: "2026-08-28" },
    ],
  },
})

/**
 * Five maps, because the page auto-expands the first three: a deep-link test
 * needs a target outside that set, or it can't tell "the link worked" from
 * "this map was open anyway". `thin desert` sits under the 10-game floor for
 * the same reason — the floor is what the `?map=` pin has to beat.
 */
export const MAP_STATS = wire<MapStatsResponse>({
  // camelCase here, unlike most fixtures in this file: MapData carries no
  // serialisation aliases, so this endpoint really is camelCase on the wire.
  // Verified against a running server, not assumed.
  maps: [
    { mapName: "alpine assault", totalGames: 40 },
    { mapName: "tournament desert", totalGames: 30 },
    { mapName: "dusty rampage", totalGames: 20 },
    { mapName: "final crusade", totalGames: 15 },
    { mapName: "thin desert", totalGames: 2 },
  ].map((m) => ({
    ...m,
    playerStats: [{ player: "Skip", wins: 3, losses: 1 }],
    generalStats: [{ general: "USA", wins: 3, losses: 1 }],
  })),
})
