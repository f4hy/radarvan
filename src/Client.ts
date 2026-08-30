import {
  AuthApi,
  BracketApi,
  CommentaryApi,
  DefaultApi,
  GameNightApi,
  MapApi,
  MapVoteApi,
  Configuration,
} from "./api"

const apiKey = import.meta.env.VITE_API_KEY as string | undefined
const headers: Record<string, string> = { "X-Client-Id": "react-frontend" }
if (apiKey) {
  headers["X-API-Key"] = apiKey
}

// How many times to transparently retry a 429 before giving up and letting the
// ResponseError propagate to the caller's error handling.
const MAX_RATE_LIMIT_RETRIES = 3
const MAX_WAIT_MS = 30_000

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// fetch wrapper that handles 429 (Too Many Requests) from the rate limiter:
// wait for the server-advertised Retry-After (which already carries jitter),
// falling back to exponential backoff if the header is missing/unreadable, then
// retry. After MAX_RATE_LIMIT_RETRIES it returns the 429 so the generated
// client throws as usual and the UI's error handling can surface it.
async function fetchWithRateLimitRetry(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  for (let attempt = 0; ; attempt++) {
    const response = await fetch(input, init)
    if (response.status !== 429 || attempt >= MAX_RATE_LIMIT_RETRIES) {
      return response
    }
    const retryAfter = Number(response.headers.get("Retry-After"))
    const waitMs =
      Number.isFinite(retryAfter) && retryAfter > 0
        ? retryAfter * 1000
        : 2 ** attempt * 1000
    await delay(Math.min(waitMs, MAX_WAIT_MS))
  }
}

/**
 * One client, same-origin, for every route — API-key and cookie-session alike.
 *
 * `basePath: ""` makes every generated path relative (they already start with
 * `/api`), which is what lets the signed session cookie ride along: in dev the
 * Vite proxy forwards `/api` to the backend, and in prod one FastAPI process
 * serves both `dist/` and `/api` (`main.py`'s CachedStaticFiles mount), so the
 * request is genuinely same-origin in both.
 *
 * It used to be an absolute URL (localhost:8000 in dev, the Heroku host in
 * prod). That made every request cross-origin in dev, so the cookie was never
 * sent — which is why auth, voting, map upload and the bracket each grew a
 * parallel hand-written `fetch` module *and a hand-written copy of the response
 * types*, in snake_case, that nothing checked against the backend. Keep this
 * relative: an absolute base path brings all of that back.
 *
 * Sending `X-API-Key` on the cookie-session routes is harmless — they don't
 * declare the key as a security scheme, and `_require_logged_in_admin` treats a
 * normal-tier key as "not an admin key" and falls through to the cookie check.
 */
const apiConfig = new Configuration({
  basePath: "",
  headers,
  credentials: "same-origin",
  fetchApi: fetchWithRateLimitRetry,
})

// Every client shares that one config. Splitting the lazy-page-only ones into
// their own modules was tried and measured at a 61-byte difference in the
// initial payload — rolldown already tree-shakes this module per importer — so
// they stay here, where there is one place to look for a client.
export const Client = new DefaultApi(apiConfig)
export const AuthClient = new AuthApi(apiConfig)
export const BracketClient = new BracketApi(apiConfig)
export const CommentaryClient = new CommentaryApi(apiConfig)
export const GameNightClient = new GameNightApi(apiConfig)
export const MapClient = new MapApi(apiConfig)
export const MapVoteClient = new MapVoteApi(apiConfig)
