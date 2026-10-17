/**
 * What every failed API call throws (`apiConfig.apiFetch` raises it on any
 * non-2xx), with FastAPI's `{"detail": ...}` already rendered into `message`.
 *
 * `detail` is a string for a raised HTTPException (the 409 vote-limit message,
 * "Admin API key required", …) and a list of error objects for a request that
 * failed validation; both are rendered rather than one falling back to the
 * status line.
 */
export class ApiError extends Error {
  readonly status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = "ApiError"
    this.status = status
  }
}

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

export async function readApiError(resp: Response): Promise<ApiError> {
  try {
    // Clone: a caller that catches this may still want to read the body.
    const body = (await resp.clone().json()) as { detail?: unknown }
    const detail = renderDetail(body?.detail)
    if (detail) return new ApiError(resp.status, detail)
  } catch {
    // Non-JSON error body (a proxy 502, an HTML error page) — fall through to
    // the status line, which at least says what happened.
  }
  return new ApiError(resp.status, `Request failed (${resp.status})`)
}

export function errorMessage(e: unknown): string {
  if (e instanceof Error) return e.message
  return String(e)
}
