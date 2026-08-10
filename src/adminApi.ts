// Admin actions driven from the UI. Same-origin fetch so the session cookie
// authenticates the caller: the server gates these on a logged-in admin
// (dependencies=ADMIN_LOGIN), not on an API key. The generated client can't be
// used here - it points at an absolute base URL, which is cross-origin in dev
// and so never sends the cookie.

import { MatchInfo } from "./api"

export async function reparseMatch(matchId: number): Promise<MatchInfo | null> {
  const resp = await fetch(`/api/reparse/${matchId}`, {
    method: "POST",
    credentials: "same-origin",
  })
  if (!resp.ok) {
    let detail = `Reparse failed (${resp.status})`
    try {
      const body = (await resp.json()) as { detail?: string }
      if (body?.detail) detail = body.detail
    } catch {
      // non-JSON error body; keep the generic message
    }
    throw new Error(detail)
  }
  return (await resp.json()) as MatchInfo | null
}
