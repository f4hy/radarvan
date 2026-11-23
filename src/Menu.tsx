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
import ErrorBoundary from "./components/ErrorBoundary"
import Loading from "./components/Loading"
import SiteSearch from "./components/SiteSearch"
import radarvanLogo from "./img/radarvan_logo.webp"
import radarvanLogoDark from "./img/radarvan_logo_dark.webp"
import { useAuth } from "./lib/AuthContext"
import { startDiscordLogin } from "./lib/auth"
import type { ColorModePreference } from "./lib/ColorModeContext"
import { useColorMode } from "./lib/ColorModeContext"
import { EASE, pageEnterSx, REDUCED_MOTION } from "./lib/motion"
import { selectedTintSx } from "./lib/theme"
import { indicatorSx, useSlidingIndicator } from "./lib/useSlidingIndicator"
import { navGroups, type RouteGroup, routeBySlug } from "./routes"

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

const drawerWidth = 220

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

  const isAdmin = status?.user?.is_admin ?? false
  const isOpsAdmin = status?.user?.is_ops_admin ?? false
  const groups = React.useMemo(
    () => navGroups({ isAdmin, isOpsAdmin }),
    [isAdmin, isOpsAdmin],
  )

  // The app bar names the page, and takes that name from the same route entry
  // the sidebar and the page's own <h1> use. First segment only, so
  // `/match/123` still finds its route.
  const current = routeBySlug(pathname.split("/")[1])

  // After returning from Discord without an in-game name yet, drop the user
  // straight onto the Account page to finish the one-time selection.
  const needsSelection = status?.user?.needs_player_selection ?? false
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
            sx={(t) => ({
              width: "100%",
              height: "auto",
              display: "block",
              ...t.applyStyles("dark", { display: "none" }),
            })}
          />
          <Box
            component="img"
            src={radarvanLogoDark}
            alt="radarvan"
            sx={(t) => ({
              width: "100%",
              height: "auto",
              display: "none",
              ...t.applyStyles("dark", { display: "block" }),
            })}
          />
        </Box>
      </Toolbar>
      <Divider />
      <NavList groups={groups} onNavigate={() => setMobileOpen(false)} />
    </div>
  )

  return (
    <Box sx={{ display: "flex" }}>
      {/* Native scrollbars, date pickers and form controls follow the mode. */}
      <CssBaseline enableColorScheme />
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
          {/* Phones only: on wider screens the sidebar shows the logo and the
              page's own <h1> sits right below, so a title here repeats it. */}
          <Typography
            variant="h6"
            noWrap
            component="div"
            sx={{ display: { sm: "none" } }}
          >
            {current?.title ?? "Radarvan"}
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <SiteSearch groups={groups} />
          <ColorModeToggle />
          {/* Icon-only on phones: a long player name here squeezed the page
              title down to a few characters. */}
          {status?.logged_in ? (
            <>
              <IconButton
                color="inherit"
                aria-label="Account"
                component={Link}
                to="/account"
                sx={{ display: { xs: "inline-flex", sm: "none" } }}
              >
                <AccountCircleIcon />
              </IconButton>
              <Button
                color="inherit"
                startIcon={<AccountCircleIcon />}
                component={Link}
                to="/account"
                sx={{ display: { xs: "none", sm: "inline-flex" } }}
              >
                {status.user?.player_name ??
                  status.user?.discord_username ??
                  "Account"}
              </Button>
            </>
          ) : (
            <>
              <IconButton
                color="inherit"
                aria-label="Login"
                onClick={startDiscordLogin}
                sx={{ display: { xs: "inline-flex", sm: "none" } }}
              >
                <LoginIcon />
              </IconButton>
              <Button
                color="inherit"
                startIcon={<LoginIcon />}
                onClick={startDiscordLogin}
                sx={{ display: { xs: "none", sm: "inline-flex" } }}
              >
                Login
              </Button>
            </>
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
            "& .MuiBackdrop-root": { backdropFilter: "blur(3px)" },
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
          // dvh excludes the mobile browser's collapsing toolbar, so a short
          // page doesn't scroll by the toolbar's height.
          minHeight: "100vh",
          "@supports (min-height: 100dvh)": { minHeight: "100dvh" },
        }}
      >
        <Toolbar />
        {/* Keyed on the path so the fade replays on each navigation. */}
        <Box
          key={pathname}
          sx={{
            maxWidth: 1700,
            mx: "auto",
            mt: { xs: 1, sm: 2 },
            ...pageEnterSx,
          }}
        >
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

function NavList(props: { groups: RouteGroup[]; onNavigate: () => void }) {
  const { pathname } = useLocation()
  const { ref: listRef, rect: pill } = useSlidingIndicator<HTMLUListElement>(
    "a.active",
    pathname,
  )

  React.useLayoutEffect(() => {
    listRef.current
      ?.querySelector("a.active")
      ?.scrollIntoView({ block: "nearest" })
  }, [pathname, listRef])

  return (
    <List ref={listRef} sx={{ px: 1, pb: 2, position: "relative" }}>
      <Box
        aria-hidden
        sx={(t) => ({
          ...indicatorSx(pill),
          borderRadius: 1.5,
          ...selectedTintSx(t),
          "&::before": {
            content: '""',
            position: "absolute",
            left: 0,
            top: 9,
            bottom: 9,
            width: 3,
            borderRadius: 3,
            bgcolor: "primary.main",
          },
        })}
      />
      {props.groups.map((group) => (
        <React.Fragment key={group.heading}>
          <ListSubheader
            disableSticky
            sx={{
              bgcolor: "transparent",
              lineHeight: 1.9,
              mt: 1.5,
              px: 1.5,
              fontSize: "0.68rem",
              fontWeight: 700,
              letterSpacing: "0.1em",
              textTransform: "uppercase",
              color: "text.secondary",
              opacity: 0.8,
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
              onNavigate={props.onNavigate}
            />
          ))}
        </React.Fragment>
      ))}
    </List>
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
        transition: `background-color 160ms ${EASE}, transform 120ms ${EASE}`,
        "& .MuiListItemIcon-root, & .MuiListItemText-primary": {
          transition: `color 160ms ${EASE}, transform 200ms ${EASE}`,
        },
        "& .MuiSvgIcon-root": { fontSize: 20 },
        "&:hover .MuiListItemIcon-root": {
          color: "text.primary",
          transform: "translateX(2px)",
        },
        "&:active": { transform: "scale(0.98)" },
        // NavLink sets aria-current="page" on the active link, so the selected
        // styling reads off the same signal assistive tech does rather than a
        // separate `selected` prop that could disagree with the URL. The
        // background is NavList's sliding pill, not the row's own.
        "&.active": {
          "&:hover": { bgcolor: "transparent" },
          "& .MuiListItemIcon-root": {
            color: "primary.main",
            transform: "none",
          },
          "& .MuiListItemText-primary": {
            fontWeight: 650,
            color: "primary.main",
          },
        },
        [REDUCED_MOTION]: {
          "&, & *": { transition: "none" },
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
          primary: {
            sx: { fontSize: "0.9rem", fontWeight: 500, color: "text.primary" },
          },
        }}
      />
    </ListItemButton>
  )
}
