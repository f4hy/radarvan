import ListIcon from "@mui/icons-material/List"
import BalanceIcon from "@mui/icons-material/Balance"
import TableView from "@mui/icons-material/TableView"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import MenuIcon from "@mui/icons-material/Menu"
import MilitaryTechIcon from "@mui/icons-material/MilitaryTech"
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
import DisplayDebugData from "./DebugData"
import DisplayPlayerRatings, { DisplayPlayerRatingTrend } from "./PlayerRatings"
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
import { isDebug } from "./utils"
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

export default function Menu() {
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const [selection, setSelection] = React.useState<Selection>("Matches")
  const debug = React.useMemo(() => isDebug(), [])
  const { status } = useAuth()

  // After returning from Discord without an in-game name yet, drop the user
  // straight onto the Account page to finish the one-time selection.
  const needsSelection = status?.user?.needs_player_selection ?? false
  React.useEffect(() => {
    if (needsSelection) {
      setSelection("Account")
    }
  }, [needsSelection])

  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const navItems: { value: Selection; text: string; icon: React.ReactNode }[] =
    [
      { value: "Matches", text: "Matches", icon: <ListIcon /> },
      { value: "PlayerStats", text: "Player Stats", icon: <PersonIcon /> },
      {
        value: "GeneralStats",
        text: "General Stats",
        icon: <MilitaryTechIcon />,
      },
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
              setSelection(s)
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
              onClick={() => setSelection("Account")}
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
        aria-label="mailbox folders"
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

type Selection =
  | "Matches"
  | "GeneralStats"
  | "PlayerStats"
  | "DebugData"
  | "MapStats"
  | "TeamStats"
  | "Tournaments"
  | "BalanceTeams"
  | "PlayerRating"
  | "PlayerRatingTrend"
  | "Superlatives"
  | "Draft"
  | "MapVoting"
  | "ChooseMap"
  | "MapUpload"
  | "Account"

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
    case "GeneralStats":
      return <DisplayGeneralStats />
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
