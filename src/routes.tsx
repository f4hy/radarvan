import AccountTreeIcon from "@mui/icons-material/AccountTree"
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings"
import BadgeIcon from "@mui/icons-material/Badge"
import BalanceIcon from "@mui/icons-material/Balance"
import BoltIcon from "@mui/icons-material/Bolt"
import CasinoIcon from "@mui/icons-material/Casino"
import CompareArrowsIcon from "@mui/icons-material/CompareArrows"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import GroupsIcon from "@mui/icons-material/Groups"
import HistoryToggleOffIcon from "@mui/icons-material/HistoryToggleOff"
import HowToVoteIcon from "@mui/icons-material/HowToVote"
import LeaderboardIcon from "@mui/icons-material/Leaderboard"
import ListIcon from "@mui/icons-material/List"
import MapIcon from "@mui/icons-material/Map"
import MenuBookIcon from "@mui/icons-material/MenuBook"
import MilitaryTechIcon from "@mui/icons-material/MilitaryTech"
import NightlightRoundIcon from "@mui/icons-material/NightlightRound"
import PersonIcon from "@mui/icons-material/Person"
import SportsKabaddiIcon from "@mui/icons-material/SportsKabaddi"
import TableView from "@mui/icons-material/TableView"
import UploadFileIcon from "@mui/icons-material/UploadFile"
import WorkspacePremiumIcon from "@mui/icons-material/WorkspacePremium"
import * as React from "react"

/**
 * Every page, once.
 *
 * This array is the router, the sidebar, the app-bar title and the gate, so
 * adding a page means adding an entry rather than editing five lists that could
 * disagree. Before this there were exactly those five: an `ALL_SELECTIONS`
 * union, a block of `React.lazy` bindings, a `NavGroup[]`, a 25-arm `switch`,
 * and a gate condition inlined into the nav — and a page could be routable but
 * unreachable, or listed but unrouted, with nothing to say so.
 *
 * A page's `title` is both its nav label and its own `<h1>`, so the two can't
 * drift; `Page` takes the same string.
 *
 * Every page is code-split. The initial bundle would otherwise carry all of
 * them (recharts, the bracket, html2canvas, …) just to render Matches.
 */

/** Who sees the *nav item*. The backend gate is the real boundary — a route is
 * still reachable by typing its URL, which is deliberate for the rating pages
 * (see the "Rating levels are not public" note in the root CLAUDE.md). */
export type Gate = "public" | "admin" | "opsAdmin"

export interface RouteGroup {
  heading: string
  routes: AppRoute[]
}

export interface AppRoute {
  /** URL path, without the leading slash. Also the old `?page=` value, so
   * links already pasted into Discord keep resolving — see LEGACY_PAGE_PARAM. */
  slug: string
  title: string
  icon: React.ReactNode
  heading: string
  gate: Gate
  Component: React.LazyExoticComponent<React.ComponentType>
}

const Account = React.lazy(() => import("./Account"))
const AdminPanel = React.lazy(() => import("./AdminPanel"))
const BalanceTeams = React.lazy(() => import("./BalanceTeams"))
const Bracket = React.lazy(() => import("./Bracket"))
const ChooseMap = React.lazy(() => import("./ChooseMap"))
const DebugData = React.lazy(() => import("./DebugData"))
const Draft = React.lazy(() => import("./Draft"))
const FFA = React.lazy(() => import("./FFA"))
const GameLength = React.lazy(() => import("./GameLength"))
const GameNight = React.lazy(() => import("./GameNight"))
const GeneralStats = React.lazy(() => import("./GeneralStats"))
const HeadToHead = React.lazy(() => import("./HeadToHead"))
const MapStats = React.lazy(() => import("./MapStats"))
const MapUpload = React.lazy(() => import("./MapUpload"))
const MapVoting = React.lazy(() => import("./MapVoting"))
const Matches = React.lazy(() => import("./Matches"))
const OpeningBookPage = React.lazy(() => import("./OpeningBook"))
const PlayerProfile = React.lazy(() => import("./PlayerProfile"))
const PlayerRatings = React.lazy(() => import("./PlayerRatings"))
const PlayerRatingTrend = React.lazy(() =>
  import("./PlayerRatings").then((m) => ({
    default: m.DisplayPlayerRatingTrend,
  })),
)
const PlayerStats = React.lazy(() => import("./PlayerStats"))
const PlayerSynergy = React.lazy(() => import("./PlayerSynergy"))
const Powers = React.lazy(() => import("./Powers"))
const Superlatives = React.lazy(() => import("./Superlatives"))
const TeamStats = React.lazy(() => import("./TeamStats"))
const Tournaments = React.lazy(() => import("./Tournaments"))

// Grouped rather than one flat list of twenty-five: a newcomer scanning an
// undivided column has no way to tell "Choose Map" (draw tonight's map) from
// "Map Stats" (win rates per map). The split is by the question you arrived
// with — Games is the log of what happened, Stats is everything derived from
// it, Players is one person at a time, Maps is the map pool.
const HEADING_ORDER = [
  "Games",
  "Competition",
  "Play tonight",
  "Stats",
  "Players",
  "Maps",
  "Admin",
] as const

export const ROUTES: AppRoute[] = [
  // Games
  {
    slug: "matches",
    title: "Matches",
    icon: <ListIcon />,
    heading: "Games",
    gate: "public",
    Component: Matches,
  },
  {
    slug: "game-night",
    title: "Game Night",
    icon: <NightlightRoundIcon />,
    heading: "Games",
    gate: "public",
    Component: GameNight,
  },
  // Competition
  {
    slug: "tournaments",
    title: "Tournaments",
    icon: <EmojiEventsIcon />,
    heading: "Competition",
    gate: "public",
    Component: Tournaments,
  },
  {
    slug: "bracket",
    title: "1v1 Bracket",
    icon: <AccountTreeIcon />,
    heading: "Competition",
    gate: "public",
    Component: Bracket,
  },
  // Play tonight
  {
    slug: "balance-teams",
    title: "Balance Teams",
    icon: <BalanceIcon />,
    heading: "Play tonight",
    gate: "public",
    Component: BalanceTeams,
  },
  {
    // Was "Skip In and Out" in the nav while the page called itself "Map
    // Draft" — one name now, and it says what the page does.
    slug: "draft",
    title: "Map Draft",
    icon: <CasinoIcon />,
    heading: "Play tonight",
    gate: "public",
    Component: Draft,
  },
  // Stats
  {
    slug: "superlatives",
    title: "Records",
    icon: <WorkspacePremiumIcon />,
    heading: "Stats",
    gate: "public",
    Component: Superlatives,
  },
  {
    slug: "team-stats",
    title: "Team Stats",
    icon: <GroupsIcon />,
    heading: "Stats",
    gate: "public",
    Component: TeamStats,
  },
  {
    slug: "general-stats",
    title: "General Stats",
    icon: <MilitaryTechIcon />,
    heading: "Stats",
    gate: "public",
    Component: GeneralStats,
  },
  {
    slug: "powers",
    title: "Generals Powers",
    icon: <BoltIcon />,
    heading: "Stats",
    gate: "public",
    Component: Powers,
  },
  {
    slug: "game-length",
    title: "Game Length",
    icon: <HistoryToggleOffIcon />,
    heading: "Stats",
    gate: "public",
    Component: GameLength,
  },
  {
    slug: "ffa",
    title: "Free-For-All",
    icon: <SportsKabaddiIcon />,
    heading: "Stats",
    gate: "public",
    Component: FFA,
  },
  {
    slug: "opening-book",
    title: "Build Orders",
    icon: <MenuBookIcon />,
    heading: "Stats",
    gate: "public",
    Component: OpeningBookPage,
  },
  // Players
  {
    slug: "player-stats",
    title: "Player Stats",
    icon: <PersonIcon />,
    heading: "Players",
    gate: "public",
    Component: PlayerStats,
  },
  {
    slug: "player-profile",
    title: "Player Profile",
    icon: <BadgeIcon />,
    heading: "Players",
    gate: "public",
    Component: PlayerProfile,
  },
  {
    slug: "head-to-head",
    title: "Head to Head",
    icon: <CompareArrowsIcon />,
    heading: "Players",
    gate: "public",
    Component: HeadToHead,
  },
  {
    slug: "player-rating-trend",
    title: "Rating Trend",
    icon: <LeaderboardIcon />,
    heading: "Players",
    gate: "public",
    Component: PlayerRatingTrend,
  },
  {
    // Admin-gated in the nav because a rating *level* is not public — see the
    // root CLAUDE.md. The gate is the page, not the route.
    slug: "player-rating",
    title: "Player Ratings",
    icon: <LeaderboardIcon />,
    heading: "Players",
    gate: "admin",
    Component: PlayerRatings,
  },
  {
    slug: "player-synergy",
    title: "Player Synergy",
    icon: <GroupsIcon />,
    heading: "Players",
    gate: "admin",
    Component: PlayerSynergy,
  },
  // Maps
  {
    slug: "map-stats",
    title: "Map Stats",
    icon: <MapIcon />,
    heading: "Maps",
    gate: "public",
    Component: MapStats,
  },
  {
    slug: "map-voting",
    title: "Map Voting",
    icon: <HowToVoteIcon />,
    heading: "Maps",
    gate: "public",
    Component: MapVoting,
  },
  {
    slug: "choose-map",
    title: "Choose Map",
    icon: <CasinoIcon />,
    heading: "Maps",
    gate: "public",
    Component: ChooseMap,
  },
  {
    slug: "map-upload",
    title: "Upload Map",
    icon: <UploadFileIcon />,
    heading: "Maps",
    gate: "public",
    Component: MapUpload,
  },
  // Admin
  {
    slug: "debug-data",
    title: "Debug Matchid",
    icon: <TableView />,
    heading: "Admin",
    gate: "admin",
    Component: DebugData,
  },
  {
    slug: "admin-panel",
    title: "Admin",
    icon: <AdminPanelSettingsIcon />,
    heading: "Admin",
    gate: "opsAdmin",
    Component: AdminPanel,
  },
  // Reachable from the app bar rather than the sidebar, so it carries no
  // heading of its own — `navGroups` drops it from the nav automatically.
  {
    slug: "account",
    title: "Account",
    icon: <PersonIcon />,
    heading: "",
    gate: "public",
    Component: Account,
  },
]

export const DEFAULT_ROUTE = ROUTES[0]

const BY_SLUG = new Map(ROUTES.map((r) => [r.slug, r]))

export function routeBySlug(
  slug: string | null | undefined,
): AppRoute | undefined {
  return slug ? BY_SLUG.get(slug) : undefined
}

/** The query param the app used to route on, before paths. A link pasted into
 * Discord months ago still carries it, so `LegacyPageRedirect` in App.tsx
 * translates it rather than letting it silently land on Matches. */
export const LEGACY_PAGE_PARAM = "page"

/** Nav groups in display order, with routes the viewer may not see removed.
 * A group whose every route is gated away drops out, heading included. */
export function navGroups(opts: {
  isAdmin: boolean
  isOpsAdmin: boolean
}): RouteGroup[] {
  const visible = (gate: Gate) =>
    gate === "public" ||
    (gate === "admin" && opts.isAdmin) ||
    (gate === "opsAdmin" && opts.isOpsAdmin)

  return HEADING_ORDER.map((heading) => ({
    heading,
    routes: ROUTES.filter((r) => r.heading === heading && visible(r.gate)),
  })).filter((group) => group.routes.length > 0)
}
