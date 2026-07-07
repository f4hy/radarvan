import * as React from "react"
import { Client } from "./Client"
import { getColorHex, playerColor } from "./utils"

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

/** A single primary identity color for a player: their actual most-common
 * in-game color when known, else the deterministic hash-per-name fallback.
 * For anything that just needs one accent color (borders, chart markers);
 * PlayerChip's avatar additionally rings this with the hash when it differs,
 * so a shared "actual" color doesn't make two players look identical. */
export function usePlayerAccentColor(name: string): string {
  const actual = usePlayerColors()[name]
  return actual != null ? getColorHex(actual) : playerColor(name)
}
