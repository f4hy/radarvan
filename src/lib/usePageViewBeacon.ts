import * as React from "react"
import { useLocation } from "react-router"
import { pageViewApiPageViewPost } from "../api/sdk.gen"

/**
 * Reports each page the visitor enters, so in-app navigation shows up in the
 * traces — a page served from the query cache otherwise makes no request.
 *
 * A view is entering a route (a pathname change). A query-only change — another
 * Game Night, a match highlight, a filter — is not a view, whether the page or
 * the visitor made it: which night or player was looked at is already on every
 * data request as `app.page.query`. The query sent here is the one the page
 * was entered with.
 */
export function usePageViewBeacon() {
  const { pathname, search } = useLocation()
  const lastPath = React.useRef<string | null>(null)
  React.useEffect(() => {
    // "/" only redirects to the default page, which reports itself.
    if (pathname === "/" || pathname === lastPath.current) return
    const referrer = lastPath.current
    lastPath.current = pathname
    pageViewApiPageViewPost({
      body: { path: pathname, query: search.replace(/^\?/, ""), referrer },
    }).catch(() => {
      // Best-effort: a lost beacon must never surface to the visitor.
    })
  }, [pathname, search])
}
