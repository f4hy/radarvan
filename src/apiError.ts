import { ResponseError } from "./api"

/**
 * Turn anything thrown by the generated client into a message worth showing.
 *
 * The generated runtime throws `ResponseError` with the fixed text "Response
 * returned an error code" and hands the raw `Response` along, so every failure
 * on a generated call used to reach the snackbar as that one useless sentence.
 * The hand-written same-origin modules each pulled FastAPI's `{"detail": ...}`
 * out of the body themselves — that is the part worth keeping from them, so it
 * lives here once instead of five times.
 *
 * `detail` is a string for a raised HTTPException (the 409 vote-limit message,
 * "Admin API key required", …) and a list of error objects for a request that
 * failed validation; both are rendered rather than one falling back to the
 * status line.
 */
type ValidationIssue = { msg?: string; loc?: (string | number)[] }

function renderDetail(detail: unknown): string | null {
  if (typeof detail === "string" && detail) return detail
  if (Array.isArray(detail)) {
    const parts = (detail as ValidationIssue[])
      .map((issue) => {
        if (typeof issue?.msg !== "string") return null
        // `loc` is ["body", "player_name"] — the field is the last hop, and
        // naming it is what makes a bare "field required" actionable.
        const field = issue.loc?.at(-1)
        return field != null ? `${String(field)}: ${issue.msg}` : issue.msg
      })
      .filter((part): part is string => part !== null)
    if (parts.length > 0) return parts.join("; ")
  }
  return null
}

/** The message for a failed `Response`, for the one caller that builds its own
 * request (`mapUpload.ts`, which the generator can't express). */
export async function responseErrorMessage(resp: Response): Promise<string> {
  try {
    // Clone: a caller that catches this may still want to read the body.
    const body = (await resp.clone().json()) as { detail?: unknown }
    const detail = renderDetail(body?.detail)
    if (detail) return detail
  } catch {
    // Non-JSON error body (a proxy 502, an HTML error page) — fall through to
    // the status line, which at least says what happened.
  }
  return `Request failed (${resp.status})`
}

export async function errorMessage(e: unknown): Promise<string> {
  if (e instanceof ResponseError) return responseErrorMessage(e.response)
  if (e instanceof Error) return e.message
  return String(e)
}
