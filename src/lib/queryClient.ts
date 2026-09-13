import { QueryClient } from "@tanstack/react-query"
import { errorMessage } from "./apiError"

/**
 * One cache for every read in the app.
 *
 * Before this, each page fetched in its own `useEffect` and threw the result
 * away on unmount — and because the router unmounts a page on every navigation,
 * going Matches → Player Stats → Matches was three round trips for data that
 * had not changed. Nothing deduplicated two components asking for the same
 * endpoint, nothing retried, and nothing cancelled.
 *
 * `staleTime` is 60s to match the backend, not by taste: `@derived(on=CORPUS)`
 * revalidates its corpus token on a 60s DB poll, so an answer younger than that
 * is one the server would have recomputed from the same inputs anyway. Asking
 * again inside that window can't produce a different number.
 *
 * `gcTime` is 10 minutes — long enough that a browsing loop (profile → head to
 * head → back) stays instant, short enough that a 512 MB-era page doesn't hold
 * every stats payload it has ever seen.
 */
export const STALE_TIME_MS = 60_000

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: STALE_TIME_MS,
      gcTime: 10 * 60_000,
      // A stats page is not worth three attempts: one retry covers a dropped
      // connection, and anything past that is the server actually being down,
      // which the error state should say rather than hide behind a spinner.
      retry: 1,
      // The rate limiter is handled in Client.ts (it waits out Retry-After and
      // replays), so a 429 never reaches here as an error.
      refetchOnWindowFocus: true,
    },
    mutations: {
      retry: 0,
    },
  },
})

/**
 * Options for an endpoint where a cache *miss* costs real money.
 *
 * `GET /api/matchup_commentary/` and `GET /api/bracket_summary/{id}` generate on
 * a miss, billing an LLM call against whichever provider COMMENTARY_PROVIDER
 * selects (see the root CLAUDE.md). Every automatic refetch the query client
 * would otherwise do — on window focus, on remount, on reconnect, on retry — is
 * a chance to bill another one, so all of them are off and the answer is held
 * for the life of the session.
 *
 * Spread this rather than re-listing the options: the point is that one place
 * decides, and `queryClient.test.ts` checks it.
 */
export const BILLED_QUERY_OPTIONS = {
  staleTime: Number.POSITIVE_INFINITY,
  gcTime: Number.POSITIVE_INFINITY,
  refetchOnWindowFocus: false,
  refetchOnMount: false,
  refetchOnReconnect: false,
  retry: false,
} as const

/**
 * A query's error, as something worth showing a person.
 *
 * The generated runtime throws `ResponseError` carrying the raw `Response`, so
 * FastAPI's `detail` needs reading off the body — which is async, and a render
 * is not. Components render `useQueryErrorMessage(error)` instead, which
 * resolves it and falls back to the status line until it does.
 */
export { errorMessage }
