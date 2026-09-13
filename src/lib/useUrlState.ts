import * as React from "react"
import { useSearchParams } from "react-router"

/**
 * The rule every hook here shares: **a value equal to the default is not
 * written**.
 *
 * Filters that serialised their defaults would leave every visitor's URL
 * carrying `?format=All&minGames=3&significant=false` the moment they touched
 * anything, and the link they then paste says nothing about what they were
 * actually looking at. Omitting the default keeps a shared URL to the parts
 * that differ from what the page shows on its own.
 *
 * The trade is that changing a default later re-points existing links, since
 * they never named the old one. That is the right way round: the alternative is
 * links that pin a value nobody chose.
 */
function withParam(
  params: URLSearchParams,
  key: string,
  value: string | null,
): URLSearchParams {
  const updated = new URLSearchParams(params)
  if (value === null || value === "") {
    updated.delete(key)
  } else {
    updated.set(key, value)
  }
  return updated
}

/**
 * A query parameter as state, with the URL as the only copy.
 *
 * Pages used to hold `useState(playerFromUrl)` and call a `setPlayerInUrl`
 * helper alongside every `setPlayer` — two copies of one fact, seeded from the
 * URL once at mount and never reconciled. That had a visible bug: clicking a
 * player chip while already on Player Profile pushed a new `?player=` and left
 * the component's state on the old name, so the page didn't change. Back and
 * forward had the same problem — the URL moved, the page didn't.
 *
 * Reading straight from `useSearchParams` removes the second copy, so a chip, a
 * pasted link, the picker and the Back button are all the same operation.
 *
 * Setting *pushes* by default: choosing a different player is a navigation, and
 * Back should return to the previous one. Pass `replace` for a control that
 * changes continuously (a slider, a search box) where one history entry per
 * keystroke would trap the visitor on the page.
 */
export function useUrlParam(
  key: string,
  opts: { replace?: boolean } = {},
): [string | null, (value: string | null) => void] {
  const [params, setParams] = useSearchParams()
  const replace = opts.replace ?? false
  const value = params.get(key)

  const setValue = React.useCallback(
    (next: string | null) => {
      setParams((prev) => withParam(prev, key, next), { replace })
    },
    [key, replace, setParams],
  )

  return [value, setValue]
}

/**
 * Read a parameter as one of a fixed set of choices.
 *
 * Anything unrecognised reads as `fallback` rather than reaching the page — a
 * pasted `?format=9v9` would otherwise become an API query parameter, or index
 * an options array and render `undefined`. A URL is attacker-controlled input
 * in the same way a request body is; this is the validation step.
 *
 * Matching is on the string form, so a numeric choice set (`[1, 2, 5]`) works
 * without a second hook and hands back the number, not `"2"`.
 */
export function useUrlChoice<T extends string | number>(
  key: string,
  options: readonly T[],
  fallback: T,
  opts: { replace?: boolean } = {},
): [T, (value: T) => void] {
  const [params, setParams] = useSearchParams()
  const replace = opts.replace ?? false
  const raw = params.get(key)
  const match = options.find((option) => String(option) === raw)
  const value = match ?? fallback

  const setValue = React.useCallback(
    (next: T) => {
      setParams(
        (prev) => withParam(prev, key, next === fallback ? null : String(next)),
        { replace },
      )
    },
    [key, fallback, replace, setParams],
  )

  return [value, setValue]
}

/**
 * Read a parameter as a number, clamped into range.
 *
 * For the controls whose value is a point on a scale rather than one of a
 * listed few — a "minimum games" threshold, a regularisation weight. Clamping
 * rather than rejecting is deliberate: `?minGames=999` from an old link should
 * show the strictest view the control can express, not silently snap back to
 * the default and look like the link was ignored.
 */
export function useUrlNumber(
  key: string,
  fallback: number,
  opts: { replace?: boolean; min?: number; max?: number } = {},
): [number, (value: number) => void] {
  const [params, setParams] = useSearchParams()
  const { replace = false, min, max } = opts
  const raw = params.get(key)
  const parsed = raw === null || raw.trim() === "" ? Number.NaN : Number(raw)
  let value = Number.isFinite(parsed) ? parsed : fallback
  if (min !== undefined) value = Math.max(min, value)
  if (max !== undefined) value = Math.min(max, value)

  const setValue = React.useCallback(
    (next: number) => {
      setParams(
        (prev) => withParam(prev, key, next === fallback ? null : String(next)),
        { replace },
      )
    },
    [key, fallback, replace, setParams],
  )

  return [value, setValue]
}

/**
 * Read a parameter as a checkbox.
 *
 * Present-and-not-`0`/`false` is on, which makes the bare `?significantOnly=1`
 * form work and keeps a hand-edited `?significantOnly=true` working too. The
 * default is `false` for every current caller, so an unchecked box writes
 * nothing at all.
 */
export function useUrlFlag(
  key: string,
  opts: { replace?: boolean } = {},
): [boolean, (value: boolean) => void] {
  const [params, setParams] = useSearchParams()
  const replace = opts.replace ?? false
  const raw = params.get(key)
  const value = raw !== null && raw !== "0" && raw !== "false"

  const setValue = React.useCallback(
    (next: boolean) => {
      setParams((prev) => withParam(prev, key, next ? "1" : null), { replace })
    },
    [key, replace, setParams],
  )

  return [value, setValue]
}

/**
 * Set several parameters at once.
 *
 * Necessary, not a convenience: `setSearchParams` from react-router hands the
 * updater `new URLSearchParams(searchParams)` built from *this render's*
 * `location.search`, and `navigate()` doesn't change that within the tick. So
 * two single-key setters called together both start from the same snapshot and
 * the second silently drops the first — which is exactly what a filter bar
 * writing player, map and format together would do.
 *
 * A key mapped to `null` is removed, matching the single-key hooks. Callers
 * that omit a default still have to do that themselves; this only bundles the
 * writes.
 */
export function useUrlPatch(
  opts: { replace?: boolean } = {},
): (updates: Record<string, string | null>) => void {
  const [, setParams] = useSearchParams()
  const replace = opts.replace ?? false

  return React.useCallback(
    (updates: Record<string, string | null>) => {
      setParams(
        (prev) => {
          let next = prev
          for (const [key, value] of Object.entries(updates)) {
            next = withParam(next, key, value)
          }
          return next
        },
        { replace },
      )
    },
    [replace, setParams],
  )
}

/**
 * Read a parameter as a record id — a positive integer, or absent.
 *
 * The `null` here means "nothing selected", so unlike the hooks above there is
 * no default to omit: absent *is* the default. Anything that isn't a positive
 * integer reads as absent, which keeps `?match=' OR 1=1` from reaching a
 * `/api/details/{id}` path.
 */
export function useUrlId(
  key: string,
  opts: { replace?: boolean } = {},
): [number | null, (value: number | null) => void] {
  const [raw, setRaw] = useUrlParam(key, opts)
  const value = raw !== null && /^[1-9]\d*$/.test(raw) ? Number(raw) : null

  const setValue = React.useCallback(
    (next: number | null) => setRaw(next === null ? null : String(next)),
    [setRaw],
  )

  return [value, setValue]
}
