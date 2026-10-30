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
  ScenarioModelSummary,
  ScenarioPrediction,
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

export const SCENARIO_MODEL = wire<ScenarioModelSummary>({
  model: {
    nGames: 1384,
    dateMin: "2022-01-01",
    dateMax: "2026-10-23",
    trainedAt: "2026-10-25T21:18:43+00:00",
    replicates: 200,
  },
  generals: [
    {
      general: 10,
      effect: {
        value: 0.1425,
        low: 0.0457,
        high: 0.2548,
      },
      games: 533,
    },
    {
      general: 7,
      effect: {
        value: 0.1168,
        low: -0.0032,
        high: 0.2037,
      },
      games: 635,
    },
    {
      general: 1,
      effect: {
        value: 0.0939,
        low: -0.0159,
        high: 0.2004,
      },
      games: 673,
    },
    {
      general: 9,
      effect: {
        value: 0.0555,
        low: -0.0635,
        high: 0.1675,
      },
      games: 560,
    },
    {
      general: 2,
      effect: {
        value: 0.0357,
        low: -0.0825,
        high: 0.1473,
      },
      games: 582,
    },
    {
      general: 6,
      effect: {
        value: 0.0342,
        low: -0.0861,
        high: 0.1546,
      },
      games: 645,
    },
    {
      general: 0,
      effect: {
        value: -0.0034,
        low: -0.1133,
        high: 0.0947,
      },
      games: 552,
    },
    {
      general: 5,
      effect: {
        value: -0.0575,
        low: -0.1515,
        high: 0.054,
      },
      games: 597,
    },
    {
      general: 3,
      effect: {
        value: -0.06,
        low: -0.1716,
        high: 0.0594,
      },
      games: 674,
    },
    {
      general: 11,
      effect: {
        value: -0.0726,
        low: -0.1885,
        high: 0.0459,
      },
      games: 566,
    },
    {
      general: 8,
      effect: {
        value: -0.0762,
        low: -0.1856,
        high: 0.0237,
      },
      games: 590,
    },
    {
      general: 4,
      effect: {
        value: -0.209,
        low: -0.2929,
        high: -0.0931,
      },
      games: 681,
    },
  ],
  matchups: [
    {
      generalA: 6,
      generalB: 7,
      effect: {
        value: -0.2353,
        low: -0.3943,
        high: -0.0539,
      },
    },
    {
      generalA: 1,
      generalB: 2,
      effect: {
        value: 0.1866,
        low: 0.0487,
        high: 0.3173,
      },
    },
  ],
  teammates: [
    {
      factionA: 0,
      factionB: 2,
      effect: { value: 0.2087, low: 0.0793, high: 0.3312 },
    },
    {
      factionA: 0,
      factionB: 1,
      effect: { value: 0.1498, low: 0.0224, high: 0.278 },
    },
  ],
  mapEffects: [
    {
      general: 1,
      feature: "log_oil_per_player",
      effect: {
        value: 0.0708,
        low: 0.0028,
        high: 0.1453,
      },
    },
    {
      general: 7,
      feature: "log_money_per_player",
      effect: {
        value: 0.0635,
        low: 0.0076,
        high: 0.1077,
      },
    },
  ],
  mapFeatures: ["log_size", "log_money_per_player", "log_oil_per_player"],
  maps: [
    {
      key: "[rank] territorial dispute zh v1",
      trainingGames: 58,
      knownGeometry: true,
      players: 6,
    },
    {
      key: "green pastures",
      trainingGames: 54,
      knownGeometry: true,
      players: 6,
    },
    {
      key: "tournament island",
      trainingGames: 45,
      knownGeometry: true,
      players: 4,
    },
  ],
  evaluation: [
    {
      protocol: "night_cv",
      games: 1384,
      deltaLogLoss: {
        value: -0.001,
        low: -0.0061,
        high: 0.0042,
      },
    },
    {
      protocol: "chronological",
      games: 288,
      deltaLogLoss: {
        value: -0.0064,
        low: -0.0176,
        high: 0.0055,
      },
    },
  ],
})

export const SCENARIO_PREDICTION = wire<ScenarioPrediction>({
  probTeamA: {
    value: 0.3974,
    low: 0.3391,
    high: 0.4619,
  },
  contributions: {
    generals: -0.3515,
    teammates: 0.0,
    matchups: -0.0649,
    map: 0.0,
  },
  combinations: 1,
  combinationsExact: true,
  map: null,
  support: {
    exactGames: 2,
    exactTeamAWins: 0,
    exactGamesOnMap: 0,
    exactTeamAWinsOnMap: 0,
  },
  swaps: [
    {
      team: "A",
      index: 0,
      options: [
        {
          general: 0,
          probTeamA: 0.4277,
          delta: {
            value: 0.0303,
            low: -0.0373,
            high: 0.0895,
          },
        },
        {
          general: 1,
          probTeamA: 0.4953,
          delta: {
            value: 0.0979,
            low: 0.022,
            high: 0.1546,
          },
        },
        {
          general: 2,
          probTeamA: 0.4508,
          delta: {
            value: 0.0534,
            low: -0.0052,
            high: 0.1083,
          },
        },
        {
          general: 3,
          probTeamA: 0.4469,
          delta: {
            value: 0.0495,
            low: -0.02,
            high: 0.1129,
          },
        },
        {
          general: 4,
          probTeamA: 0.3974,
          delta: {
            value: 0.0,
            low: 0.0,
            high: 0.0,
          },
        },
        {
          general: 5,
          probTeamA: 0.4447,
          delta: {
            value: 0.0473,
            low: -0.019,
            high: 0.1106,
          },
        },
        {
          general: 6,
          probTeamA: 0.4716,
          delta: {
            value: 0.0742,
            low: 0.0173,
            high: 0.1452,
          },
        },
        {
          general: 7,
          probTeamA: 0.4919,
          delta: {
            value: 0.0945,
            low: 0.0226,
            high: 0.1575,
          },
        },
        {
          general: 8,
          probTeamA: 0.421,
          delta: {
            value: 0.0236,
            low: -0.0412,
            high: 0.0824,
          },
        },
        {
          general: 9,
          probTeamA: 0.4864,
          delta: {
            value: 0.089,
            low: 0.0173,
            high: 0.1677,
          },
        },
        {
          general: 10,
          probTeamA: 0.5,
          delta: {
            value: 0.1026,
            low: 0.0381,
            high: 0.1609,
          },
        },
        {
          general: 11,
          probTeamA: 0.4355,
          delta: {
            value: 0.0382,
            low: -0.0282,
            high: 0.0967,
          },
        },
      ],
    },
    {
      team: "B",
      index: 0,
      options: [
        {
          general: 0,
          probTeamA: 0.4383,
          delta: {
            value: 0.0409,
            low: -0.0269,
            high: 0.1029,
          },
        },
        {
          general: 1,
          probTeamA: 0.4424,
          delta: {
            value: 0.045,
            low: -0.0148,
            high: 0.1045,
          },
        },
        {
          general: 2,
          probTeamA: 0.4051,
          delta: {
            value: 0.0077,
            low: -0.0544,
            high: 0.0786,
          },
        },
        {
          general: 3,
          probTeamA: 0.4438,
          delta: {
            value: 0.0464,
            low: -0.0183,
            high: 0.1233,
          },
        },
        {
          general: 4,
          probTeamA: 0.5,
          delta: {
            value: 0.1026,
            low: 0.0381,
            high: 0.1609,
          },
        },
        {
          general: 5,
          probTeamA: 0.4233,
          delta: {
            value: 0.0259,
            low: -0.0461,
            high: 0.0947,
          },
        },
        {
          general: 6,
          probTeamA: 0.3964,
          delta: {
            value: -0.001,
            low: -0.0747,
            high: 0.0807,
          },
        },
        {
          general: 7,
          probTeamA: 0.3891,
          delta: {
            value: -0.0083,
            low: -0.0772,
            high: 0.0741,
          },
        },
        {
          general: 8,
          probTeamA: 0.4998,
          delta: {
            value: 0.1024,
            low: 0.0443,
            high: 0.1695,
          },
        },
        {
          general: 9,
          probTeamA: 0.4294,
          delta: {
            value: 0.032,
            low: -0.0387,
            high: 0.0945,
          },
        },
        {
          general: 10,
          probTeamA: 0.3974,
          delta: {
            value: 0.0,
            low: 0.0,
            high: 0.0,
          },
        },
        {
          general: 11,
          probTeamA: 0.459,
          delta: {
            value: 0.0616,
            low: -0.0119,
            high: 0.1373,
          },
        },
      ],
    },
  ],
  maps: [
    {
      key: "[rank] territorial dispute zh v1",
      trainingGames: 58,
      probTeamA: 0.4038,
      delta: {
        value: 0.0064,
        low: -0.0069,
        high: 0.0225,
      },
    },
    {
      key: "green pastures",
      trainingGames: 54,
      probTeamA: 0.3874,
      delta: {
        value: -0.01,
        low: -0.0438,
        high: 0.0285,
      },
    },
  ],
  model: {
    nGames: 1384,
    dateMin: "2022-01-01",
    dateMax: "2026-10-23",
    trainedAt: "2026-10-25T21:18:43+00:00",
    replicates: 200,
  },
})
