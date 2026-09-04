import AccountCircleIcon from "@mui/icons-material/AccountCircle"
import DarkModeIcon from "@mui/icons-material/DarkMode"
import LightModeIcon from "@mui/icons-material/LightMode"
import LoginIcon from "@mui/icons-material/Login"
import MenuIcon from "@mui/icons-material/Menu"
import SettingsBrightnessIcon from "@mui/icons-material/SettingsBrightness"
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
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router"
import { useAuth } from "./AuthContext"
import type { ColorModePreference } from "./ColorModeContext"
import { useColorMode } from "./ColorModeContext"
import ErrorBoundary from "./ErrorBoundary"
import { startDiscordLogin } from "./auth"
import radarvanLogo from "./img/radarvan_logo.webp"
import Loading from "./Loading"
import { navGroups, routeBySlug } from "./routes"

// Cycles system -> light -> dark -> system on click, and shows the current
// preference (not just the resolved mode) so "system" stays visible as a
// distinct state rather than silently collapsing into whatever it resolved
// to today.
const NEXT_PREFERENCE: Record<ColorModePreference, ColorModePreference> = {
  system: "light",
  light: "dark",
  dark: "system",
}
const COLOR_MODE_ICON: Record<ColorModePreference, React.ReactNode> = {
  system: <SettingsBrightnessIcon />,
  light: <LightModeIcon />,
  dark: <DarkModeIcon />,
}
const COLOR_MODE_LABEL: Record<ColorModePreference, string> = {
  system: "Matching your system",
  light: "Light",
  dark: "Dark",
}

function ColorModeToggle() {
  const { preference, setPreference } = useColorMode()
  return (
    <Tooltip title={`Theme: ${COLOR_MODE_LABEL[preference]} (click to change)`}>
      <IconButton
        color="inherit"
        aria-label="Toggle color mode"
        onClick={() => setPreference(NEXT_PREFERENCE[preference])}
      >
        {COLOR_MODE_ICON[preference]}
      </IconButton>
    </Tooltip>
  )
}

const drawerWidth = 204

/**
 * The app shell: top bar, sidebar, and the slot the routed page renders into.
 *
 * It used to be the router too — it held the current page in state, wrote
 * `?page=` by hand, and picked the component out of a 25-arm switch. All of
 * that is `routes.tsx` and `App.tsx` now, which is why nav items can be plain
 * links: a `ListItemButton component={NavLink}` renders a real `<a href>`, so
 * middle-click, ⌘-click and "copy link address" work, and the browser handles
 * history instead of a `popstate` listener.
 */
export default function Menu() {
  const [mobileOpen, setMobileOpen] = React.useState(false)
  const { status } = useAuth()
  const { pathname } = useLocation()
  const navigate = useNavigate()

  const isAdmin = status?.user?.isAdmin ?? false
  const isOpsAdmin = status?.user?.isOpsAdmin ?? false
  const groups = React.useMemo(
    () => navGroups({ isAdmin, isOpsAdmin }),
    [isAdmin, isOpsAdmin],
  )

  // The app bar names the page, and takes that name from the same route entry
  // the sidebar and the page's own <h1> use.
  const current = routeBySlug(pathname.replace(/^\//, ""))

  // After returning from Discord without an in-game name yet, drop the user
  // straight onto the Account page to finish the one-time selection.
  const needsSelection = status?.user?.needsPlayerSelection ?? false
  React.useEffect(() => {
    if (needsSelection) navigate("/account")
  }, [needsSelection, navigate])

  const handleDrawerToggle = () => setMobileOpen((open) => !open)

  const drawer = (
    <div>
      <Toolbar sx={{ px: 2 }}>
        <Box
          component={Link}
          to="/"
          sx={{ display: "block", width: "100%", maxWidth: 150 }}
        >
          <Box
            component="img"
            src={radarvanLogo}
            alt="radarvan"
            sx={{ width: "100%", height: "auto", display: "block" }}
          />
        </Box>
      </Toolbar>
      <Divider />
      <List sx={{ px: 1, pb: 2 }}>
        {groups.map((group) => (
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
            {group.routes.map((route) => (
              <MenuItem
                key={route.slug}
                slug={route.slug}
                text={route.title}
                icon={route.icon}
                onNavigate={() => setMobileOpen(false)}
              />
            ))}
          </React.Fragment>
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
            {current?.title ?? "Radarvan"}
          </Typography>
          <ColorModeToggle />
          {status?.loggedIn ? (
            <Button
              color="inherit"
              startIcon={<AccountCircleIcon />}
              component={Link}
              to="/account"
            >
              {status.user?.playerName ??
                status.user?.discordUsername ??
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
          {/* Keyed on the path so navigating away clears a caught error
              rather than pinning the boundary open on the next page. */}
          <ErrorBoundary key={pathname} what="this page">
            <React.Suspense fallback={<Loading />}>
              <Outlet />
            </React.Suspense>
          </ErrorBoundary>
        </Box>
      </Box>
    </Box>
  )
}

function MenuItem(props: {
  slug: string
  text: string
  icon: React.ReactNode
  onNavigate: () => void
}) {
  return (
    <ListItemButton
      component={NavLink}
      to={`/${props.slug}`}
      onClick={props.onNavigate}
      sx={{
        minHeight: 38,
        borderRadius: 1.5,
        mb: 0.25,
        px: 1.5,
        // NavLink sets aria-current="page" on the active link, so the selected
        // styling reads off the same signal assistive tech does rather than a
        // separate `selected` prop that could disagree with the URL.
        "&.active": {
          bgcolor: "rgba(47, 109, 240, 0.12)",
          "&:hover": { bgcolor: "rgba(47, 109, 240, 0.18)" },
          "& .MuiListItemIcon-root": { color: "primary.main" },
          "& .MuiListItemText-primary": {
            fontWeight: 700,
            color: "primary.main",
          },
        },
      }}
    >
      <ListItemIcon
        sx={{
          minWidth: 0,
          mr: 1.5,
          justifyContent: "center",
          color: "text.secondary",
        }}
      >
        {props.icon}
      </ListItemIcon>
      <ListItemText
        primary={props.text}
        slotProps={{
          primary: { sx: { fontWeight: 500, color: "text.primary" } },
        }}
      />
    </ListItemButton>
  )
}
