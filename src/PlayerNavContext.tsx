import * as React from "react"

/**
 * Cross-page navigation to a player, available to any component that renders a
 * player's name.
 *
 * `Menu` owns the routing (it holds the `Selection` state and the `?page=` URL
 * writing), so previously the only way to reach a profile from a card was for
 * Menu to thread `goToPlayerProfile` down as a prop — which it did for exactly
 * one page, `Bracket`. Everywhere else a player's name was a dead end: the
 * "Nemesis" card on a profile named an opponent it couldn't link to, and the
 * Game Night standings couldn't reach anyone's profile.
 *
 * Same pattern as PlayerColorsContext (and BracketDataContext), for the same
 * reason: a cross-cutting concern every leaf needs shouldn't be prop-drilled.
 */

export interface PlayerNav {
  goToPlayerProfile: (playerName: string) => void
  goToHeadToHead: (player1: string, player2: string) => void
}

// A no-op default rather than null, so a component rendered outside the
// provider (a test, a Storybook-style harness) still renders — it just doesn't
// navigate. `enabled` is what callers check before showing a link affordance.
const NO_NAV: PlayerNav = {
  goToPlayerProfile: () => {},
  goToHeadToHead: () => {},
}

const PlayerNavContext = React.createContext<PlayerNav | null>(null)

export function PlayerNavProvider(props: {
  value: PlayerNav
  children: React.ReactNode
}) {
  return (
    <PlayerNavContext.Provider value={props.value}>
      {props.children}
    </PlayerNavContext.Provider>
  )
}

export function usePlayerNav(): PlayerNav & { enabled: boolean } {
  const nav = React.useContext(PlayerNavContext)
  return { ...(nav ?? NO_NAV), enabled: nav !== null }
}
