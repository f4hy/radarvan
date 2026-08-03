import { CommentaryApi, DefaultApi, MapApi, Configuration } from "./api"

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

function getConfig(): Configuration {
  // Using a framework-agnostic check for NODE_ENV
  if (import.meta.env.MODE === "development") {
    return new Configuration({
      basePath: "http://localhost:8000",
      headers,
      fetchApi: fetchWithRateLimitRetry,
    })
  }
  // This will be used in production
  return new Configuration({
    basePath: "https://radarvan-5e9c302c60e6.herokuapp.com",
    headers,
    fetchApi: fetchWithRateLimitRetry,
  })
}
const config = getConfig()
export const Client = new DefaultApi(config)
export const CommentaryClient = new CommentaryApi(config)
export const MapClient = new MapApi(config)
