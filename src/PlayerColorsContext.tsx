import * as React from "react"
import { Client } from "./Client"
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
export function PlayerColorsProvider(props: { children: React.ReactNode }) {
  const [colors, setColors] = React.useState<Record<string, string>>({})

  React.useEffect(() => {
    Client.getPlayerColorsApiPlayerColorsGet()
      .then((data) => {
        const clean: Record<string, string> = {}
        for (const [name, color] of Object.entries(data)) {
          if (color) clean[name] = color
        }
        setColors(clean)
      })
      .catch(() => {
        // Swallow - the hash-based fallback covers this.
      })
  }, [])

  return (
    <PlayerColorsContext.Provider value={colors}>
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
