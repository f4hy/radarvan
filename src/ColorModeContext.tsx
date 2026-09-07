import { useColorScheme } from "@mui/material/styles"

export type ColorModePreference = "light" | "dark" | "system"
export type ColorMode = "light" | "dark"

interface ColorModeValue {
  /** The mode actually in effect — what recharts (which can't read MUI's
   * theme/CSS variables) and other non-MUI color logic should read. */
  mode: ColorMode
  /** What the user asked for — "system" tracks the OS setting live. */
  preference: ColorModePreference
  setPreference: (preference: ColorModePreference) => void
}

/**
 * Thin wrapper over MUI's `useColorScheme`, which — because `theme.ts` builds
 * a `cssVariables` theme with both color schemes — is provided directly by
 * `ThemeProvider` in `App.tsx` (no separate context/provider of our own).
 * MUI owns the `prefers-color-scheme` tracking, localStorage persistence, and
 * stamping the `data-color-mode` attribute that `index.css`'s recharts rules
 * and `theme.ts`'s `colorSchemeSelector` both key off of.
 */
export function useColorMode(): ColorModeValue {
  const { mode, colorScheme, setMode } = useColorScheme()
  return {
    mode: colorScheme ?? "light",
    preference: mode ?? "system",
    setPreference: setMode,
  }
}
