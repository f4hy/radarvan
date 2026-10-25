import type { CreateClientConfig } from "../api/client.gen"
import { readApiError } from "./apiError"

const apiKey = import.meta.env.VITE_API_KEY as string | undefined
const headers: Record<string, string> = { "X-Client-Id": "react-frontend" }
if (apiKey) {
  headers["X-API-Key"] = apiKey
}

// A random id per browser, for counting distinct visitors in the traces
// (request_tags.py). Generated here rather than by the server so the
// concurrent requests of a first page load all carry the same one.
const VISITOR_STORAGE_KEY = "radarvan-visitor-id"
const visitorId: string | null = (() => {
  try {
    const stored = localStorage.getItem(VISITOR_STORAGE_KEY)
    if (stored) return stored
    const minted = crypto.randomUUID()
    localStorage.setItem(VISITOR_STORAGE_KEY, minted)
    return minted
  } catch {
    // Storage blocked (private mode, disabled site data): stay anonymous.
    return null
  }
})()

// How many times to transparently retry a 429 before giving up and letting the
// ApiError propagate to the caller's error handling.
const MAX_RATE_LIMIT_RETRIES = 3
const MAX_WAIT_MS = 30_000

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

// fetch wrapper that handles 429 (Too Many Requests) from the rate limiter:
// wait for the server-advertised Retry-After (which already carries jitter),
// falling back to exponential backoff if the header is missing/unreadable, then
// retry. After MAX_RATE_LIMIT_RETRIES it returns the 429 like any other failure.
async function fetchWithRateLimitRetry(request: Request): Promise<Response> {
  for (let attempt = 0; ; attempt++) {
    // Clone: a Request body can only be read once, and a retry resends it.
    const response = await fetch(request.clone())
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

// The generated client throws the parsed error *body* on a non-2xx, which loses
// the status. Throwing here instead means every failure reaches callers as an
// ApiError carrying both the status and FastAPI's rendered `detail`.
async function apiFetch(
  input: RequestInfo | URL,
  init?: RequestInit,
): Promise<Response> {
  const request = new Request(input, init)
  // Tags the server's trace with the page that asked (request_tags.py), so
  // usage can be read per page rather than only per endpoint.
  request.headers.set(
    "X-Radarvan-Page",
    window.location.pathname + window.location.search,
  )
  if (visitorId) request.headers.set("X-Radarvan-Visitor", visitorId)
  const response = await fetchWithRateLimitRetry(request)
  if (!response.ok) throw await readApiError(response)
  return response
}

/**
 * The generated client's initial config — `openapi-ts.config.mjs` points
 * `runtimeConfigPath` here, so there is no `setConfig()` call to forget.
 *
 * `baseUrl: ""` keeps every request relative (generated paths already start
 * with `/api`), which is what lets the session cookie ride along: in dev the
 * Vite proxy forwards `/api`, and in prod one FastAPI process serves both
 * `dist/` and `/api`. An absolute base URL makes dev cross-origin and the
 * cookie unsendable — that is how the app once grew a parallel hand-written
 * fetch layer. Keep it relative.
 *
 * Sending `X-API-Key` on the cookie-session routes is harmless — they don't
 * declare the key as a security scheme, and `_require_logged_in_admin` treats a
 * normal-tier key as "not an admin key" and falls through to the cookie check.
 */
export const createClientConfig: CreateClientConfig = (config) => ({
  ...config,
  baseUrl: "",
  headers,
  credentials: "same-origin",
  fetch: apiFetch,
  throwOnError: true,
})
