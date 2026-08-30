import RefreshIcon from "@mui/icons-material/Refresh"
import Alert from "@mui/material/Alert"
import AlertTitle from "@mui/material/AlertTitle"
import Button from "@mui/material/Button"
import type { UseQueryResult } from "@tanstack/react-query"
import * as React from "react"
import { errorMessage } from "./apiError"
import Loading from "./Loading"

/**
 * The three states of a read, in one place.
 *
 * Pages used to spell this as a convention — `data === null` meant loading —
 * which had no room for "failed" at all. A request that errored left the page
 * in its skeleton forever, and on four pages the early `return <Loading />` sat
 * *above* the JSX that mounted the error snackbar, so the failure was never
 * shown to anyone. Whether a page got that right was per-file.
 *
 * `QueryState` renders the error branch itself, so a call site can't skip it,
 * and hands `children` a non-nullable `data` so the success path doesn't carry
 * null checks that only ever existed to model loading.
 */

/** Reads FastAPI's `detail` off the thrown ResponseError. Async (it reads the
 * response body) and a render isn't, so the status line shows until it lands. */
function useErrorText(error: unknown): string {
  const [text, setText] = React.useState<string | null>(null)
  React.useEffect(() => {
    if (error == null) {
      setText(null)
      return
    }
    let stale = false
    void errorMessage(error).then((m) => !stale && setText(m))
    return () => {
      stale = true
    }
  }, [error])
  return text ?? "Loading the error…"
}

export function ErrorState(props: {
  error: unknown
  onRetry?: () => void
  /** What failed, in the reader's terms — "Player Stats", "this match". */
  what?: string
}) {
  const text = useErrorText(props.error)
  return (
    <Alert
      severity="error"
      action={
        props.onRetry && (
          <Button
            color="inherit"
            size="small"
            startIcon={<RefreshIcon />}
            onClick={props.onRetry}
          >
            Retry
          </Button>
        )
      }
    >
      <AlertTitle>
        {props.what ? `Couldn't load ${props.what}` : "Something went wrong"}
      </AlertTitle>
      {text}
    </Alert>
  )
}

export default function QueryState<T>(props: {
  query: UseQueryResult<T>
  what?: string
  /** Override the skeleton — a list page wants its own shape. */
  loading?: React.ReactNode
  children: (data: T) => React.ReactNode
}) {
  const { query } = props
  if (query.isPending) {
    return <>{props.loading ?? <Loading />}</>
  }
  if (query.isError) {
    return (
      <ErrorState
        error={query.error}
        what={props.what}
        onRetry={() => void query.refetch()}
      />
    )
  }
  // `isPending` and `isError` are both false, so data is loaded. The cast is
  // the one place this is asserted, instead of every call site testing for a
  // null that only ever meant "still loading".
  return <>{props.children(query.data as T)}</>
}

/**
 * The early-return form, for a component whose hooks already depend on the
 * data (`useMemo` over the rows, an effect that seeds state from them).
 *
 * Those hooks have to sit above any conditional return, so the render-prop form
 * can't wrap them. Returns the pending/error element when there is one and null
 * when the data is ready, so a call site reads:
 *
 *     const fallback = queryFallback(query, "map stats")
 *     if (fallback) return fallback
 *     const mapStats = query.data as MapStats
 *
 * Prefer `QueryState` where the hooks don't need the data — it hands back a
 * non-nullable value instead of leaving the assertion to the caller.
 */
export function queryFallback<T>(
  query: UseQueryResult<T>,
  what?: string,
): React.ReactElement | null {
  if (query.isPending) return <Loading />
  if (query.isError) {
    return (
      <ErrorState
        error={query.error}
        what={what}
        onRetry={() => void query.refetch()}
      />
    )
  }
  return null
}
