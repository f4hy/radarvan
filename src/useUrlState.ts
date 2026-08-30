import * as React from "react"
import { useSearchParams } from "react-router"

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
      setParams(
        (prev) => {
          // Build from `prev` rather than the render's snapshot so setting two
          // params in one tick doesn't drop the first.
          const updated = new URLSearchParams(prev)
          if (next === null || next === "") {
            updated.delete(key)
          } else {
            updated.set(key, next)
          }
          return updated
        },
        { replace },
      )
    },
    [key, replace, setParams],
  )

  return [value, setValue]
}
