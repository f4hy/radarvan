// Admin actions driven from the UI. Same-origin fetch so the session cookie
// authenticates the caller: the server gates these on a logged-in admin
// (dependencies=ADMIN_LOGIN for the reparse button, OPS_ADMIN for everything
// the Admin panel runs), not on an API key. The generated client can't be used
// here — it points at an absolute base URL, which is cross-origin in dev and so
// never sends the cookie.

import { MatchInfo } from "./api"

export type AdminMethod = "POST" | "DELETE"

// A query value of undefined or "" is dropped rather than sent as empty: the
// handlers default their optional params, and `?winner=` would fail validation
// rather than mean "unset".
export type QueryValues = Record<string, string | number | undefined>

function buildUrl(path: string, query?: QueryValues): string {
  if (!query) return path
  const params = new URLSearchParams()
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === "") continue
    params.set(key, String(value))
  }
  const qs = params.toString()
  return qs ? `${path}?${qs}` : path
}

async function errorFrom(resp: Response, fallback: string): Promise<Error> {
  let detail = `${fallback} (${resp.status})`
  try {
    const body = (await resp.json()) as { detail?: string }
    if (body?.detail) detail = body.detail
  } catch {
    // non-JSON error body; keep the generic message
  }
  return new Error(detail)
}

// Run one admin task. Returns the parsed JSON body, or null for an empty one.
// `label` only names the task in the fallback error message, for the case where
// the server sends no `detail` (e.g. a proxy 502).
export async function adminRequest<T>(
  path: string,
  method: AdminMethod = "POST",
  query?: QueryValues,
  label = "Request",
): Promise<T | null> {
  const resp = await fetch(buildUrl(path, query), {
    method,
    credentials: "same-origin",
  })
  if (!resp.ok) {
    throw await errorFrom(resp, `${label} failed`)
  }
  const text = await resp.text()
  return text ? (JSON.parse(text) as T) : null
}

export async function reparseMatch(matchId: number): Promise<MatchInfo | null> {
  return adminRequest<MatchInfo>(
    `/api/reparse/${matchId}`,
    "POST",
    undefined,
    "Reparse",
  )
}
