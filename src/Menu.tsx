import ListIcon from "@mui/icons-material/List"
import BalanceIcon from "@mui/icons-material/Balance"
import TableView from "@mui/icons-material/TableView"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import MenuIcon from "@mui/icons-material/Menu"
import MilitaryTechIcon from "@mui/icons-material/MilitaryTech"
import SportsKabaddiIcon from "@mui/icons-material/SportsKabaddi"
import PersonIcon from "@mui/icons-material/Person"
import AccountCircleIcon from "@mui/icons-material/AccountCircle"
import LoginIcon from "@mui/icons-material/Login"
import AppBar from "@mui/material/AppBar"
import Button from "@mui/material/Button"
import Box from "@mui/material/Box"
import CssBaseline from "@mui/material/CssBaseline"
import Divider from "@mui/material/Divider"
import Drawer from "@mui/material/Drawer"
import IconButton from "@mui/material/IconButton"
import List from "@mui/material/List"
import ListItemButton from "@mui/material/ListItemButton"
import ListItemIcon from "@mui/material/ListItemIcon"
import ListItemText from "@mui/material/ListItemText"
import Toolbar from "@mui/material/Toolbar"
import Typography from "@mui/material/Typography"
import * as React from "react"
import DisplayGeneralStats from "./GeneralStats"
import DisplayBalanceTeams from "./BalanceTeams"
import DisplayMatches from "./Matches"
import DisplayPlayerStats from "./PlayerStats"
import DisplayFFAStats from "./FFA"
import HeadToHead from "./HeadToHead"
import CompareArrowsIcon from "@mui/icons-material/CompareArrows"
import DisplayDebugData from "./DebugData"
import DisplayPlayerRatings, { DisplayPlayerRatingTrend } from "./PlayerRatings"
import DisplayPlayerSynergy from "./PlayerSynergy"
import LeaderboardIcon from "@mui/icons-material/Leaderboard"
import GroupsIcon from "@mui/icons-material/Groups"
import MapIcon from "@mui/icons-material/Map"
import DisplayTournamentResults from "./Tournaments"
import DisplayMapStats from "./MapStats"
import DisplayTeamStats from "./TeamStats"
import DisplaySuperlatives from "./Superlatives"
import WorkspacePremiumIcon from "@mui/icons-material/WorkspacePremium"
import CasinoIcon from "@mui/icons-material/Casino"
import HowToVoteIcon from "@mui/icons-material/HowToVote"
import DisplayDraft from "./Draft"
import MapVoting from "./MapVoting"
import ChooseMap from "./ChooseMap"
import MapUpload from "./MapUpload"
import Account from "./Account"
import UploadFileIcon from "@mui/icons-material/UploadFile"
import { useAuth } from "./AuthContext"
import { startDiscordLogin } from "./auth"
import radarvanLogo from "./img/radarvan_logo.webp"
const drawerWidth = 190

const ALL_SELECTIONS = [
  "Matches",
  "GeneralStats",
  "PlayerStats",
  "FFA",
  "HeadToHead",
  "DebugData",
  "MapStats",
  "TeamStats",
  "Tournaments",
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

function pushPage(s: Selection): void {
  const params = new URLSearchParams(window.location.search)
  params.set("page", toSlug(s))
  window.history.pushState(null, "", `?${params.toString()}`)
}

export default function Menu() {
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const [selection, setSelection] = React.useState<Selection>(selectionFromUrl)
  const { status } = useAuth()
  const debug = status?.user?.is_admin ?? false

  // Navigate to a page and reflect it in the URL (?page=) so it's shareable.
  const navigate = React.useCallback((s: Selection) => {
    setSelection(s)
    pushPage(s)
  }, [])

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

  const navItems: { value: Selection; text: string; icon: React.ReactNode }[] =
    [
      { value: "Matches", text: "Matches", icon: <ListIcon /> },
      { value: "PlayerStats", text: "Player Stats", icon: <PersonIcon /> },
      {
        value: "HeadToHead",
        text: "Head to Head",
        icon: <CompareArrowsIcon />,
      },
      {
        value: "GeneralStats",
        text: "General Stats",
        icon: <MilitaryTechIcon />,
      },
      { value: "FFA", text: "Free-For-All", icon: <SportsKabaddiIcon /> },
      { value: "Tournaments", text: "Tournaments", icon: <EmojiEventsIcon /> },
      { value: "BalanceTeams", text: "Balance Teams", icon: <BalanceIcon /> },
      { value: "MapStats", text: "Map Stats", icon: <MapIcon /> },
      { value: "TeamStats", text: "Team Stats", icon: <GroupsIcon /> },
      {
        value: "Superlatives",
        text: "Records",
        icon: <WorkspacePremiumIcon />,
      },
      { value: "Draft", text: "Skip In and Out", icon: <CasinoIcon /> },
      { value: "MapVoting", text: "Map Voting", icon: <HowToVoteIcon /> },
      { value: "ChooseMap", text: "Choose Map", icon: <CasinoIcon /> },
      { value: "MapUpload", text: "Upload Map", icon: <UploadFileIcon /> },
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
            { value: "DebugData", text: "Debug Matchid", icon: <TableView /> },
          ] as const)
        : []),
    ]

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
      <List sx={{ px: 1 }}>
        {navItems.map((item) => (
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
      </List>
    </div>
  )

  return (
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
          <Typography variant="h6" noWrap component="div" sx={{ flexGrow: 1 }}>
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
          <Main selection={selection} />
        </Box>
      </Box>
    </Box>
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
    case "PlayerStats":
      return <DisplayPlayerStats />
    case "HeadToHead":
      return <HeadToHead />
    case "GeneralStats":
      return <DisplayGeneralStats />
    case "FFA":
      return <DisplayFFAStats />
    case "Tournaments":
      return <DisplayTournamentResults />
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
        minHeight: 44,
        borderRadius: 1.5,
        mb: 0.25,
        px: 1.5,
      }}
      onClick={() => props.callback(props.value)}
    >
      <ListItemIcon
        sx={{
          minWidth: 0,
          mr: 2,
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
            fontWeight: props.selected ? 700 : 500,
            color: props.selected ? "primary.main" : "text.primary",
          },
        }}
      />
    </ListItemButton>
  )
}
