import { describe, expect, it } from "vitest"
import { BILLED_QUERY_OPTIONS, queryClient, STALE_TIME_MS } from "./queryClient"

describe("BILLED_QUERY_OPTIONS", () => {
  /**
   * `GET /api/matchup_commentary/` and `GET /api/bracket_summary/{id}` generate
   * on a cache miss, and generating bills a real LLM call. Every one of these
   * flags is off for that reason — a default-configured query would happily
   * re-ask on window focus, which is a charge, silently, whenever someone tabs
   * back to a bracket popup they left open.
   *
   * If a future default makes one of these redundant, delete it from the object
   * and this test together, deliberately. Do not loosen one to fix a staleness
   * complaint: stale flavor text is free, a refetch is not.
   */
  it("turns off every automatic refetch", () => {
    expect(BILLED_QUERY_OPTIONS.refetchOnWindowFocus).toBe(false)
    expect(BILLED_QUERY_OPTIONS.refetchOnMount).toBe(false)
    expect(BILLED_QUERY_OPTIONS.refetchOnReconnect).toBe(false)
  })

  it("never retries, so a failure can't bill a second attempt", () => {
    expect(BILLED_QUERY_OPTIONS.retry).toBe(false)
  })

  it("never goes stale, so nothing revalidates it", () => {
    expect(BILLED_QUERY_OPTIONS.staleTime).toBe(Number.POSITIVE_INFINITY)
    expect(BILLED_QUERY_OPTIONS.gcTime).toBe(Number.POSITIVE_INFINITY)
  })
})

describe("query client defaults", () => {
  it("matches the backend's own 60s corpus poll", () => {
    // Not a taste call: `@derived(on=CORPUS)` revalidates its token on a 60s DB
    // poll, so an answer younger than that is one the server would have
    // recomputed from identical inputs.
    expect(STALE_TIME_MS).toBe(60_000)
    expect(queryClient.getDefaultOptions().queries?.staleTime).toBe(60_000)
  })

  it("retries a read once, and a mutation never", () => {
    // A write is not safe to replay on the client's own initiative.
    expect(queryClient.getDefaultOptions().queries?.retry).toBe(1)
    expect(queryClient.getDefaultOptions().mutations?.retry).toBe(0)
  })
})
