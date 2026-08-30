import Button from "@mui/material/Button"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import { Link, useLocation } from "react-router"
import Page from "./Page"
import { DEFAULT_ROUTE } from "./routes"

/**
 * A path the router doesn't know. The server hands any non-`/api` path to the
 * app shell (see `http_cache.CachedStaticFiles`), so this is what a mistyped or
 * retired URL reaches — previously the switch's `default` arm printed the raw
 * selection string into a bare `<div>`.
 */
export default function NotFound() {
  const { pathname } = useLocation()
  return (
    <Page title="Page not found" width="narrow">
      <Stack spacing={2} sx={{ alignItems: "flex-start" }}>
        <Typography variant="body1">
          There's nothing at <code>{pathname}</code>.
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          If you followed a link from chat, the page may have been renamed since
          it was posted. Everything is reachable from the sidebar.
        </Typography>
        <Button
          variant="contained"
          component={Link}
          to={`/${DEFAULT_ROUTE.slug}`}
        >
          Go to {DEFAULT_ROUTE.title}
        </Button>
      </Stack>
    </Page>
  )
}
