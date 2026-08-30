import { ThemeProvider } from "@mui/material/styles"
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
import Menu from "./Menu"
import { PlayerColorsProvider } from "./PlayerColorsContext"
import NotFound from "./NotFound"
import { DEFAULT_ROUTE, LEGACY_PAGE_PARAM, ROUTES, routeBySlug } from "./routes"
import theme from "./theme"

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

export default function App() {
  return (
    <div className="App">
      <ThemeProvider theme={theme}>
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
      </ThemeProvider>
    </div>
  )
}
