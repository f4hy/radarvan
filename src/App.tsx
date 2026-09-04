import { ThemeProvider } from "@mui/material/styles"
import { QueryClientProvider } from "@tanstack/react-query"
import * as React from "react"
import {
  BrowserRouter,
  Navigate,
  Route,
  Routes,
  useSearchParams,
} from "react-router"
import "./App.css"
import { AuthProvider } from "./AuthContext"
import { ColorModeProvider, useColorMode } from "./ColorModeContext"
import ErrorBoundary from "./ErrorBoundary"
import Menu from "./Menu"
import { PlayerColorsProvider } from "./PlayerColorsContext"
import NotFound from "./NotFound"
import { queryClient } from "./queryClient"
import { DEFAULT_ROUTE, LEGACY_PAGE_PARAM, ROUTES, routeBySlug } from "./routes"
import { buildTheme } from "./theme"

/**
 * The app routed on `?page=<slug>` before it had a router, and those links were
 * built to be pasted into chat — so they exist, in Discord scrollback, forever.
 * This translates one into its path form, carrying the rest of the query string
 * (`date`, `player`, `player1`/`player2`) across untouched.
 *
 * `replace` so the legacy URL doesn't sit in history as a step to go Back to.
 * An unknown `?page=` value falls through to the default page rather than the
 * not-found screen: it is more likely a slug this app renamed than a typo, and
 * the visitor came from a link somebody else wrote.
 */
function LegacyPageRedirect() {
  const [params] = useSearchParams()
  const page = params.get(LEGACY_PAGE_PARAM)
  if (page === null) {
    return <Navigate to={`/${DEFAULT_ROUTE.slug}`} replace />
  }
  const target = routeBySlug(page) ?? DEFAULT_ROUTE
  const rest = new URLSearchParams(params)
  rest.delete(LEGACY_PAGE_PARAM)
  const query = rest.toString()
  return <Navigate to={`/${target.slug}${query ? `?${query}` : ""}`} replace />
}

// The root boundary can't assume the theme or the router mounted, so its
// fallback is plain DOM rather than MUI components.
function RootFallback(error: Error) {
  return (
    <div style={{ padding: 24, fontFamily: "system-ui, sans-serif" }}>
      <h1 style={{ fontSize: 20 }}>Radarvan failed to start</h1>
      <p>Reloading the page usually clears this.</p>
      <pre style={{ whiteSpace: "pre-wrap", color: "#5b6675" }}>
        {error.message}
      </pre>
    </div>
  )
}

// Reads the resolved light/dark mode and hands ThemeProvider a matching
// theme — split out so ColorModeProvider can sit outside it (the theme
// depends on the mode; the mode doesn't depend on the theme).
function ThemedApp(props: { children: React.ReactNode }) {
  const { mode } = useColorMode()
  const theme = React.useMemo(() => buildTheme(mode), [mode])
  return <ThemeProvider theme={theme}>{props.children}</ThemeProvider>
}

export default function App() {
  return (
    <div className="App">
      <ErrorBoundary fallback={RootFallback}>
        <ColorModeProvider>
          <ThemedApp>
            <QueryClientProvider client={queryClient}>
              <BrowserRouter>
                <AuthProvider>
                  <PlayerColorsProvider>
                    <Routes>
                      <Route element={<Menu />}>
                        <Route index element={<LegacyPageRedirect />} />
                        {ROUTES.map((route) => (
                          <Route
                            key={route.slug}
                            path={route.slug}
                            element={<route.Component />}
                          />
                        ))}
                        <Route path="*" element={<NotFound />} />
                      </Route>
                    </Routes>
                  </PlayerColorsProvider>
                </AuthProvider>
              </BrowserRouter>
            </QueryClientProvider>
          </ThemedApp>
        </ColorModeProvider>
      </ErrorBoundary>
    </div>
  )
}
