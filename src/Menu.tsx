import ListIcon from "@mui/icons-material/List"
import LooksTwoIcon from "@mui/icons-material/LooksTwo"
import MapIcon from "@mui/icons-material/Map"
import MenuIcon from "@mui/icons-material/Menu"
import MilitaryTechIcon from "@mui/icons-material/MilitaryTech"
import PeopleIcon from "@mui/icons-material/People"
import PersonIcon from "@mui/icons-material/Person"
import AppBar from "@mui/material/AppBar"
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
import DisplayMapStats from "./MapStats"
import DisplayMatches from "./Matches"
import DisplayPairStats from "./PairStats"
import DisplayPlayerStats from "./PlayerStats"
import DisplayTeamStats from "./TeamStats"
import WrappedYear from "./Wrapped"
import RedeemIcon from "@mui/icons-material/Redeem"

const drawerWidth = 190

export default function Menu() {
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const [selection, setSelection] = React.useState<Selection>("Matches")
  const handleDrawerToggle = () => {
    setMobileOpen(!mobileOpen)
  }

  const drawer = (
    <div>
      <Toolbar />
      <Divider />
      <List>
        <MenuItem
          value="Matches"
          text="Matches"
          open={true}
          icon={<ListIcon />}
          callback={setSelection}
        />
        <MenuItem
          value="PlayerStats"
          text="Player Stats"
          open={true}
          icon={<PersonIcon />}
          callback={setSelection}
        />
        <MenuItem
          value="TeamStats"
          text="Team Stats"
          open={true}
          icon={<PeopleIcon />}
          callback={setSelection}
        />
        <MenuItem
          value="GeneralStats"
          text="General Stats"
          open={true}
          icon={<MilitaryTechIcon />}
          callback={setSelection}
        />
      </List>
      <Divider />
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
          <Typography variant="h6" noWrap component="div">
            {selection}
          </Typography>
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
          p: 3,
          width: { sm: `calc(100% - ${drawerWidth}px)` },
        }}
      >
        <Toolbar />
        <Main selection={selection} />
      </Box>
    </Box>
  )
}

type Selection =
  | "Matches"
  | "GeneralStats"
  | "PlayerStats"
  | "TeamStats"
  | "MapStats"
  | "PairStats"
  | "Wrapped"

interface MenuItemProps {
  open: boolean
  value: Selection
  text: string
  icon: React.ReactNode
  callback: (s: Selection) => void
}

function Main(props: { selection: Selection }) {
  switch (props.selection) {
    case "Matches":
      return <DisplayMatches />
    case "PlayerStats":
      return <DisplayPlayerStats />
    case "GeneralStats":
      return <DisplayGeneralStats />
    case "TeamStats":
      return <DisplayTeamStats />
    default:
      return <div>{props.selection}</div>
  }
}

function MenuItem(props: MenuItemProps) {
  const open = props.open
  return (
    <ListItemButton
      key={props.value}
      sx={{
        minHeight: 48,
        justifyContent: { open } ? "initial" : "center",
        px: 2.5,
      }}
      onClick={() => props.callback(props.value)}
    >
      <ListItemIcon
        sx={{
          minWidth: 0,
          mr: open ? 3 : "auto",
          justifyContent: "center",
        }}
      >
        {props.icon}
      </ListItemIcon>
      <ListItemText primary={props.text} sx={{ opacity: open ? 1 : 0 }} />
    </ListItemButton>
  )
}
