import * as React from "react"
import { useLocation, useNavigationType } from "react-router"
import { pageViewApiPageViewPost } from "../api/sdk.gen"

/**
 * Reports each page the visitor lands on, so in-app navigation shows up in the
 * traces — a page served from the query cache otherwise makes no request.
 *
 * A REPLACE on the same path is a page writing its own default into the URL
 * (Game Night landing on the latest night), not a new view.
 */
export function usePageViewBeacon() {
  const { pathname, search } = useLocation()
  const navigationType = useNavigationType()
  const last = React.useRef<string | null>(null)
  React.useEffect(() => {
    // "/" only redirects to the default page, which reports itself.
    if (pathname === "/") return
    const previous = last.current
    const previousPath = previous?.split("?")[0]
    const key = pathname + search
    if (key === previous) return
    last.current = key
    if (navigationType === "REPLACE" && previousPath === pathname) return
    pageViewApiPageViewPost({
      body: {
        path: pathname,
        query: search.replace(/^\?/, ""),
        referrer: previousPath ?? null,
      },
    }).catch(() => {
      // Best-effort: a lost beacon must never surface to the visitor.
    })
  }, [pathname, search, navigationType])
}
