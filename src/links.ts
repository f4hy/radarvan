import { useNavigate } from "react-router"
import * as React from "react"

/**
 * Where a player's name points.
 *
 * These are hrefs rather than click handlers on purpose: a `PlayerChip` built
 * on `<Link to={playerProfileHref(name)}>` is a real `<a href>`, so ⌘-click
 * opens the profile in a new tab, middle-click works, "copy link address"
 * yields something pasteable into Discord, and the browser shows the target in
 * the status bar. A `<button onClick>` — which is what these were before the
 * router — offers none of that, however correct its semantics.
 *
 * Building the query with URLSearchParams rather than a template string is what
 * keeps a name like "pc | purple" from truncating the URL at the pipe.
 */

export function playerProfileHref(playerName: string): string {
  return `/player-profile?${new URLSearchParams({ player: playerName })}`
}

export function headToHeadHref(player1: string, player2: string): string {
  return `/head-to-head?${new URLSearchParams({ player1, player2 })}`
}

/** One evening's recap. The link Matches puts on every night row, and the one
 * people paste into chat. */
export function gameNightHref(date: string): string {
  return `/game-night?${new URLSearchParams({ date })}`
}

/**
 * The imperative form, for the few places that navigate from something that
 * isn't a link (a chart segment, a dialog action).
 *
 * This replaces `PlayerNavContext`, which existed only because `Menu` owned the
 * routing state and a leaf had no other way to reach it. `useNavigate` works
 * anywhere under the router, so the context had nothing left to carry.
 */
export function usePlayerNav() {
  const navigate = useNavigate()
  return React.useMemo(
    () => ({
      goToPlayerProfile: (playerName: string) =>
        navigate(playerProfileHref(playerName)),
      goToHeadToHead: (player1: string, player2: string) =>
        navigate(headToHeadHref(player1, player2)),
    }),
    [navigate],
  )
}
