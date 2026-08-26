import AccountCircleIcon from "@mui/icons-material/AccountCircle"
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings"
import AccountTreeIcon from "@mui/icons-material/AccountTree"
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
import LoginIcon from "@mui/icons-material/Login"
import MapIcon from "@mui/icons-material/Map"
import MenuIcon from "@mui/icons-material/Menu"
import MilitaryTechIcon from "@mui/icons-material/MilitaryTech"
import NightlightRoundIcon from "@mui/icons-material/NightlightRound"
import PersonIcon from "@mui/icons-material/Person"
import SportsKabaddiIcon from "@mui/icons-material/SportsKabaddi"
import TableView from "@mui/icons-material/TableView"
import UploadFileIcon from "@mui/icons-material/UploadFile"
import WorkspacePremiumIcon from "@mui/icons-material/WorkspacePremium"
import AppBar from "@mui/material/AppBar"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import CssBaseline from "@mui/material/CssBaseline"
import Divider from "@mui/material/Divider"
import Drawer from "@mui/material/Drawer"
import IconButton from "@mui/material/IconButton"
import List from "@mui/material/List"
import ListItemButton from "@mui/material/ListItemButton"
import ListItemIcon from "@mui/material/ListItemIcon"
import ListItemText from "@mui/material/ListItemText"
import ListSubheader from "@mui/material/ListSubheader"
import Toolbar from "@mui/material/Toolbar"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { useAuth } from "./AuthContext"
import { startDiscordLogin } from "./auth"
import radarvanLogo from "./img/radarvan_logo.webp"
import Loading from "./Loading"
import { PlayerNavProvider, type PlayerNav } from "./PlayerNavContext"

// Every page is code-split: the initial bundle would otherwise carry all of
// them (recharts, the bracket, html2canvas, …) just to render the default
// Matches list. Keep new pages lazy too.
const Account = React.lazy(() => import("./Account"))
const AdminPanel = React.lazy(() => import("./AdminPanel"))
const DisplayBalanceTeams = React.lazy(() => import("./BalanceTeams"))
const DisplayBracket = React.lazy(() => import("./Bracket"))
const ChooseMap = React.lazy(() => import("./ChooseMap"))
const GameLength = React.lazy(() => import("./GameLength"))
const GameNight = React.lazy(() => import("./GameNight"))
const DisplayDebugData = React.lazy(() => import("./DebugData"))
const DisplayDraft = React.lazy(() => import("./Draft"))
const DisplayFFAStats = React.lazy(() => import("./FFA"))
const DisplayGeneralStats = React.lazy(() => import("./GeneralStats"))
const HeadToHead = React.lazy(() => import("./HeadToHead"))
const DisplayMapStats = React.lazy(() => import("./MapStats"))
const MapUpload = React.lazy(() => import("./MapUpload"))
const MapVoting = React.lazy(() => import("./MapVoting"))
const DisplayMatches = React.lazy(() => import("./Matches"))
const DisplayPlayerProfile = React.lazy(() => import("./PlayerProfile"))
const DisplayPlayerRatings = React.lazy(() => import("./PlayerRatings"))
const DisplayPlayerRatingTrend = React.lazy(() =>
  import("./PlayerRatings").then((m) => ({
    default: m.DisplayPlayerRatingTrend,
  })),
)
const DisplayPlayerStats = React.lazy(() => import("./PlayerStats"))
const DisplayPowers = React.lazy(() => import("./Powers"))
const DisplayPlayerSynergy = React.lazy(() => import("./PlayerSynergy"))
const DisplaySuperlatives = React.lazy(() => import("./Superlatives"))
const DisplayTeamStats = React.lazy(() => import("./TeamStats"))
const DisplayTournamentResults = React.lazy(() => import("./Tournaments"))

const drawerWidth = 204

interface NavGroup {
  heading: string
  items: { value: Selection; text: string; icon: React.ReactNode }[]
}

const ALL_SELECTIONS = [
  "Matches",
  "GameNight",
  "GameLength",
  "GeneralStats",
  "Powers",
  "PlayerStats",
  "PlayerProfile",
  "FFA",
  "HeadToHead",
  "DebugData",
  "MapStats",
  "TeamStats",
  "Tournaments",
  "Bracket",
  "BalanceTeams",
  "PlayerRating",
  "PlayerRatingTrend",
  "PlayerSynergy",
  "Superlatives",
  "Draft",
  "MapVoting",
  "ChooseMap",
  "MapUpload",
  "Account",
  "AdminPanel",
] as const

type Selection = (typeof ALL_SELECTIONS)[number]

// Selection <-> URL slug (e.g. "PlayerStats" <-> "player-stats") so each page is
// linkable/bookmarkable via ?page=.
function toSlug(s: Selection): string {
  return s.replace(/([a-z0-9])([A-Z])/g, "$1-$2").toLowerCase()
}

const SLUG_TO_SELECTION: Record<string, Selection> = Object.fromEntries(
  ALL_SELECTIONS.map((s) => [toSlug(s), s]),
)

function selectionFromUrl(): Selection {
  const slug = new URLSearchParams(window.location.search).get("page")
  return (slug ? SLUG_TO_SELECTION[slug] : undefined) ?? "Matches"
}

function pushPage(s: Selection, extraParams?: Record<string, string>): void {
  const params = new URLSearchParams(window.location.search)
  params.set("page", toSlug(s))
  for (const [key, value] of Object.entries(extraParams ?? {})) {
    params.set(key, value)
  }
  window.history.pushState(null, "", `?${params.toString()}`)
}

export default function Menu() {
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const [selection, setSelection] = React.useState<Selection>(selectionFromUrl)
  const { status } = useAuth()
  const debug = status?.user?.is_admin ?? false
  const opsAdmin = status?.user?.is_ops_admin ?? false

  // Navigate to a page and reflect it in the URL (?page=) so it's shareable.
  const navigate = React.useCallback((s: Selection) => {
    setSelection(s)
    pushPage(s)
  }, [])

  // Jump straight to a specific player's profile (e.g. from a clickable
  // PlayerChip elsewhere) - sets both URL params PlayerProfile reads
  // (`page` and `player`) in one history entry, then switches the page.
  const goToPlayerProfile = React.useCallback((playerName: string) => {
    setSelection("PlayerProfile")
    pushPage("PlayerProfile", { player: playerName })
  }, [])

  // Same idea for jumping straight to two players' head-to-head record.
  const goToHeadToHead = React.useCallback(
    (player1: string, player2: string) => {
      setSelection("HeadToHead")
      pushPage("HeadToHead", { player1, player2 })
    },
    [],
  )

  const playerNav: PlayerNav = React.useMemo(
    () => ({ goToPlayerProfile, goToHeadToHead }),
    [goToPlayerProfile, goToHeadToHead],
  )

  // Keep in sync with browser back/forward.
  React.useEffect(() => {
    const onPop = () => setSelection(selectionFromUrl())
    window.addEventListener("popstate", onPop)
    return () => window.removeEventListener("popstate", onPop)
  }, [])

  // After returning from Discord without an in-game name yet, drop the user
  // straight onto the Account page to finish the one-time selection.
  const needsSelection = status?.user?.needs_player_selection ?? false
  React.useEffect(() => {
    if (needsSelection) {
      navigate("Account")
    }
  }, [needsSelection, navigate])

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  // Grouped rather than one flat list of nineteen: a newcomer scanning an
  // undivided column has no way to tell "Choose Map" (draw tonight's map) from
  // "Map Stats" (win rates per map). The split is by the question you arrived
  // with: Games is the log of what happened, Stats is everything derived from
  // it, Players is one person at a time, Maps is the map pool.
  // Each item's `text` is also the page's own <h1>, so the nav and the page
  // never disagree about what a page is called.
  const allGroups: NavGroup[] = [
    {
      heading: "Games",
      items: [
        { value: "Matches", text: "Matches", icon: <ListIcon /> },
        {
          value: "GameNight",
          text: "Game Night",
          icon: <NightlightRoundIcon />,
        },
      ],
    },
    {
      heading: "Competition",
      items: [
        {
          value: "Tournaments",
          text: "Tournaments",
          icon: <EmojiEventsIcon />,
        },
        { value: "Bracket", text: "1v1 Bracket", icon: <AccountTreeIcon /> },
      ],
    },
    {
      heading: "Play tonight",
      items: [
        { value: "BalanceTeams", text: "Balance Teams", icon: <BalanceIcon /> },
        // Was "Skip In and Out" in the nav while the page called itself "Map
        // Draft" — one name now, and it says what the page does.
        { value: "Draft", text: "Map Draft", icon: <CasinoIcon /> },
      ],
    },
    {
      heading: "Stats",
      items: [
        {
          value: "Superlatives",
          text: "Records",
          icon: <WorkspacePremiumIcon />,
        },
        { value: "TeamStats", text: "Team Stats", icon: <GroupsIcon /> },
        {
          value: "GeneralStats",
          text: "General Stats",
          icon: <MilitaryTechIcon />,
        },
        {
          value: "Powers",
          text: "Generals Powers",
          icon: <BoltIcon />,
        },
        {
          value: "GameLength",
          text: "Game Length",
          icon: <HistoryToggleOffIcon />,
        },
        { value: "FFA", text: "Free-For-All", icon: <SportsKabaddiIcon /> },
      ],
    },
    {
      heading: "Players",
      items: [
        { value: "PlayerStats", text: "Player Stats", icon: <PersonIcon /> },
        { value: "PlayerProfile", text: "Player Profile", icon: <BadgeIcon /> },
        {
          value: "HeadToHead",
          text: "Head to Head",
          icon: <CompareArrowsIcon />,
        },
        {
          value: "PlayerRatingTrend",
          text: "Rating Trend",
          icon: <LeaderboardIcon />,
        },
        ...(debug
          ? ([
              {
                value: "PlayerRating",
                text: "Player Ratings",
                icon: <LeaderboardIcon />,
              },
              {
                value: "PlayerSynergy",
                text: "Player Synergy",
                icon: <GroupsIcon />,
              },
            ] as const)
          : []),
      ],
    },
    {
      heading: "Maps",
      items: [
        { value: "MapStats", text: "Map Stats", icon: <MapIcon /> },
        { value: "MapVoting", text: "Map Voting", icon: <HowToVoteIcon /> },
        { value: "ChooseMap", text: "Choose Map", icon: <CasinoIcon /> },
        { value: "MapUpload", text: "Upload Map", icon: <UploadFileIcon /> },
      ],
    },
    {
      heading: "Admin",
      items: [
        ...(debug
          ? ([
              {
                value: "DebugData",
                text: "Debug Matchid",
                icon: <TableView />,
              },
            ] as const)
          : []),
        ...(opsAdmin
          ? ([
              {
                value: "AdminPanel",
                text: "Admin",
                icon: <AdminPanelSettingsIcon />,
              },
            ] as const)
          : []),
      ],
    },
  ]
  // Any group whose items are all gated away drops out, heading included — so
  // a new gated group gets this for free.
  const navGroups = allGroups.filter((group) => group.items.length > 0)

  const navItems = navGroups.flatMap((g) => g.items)

  const drawer = (
    <div>
      <Toolbar sx={{ px: 2 }}>
        <Box
          component="img"
          src={radarvanLogo}
          alt="radarvan"
          sx={{
            width: "100%",
            maxWidth: 150,
            height: "auto",
            display: "block",
          }}
        />
      </Toolbar>
      <Divider />
      <List sx={{ px: 1, pb: 2 }}>
        {navGroups.map((group) => (
          <React.Fragment key={group.heading}>
            <ListSubheader
              disableSticky
              sx={{
                bgcolor: "transparent",
                lineHeight: 1.9,
                mt: 1,
                px: 1.5,
                fontSize: "0.7rem",
                letterSpacing: "0.08em",
                textTransform: "uppercase",
                color: "text.secondary",
              }}
            >
              {group.heading}
            </ListSubheader>
            {group.items.map((item) => (
              <MenuItem
                key={item.value}
                value={item.value}
                text={item.text}
                icon={item.icon}
                selected={selection === item.value}
                callback={(s) => {
                  navigate(s)
                  setMobileOpen(false)
                }}
              />
            ))}
          </React.Fragment>
        ))}
      </List>
    </div>
  )

  return (
    <PlayerNavProvider value={playerNav}>
      <Box sx={{ display: "flex" }}>
        <CssBaseline />
        <AppBar
          position="fixed"
          sx={{
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            ml: { sm: `${drawerWidth}px` },
          }}
        >
          <Toolbar>
            <IconButton
              color="inherit"
              aria-label="open drawer"
              edge="start"
              onClick={handleDrawerToggle}
              sx={{ mr: 2, display: { sm: "none" } }}
            >
              <MenuIcon />
            </IconButton>
            <Typography
              variant="h6"
              noWrap
              component="div"
              sx={{ flexGrow: 1 }}
            >
              {navItems.find((i) => i.value === selection)?.text ?? selection}
            </Typography>
            {status?.logged_in ? (
              <Button
                color="inherit"
                startIcon={<AccountCircleIcon />}
                onClick={() => navigate("Account")}
              >
                {status.user?.player_name ??
                  status.user?.discord_username ??
                  "Account"}
              </Button>
            ) : (
              <Button
                color="inherit"
                startIcon={<LoginIcon />}
                onClick={startDiscordLogin}
              >
                Login
              </Button>
            )}
          </Toolbar>
        </AppBar>
        <Box
          component="nav"
          sx={{ width: { sm: drawerWidth }, flexShrink: { sm: 0 } }}
          aria-label="Primary navigation"
        >
          <Drawer
            variant="temporary"
            open={mobileOpen}
            onClose={handleDrawerToggle}
            ModalProps={{
              keepMounted: true, // Better open performance on mobile.
            }}
            sx={{
              display: { xs: "block", sm: "none" },
              "& .MuiDrawer-paper": {
                boxSizing: "border-box",
                width: drawerWidth,
              },
            }}
          >
            {drawer}
          </Drawer>
          <Drawer
            variant="permanent"
            sx={{
              display: { xs: "none", sm: "block" },
              "& .MuiDrawer-paper": {
                boxSizing: "border-box",
                width: drawerWidth,
              },
            }}
            open
          >
            {drawer}
          </Drawer>
        </Box>
        <Box
          component="main"
          sx={{
            flexGrow: 1,
            p: { xs: 1.5, sm: 3 },
            width: { sm: `calc(100% - ${drawerWidth}px)` },
            minWidth: 0,
            bgcolor: "background.default",
            minHeight: "100vh",
          }}
        >
          <Toolbar />
          <Box sx={{ maxWidth: 1700, mx: "auto", mt: { xs: 1, sm: 2 } }}>
            <React.Suspense fallback={<Loading />}>
              <Main selection={selection} />
            </React.Suspense>
          </Box>
        </Box>
      </Box>
    </PlayerNavProvider>
  )
}

interface MenuItemProps {
  value: Selection
  text: string
  icon: React.ReactNode
  selected: boolean
  callback: (s: Selection) => void
  disabled?: boolean
}

function Main(props: { selection: Selection }) {
  switch (props.selection) {
    case "Matches":
      return <DisplayMatches />
    case "GameNight":
      return <GameNight />
    case "GameLength":
      return <GameLength />
    case "PlayerStats":
      return <DisplayPlayerStats />
    case "PlayerProfile":
      return <DisplayPlayerProfile />
    case "HeadToHead":
      return <HeadToHead />
    case "GeneralStats":
      return <DisplayGeneralStats />
    case "Powers":
      return <DisplayPowers />
    case "FFA":
      return <DisplayFFAStats />
    case "Tournaments":
      return <DisplayTournamentResults />
    case "Bracket":
      return <DisplayBracket />
    case "BalanceTeams":
      return <DisplayBalanceTeams />
    case "MapStats":
      return <DisplayMapStats />
    case "TeamStats":
      return <DisplayTeamStats />
    case "Superlatives":
      return <DisplaySuperlatives />
    case "PlayerRating":
      return <DisplayPlayerRatings />
    case "PlayerRatingTrend":
      return <DisplayPlayerRatingTrend />
    case "PlayerSynergy":
      return <DisplayPlayerSynergy />
    case "Draft":
      return <DisplayDraft />
    case "MapVoting":
      return <MapVoting />
    case "ChooseMap":
      return <ChooseMap />
    case "MapUpload":
      return <MapUpload />
    case "Account":
      return <Account />
    case "DebugData":
      return <DisplayDebugData />
    case "AdminPanel":
      return <AdminPanel />
    default:
      return <div>{props.selection}</div>
  }
}

function MenuItem(props: MenuItemProps) {
  return (
    <ListItemButton
      key={props.value}
      disabled={props.disabled}
      selected={props.selected}
      sx={{
        minHeight: 38,
        borderRadius: 1.5,
        mb: 0.25,
        px: 1.5,
      }}
      onClick={() => props.callback(props.value)}
    >
      <ListItemIcon
        sx={{
          minWidth: 0,
          mr: 1.5,
          justifyContent: "center",
          color: props.selected ? "primary.main" : "text.secondary",
        }}
      >
        {props.icon}
      </ListItemIcon>
      <ListItemText
        primary={props.text}
        slotProps={{
          primary: {
            sx: {
              fontWeight: props.selected ? 700 : 500,
              color: props.selected ? "primary.main" : "text.primary",
            },
          },
        }}
      />
    </ListItemButton>
  )
}
