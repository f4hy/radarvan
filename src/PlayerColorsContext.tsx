import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import { PlayersClient } from "./clients/players"
import {
  getColorHex,
  type PlayerPalette,
  playerColor,
  playerPalette,
} from "./utils"

const PlayerColorsContext = React.createContext<Record<string, string>>({})

/** Fetches each player's most-common actual in-game color once at app
 * startup. Best-effort: PlayerChip falls back to its hash-based color for
 * any name missing here (not yet loaded, request failed, or not enough
 * games to have a "usual" color). */
const NO_COLORS: Record<string, string> = {}

export function PlayerColorsProvider(props: { children: React.ReactNode }) {
  // Best-effort, and it stays that way: a failure resolves to the empty map and
  // PlayerChip falls back to its hash-based color, so no retry and no error
  // surface. Colors only change when someone plays a new one, so this is held
  // for the session rather than revalidated.
  const { data } = useQuery({
    queryKey: ["playerColors"],
    queryFn: async () => {
      const raw = await PlayersClient.getPlayerColorsApiPlayerColorsGet()
      const clean: Record<string, string> = {}
      for (const [name, color] of Object.entries(raw)) {
        if (color) clean[name] = color
      }
      return clean
    },
    staleTime: Number.POSITIVE_INFINITY,
    retry: false,
  })

  return (
    <PlayerColorsContext.Provider value={data ?? NO_COLORS}>
      {props.children}
    </PlayerColorsContext.Provider>
  )
}

export function usePlayerColors(): Record<string, string> {
  return React.useContext(PlayerColorsContext)
}

/** A player's raw identity color: their actual most-common in-game color when
 * known, else the deterministic hash-per-name fallback.
 *
 * This is the *unmodified* game hue, so it is only safe for swatches, borders
 * and chart markers. Anything drawing text wants `usePlayerPalette().ink` —
 * `#FFFF00` and `#BFFF00` are real player colors and neither is readable on
 * white. */
export function usePlayerAccentColor(name: string): string {
  const actual = usePlayerColors()[name]
  return actual != null ? getColorHex(actual) : playerColor(name)
}

/** The usable form of a player's color: a swatch (`dot`), a readable text
 * color (`ink`), and the wash/border derived from the same hue. Lives here
 * beside the raw hook so a call site picks between them deliberately. */
export function usePlayerPalette(name: string): PlayerPalette {
  return playerPalette(usePlayerAccentColor(name))
}
