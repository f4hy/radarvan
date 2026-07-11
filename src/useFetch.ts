import * as React from "react"

/**
 * Fetch data whenever `deps` change, guarding against out-of-order responses:
 * a response that resolves after the deps changed (or the component
 * unmounted) is dropped instead of clobbering the newer request's data.
 *
 * Returns null while the current fetch is in flight — data is reset on every
 * deps change, so `data === null` always means "loading" and a resolved empty
 * result stays distinguishable from a pending one. Errors go to `onError`
 * (typically useErrorSnackbar's showError) and leave the data null.
 *
 * `fetcher`/`onError` are intentionally read fresh on each run rather than
 * being deps themselves — callers pass inline closures without useCallback
 * ceremony, and `deps` alone decides when to refetch.
 */
export function useFetch<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList,
  onError: (e: unknown) => void = console.error,
): T | null {
  const [data, setData] = React.useState<T | null>(null)
  React.useEffect(() => {
    let stale = false
    setData(null)
    fetcher().then(
      (d) => {
        if (!stale) setData(d)
      },
      (e) => {
        if (!stale) onError(e)
      },
    )
    return () => {
      stale = true
    }
  }, deps)
  return data
}
