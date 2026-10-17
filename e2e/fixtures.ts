import type {
  AuthStatus,
  DurationDistribution,
  GameNightRecap,
  MapStatsResponse,
  MapsByPlayerCount,
  MapVotePage,
  MatchInfo,
  PlayerProfile,
  PlayerRatingData,
  Superlatives,
  TeamStatsResponse,
} from "../src/api/types.gen"

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
 * The generated types use the wire's own field names, so the one gap between a
 * model and its JSON is that the response transformers turn date strings into
 * `Date`. Mocks fulfil raw HTTP, so everything here is written the way the
 * server writes it, with dates as strings, and `wire<T>()` checks exactly that.
 */

type Wire<T> = T extends Date
  ? string
  : T extends readonly (infer U)[]
    ? Wire<U>[]
    : T extends object
      ? { [K in keyof T]: Wire<T[K]> }
      : T

/** A raw JSON body that the response transformers will turn into `T`. */
export function wire<T>(body: Wire<T>): { __model?: T; body: Wire<T> } {
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

export const MATCH = wire<MatchInfo>({
  id: 1,
  timestamp: "2026-08-29T02:00:00Z",
  date: "2026-08-28",
  map: "maps/tournament island",
  winning_team: 1,
  players: [],
  duration_minutes: 21.5,
  filename: "upload:fixture",
  has_ai: false,
})

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
      date_computed: "2026-08-29",
      value: "412",
      player: "Skip",
      match_id: null,
    },
  ],
})

export const DURATIONS = wire<DurationDistribution>({
  bucketMinutes: 2,
  buckets: [{ startMinutes: 0, endMinutes: 2, count: 3 }],
  stats: {
    count: 3,
    totalMinutes: 66,
    medianMinutes: 21,

    meanMinutes: 22,
    p10Minutes: 10,
    p90Minutes: 40,
    shortestMinutes: 5,
    longestMinutes: 55,
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

export const MATCH_OF_THE_NIGHT_BLURB =
  "Skip and Syn were written off at 12% on tournament island, then clawed the whole game back."

// Complete rather than minimal, and that is the lesson: the first version left
// `started_at`/`ended_at` out, `clockSpan` did `new Date(undefined).toISOString()`
// and the page threw "invalid date" into the error boundary. A required field
// omitted from a fixture is a bug in the fixture, not a discovery about the app.
export const GAME_NIGHT = wire<GameNightRecap>({
  date: "2026-08-28",
  matchCount: 6,
  countedMatches: 6,
  totalMinutes: 128,
  medianMinutes: 21,
  startedAt: "2026-08-28T23:10:00Z",
  endedAt: "2026-08-29T01:18:00Z",
  formats: { "2v2": 6 },
  maps: { "maps/tournament island": 6 },
  players: [],
  highlights: [
    // Listed first on purpose: the page must still put the match of the night on top.
    {
      kind: "longest_game",
      title: "Longest game",
      detail: "40.7 min on tournament island",
      matchId: 99,
    },
    {
      kind: "match_of_the_night",
      title: "Match of the night",
      detail:
        "Skip & Syn on tournament island: the lead changed hands 3 times; they were down to 12% to win before taking it",
      matchId: 1234,
      points: [0.5, 0.3, 0.12, 0.4, 0.7, 0.95],
      blurb: MATCH_OF_THE_NIGHT_BLURB,
    },
  ],
  aiSummary: null,
  aiSummaryProvider: null,
  aiSummaryComputedAt: null,
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
    generalWinRateOverTime: [],
    mostPlayedGeneral: null,
    bestGeneral: null,
    favoriteMap: null,
    bestMap: null,
    favoriteTeammate: null,
    nemesis: { name: nemesis, wins: 4, losses: 11 },
    favoriteVictim: null,
    avgWinDurationMinutes: 20,
    avgLossDurationMinutes: 25,
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
      high_ordinal: 26,
      low_ordinal: 21,
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
    generalStats: [{ general: 0, wins: 3, losses: 1 }],
  })),
})

// Same alias situation as MapData above (Field(alias=...) with a camelCase
// alias, so populate_by_name doesn't change what's on the wire): camelCase here.
export const MAPS_BY_PLAYER_COUNT = wire<MapsByPlayerCount[]>([
  { playerCount: 2, maps: ["alpine assault", "dusty rampage"] },
  {
    playerCount: 4,
    maps: ["maps/tournament island", "tournament desert", "final crusade"],
  },
])
