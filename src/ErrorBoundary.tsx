import RefreshIcon from "@mui/icons-material/Refresh"
import Alert from "@mui/material/Alert"
import AlertTitle from "@mui/material/AlertTitle"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import * as React from "react"

/**
 * The backstop for a render-time throw.
 *
 * There was none: any exception while rendering unmounted the whole React tree
 * and left a blank white page, with the nav gone too — a single bad field on
 * one card took out the app. `QueryState` handles a *failed request*; this
 * handles the bugs, which is a different job and needs a class component
 * because that is still the only way to catch a render error.
 *
 * One wraps the routed page (keyed on the path in `Menu`, so navigating away
 * clears a caught error rather than pinning it), and one wraps the whole app so
 * a throw in the shell itself still says something.
 */

interface Props {
  children: React.ReactNode
  /** Shown above the message — "this page" for a route, omitted for the root. */
  what?: string
  /** Rendered instead of the default panel, for the root boundary where MUI's
   * ThemeProvider may itself be the thing that failed. */
  fallback?: (error: Error, reset: () => void) => React.ReactNode
}

interface State {
  error: Error | null
}

export default class ErrorBoundary extends React.Component<Props, State> {
  override state: State = { error: null }

  static getDerivedStateFromError(error: Error): State {
    return { error }
  }

  override componentDidCatch(error: Error, info: React.ErrorInfo) {
    // Nothing ships errors off the client today, so the console is the only
    // record — log both halves, since the component stack is what actually
    // names the culprit.
    console.error("Unhandled render error", error, info.componentStack)
  }

  reset = () => this.setState({ error: null })

  override render() {
    const { error } = this.state
    if (error === null) return this.props.children
    if (this.props.fallback) return this.props.fallback(error, this.reset)
    return (
      <Box sx={{ maxWidth: 720 }}>
        <Alert
          severity="error"
          action={
            <Button
              color="inherit"
              size="small"
              startIcon={<RefreshIcon />}
              onClick={this.reset}
            >
              Try again
            </Button>
          }
        >
          <AlertTitle>
            {this.props.what
              ? `Something went wrong in ${this.props.what}`
              : "Something went wrong"}
          </AlertTitle>
          <Stack spacing={1}>
            <Typography variant="body2">
              This is a bug, not something you did. The rest of the app still
              works — pick another page from the sidebar.
            </Typography>
            <Typography
              variant="caption"
              component="pre"
              sx={{
                color: "text.secondary",
                whiteSpace: "pre-wrap",
                wordBreak: "break-word",
                m: 0,
              }}
            >
              {error.message}
            </Typography>
          </Stack>
        </Alert>
      </Box>
    )
  }
}
