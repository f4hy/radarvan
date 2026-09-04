import * as React from "react"

export type ColorModePreference = "light" | "dark" | "system"
export type ColorMode = "light" | "dark"

const STORAGE_KEY = "radarvan-color-mode"

function readStoredPreference(): ColorModePreference {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === "light" || raw === "dark" || raw === "system") return raw
  } catch {
    // Storage can throw in a private-browsing context; fall through.
  }
  return "system"
}

function systemPrefersDark(): boolean {
  return (
    typeof window !== "undefined" &&
    window.matchMedia?.("(prefers-color-scheme: dark)").matches === true
  )
}

interface ColorModeContextValue {
  /** The mode actually in effect — what the theme and charts should read. */
  mode: ColorMode
  /** What the user asked for — "system" tracks the OS setting live. */
  preference: ColorModePreference
  setPreference: (preference: ColorModePreference) => void
}

const ColorModeContext = React.createContext<ColorModeContextValue | null>(null)

/**
 * Owns the light/dark/system preference (persisted in localStorage) and
 * resolves it to the effective mode, tracking the OS setting live while on
 * "system". Also stamps `data-color-mode` on the root element so plain CSS
 * (recharts' SVG text/lines, which can't read the MUI theme) can react to it
 * too — see the `[data-color-mode="dark"]` rules in index.css.
 */
export function ColorModeProvider(props: { children: React.ReactNode }) {
  const [preference, setPreferenceState] =
    React.useState<ColorModePreference>(readStoredPreference)
  const [systemDark, setSystemDark] = React.useState(systemPrefersDark)

  React.useEffect(() => {
    const mql = window.matchMedia("(prefers-color-scheme: dark)")
    const onChange = () => setSystemDark(mql.matches)
    mql.addEventListener("change", onChange)
    return () => mql.removeEventListener("change", onChange)
  }, [])

  const mode: ColorMode =
    preference === "system" ? (systemDark ? "dark" : "light") : preference

  React.useEffect(() => {
    document.documentElement.dataset.colorMode = mode
  }, [mode])

  const setPreference = React.useCallback((next: ColorModePreference) => {
    setPreferenceState(next)
    try {
      localStorage.setItem(STORAGE_KEY, next)
    } catch {
      // Best-effort — the preference just won't survive a reload.
    }
  }, [])

  const value = React.useMemo(
    () => ({ mode, preference, setPreference }),
    [mode, preference, setPreference],
  )

  return (
    <ColorModeContext.Provider value={value}>
      {props.children}
    </ColorModeContext.Provider>
  )
}

export function useColorMode(): ColorModeContextValue {
  const ctx = React.useContext(ColorModeContext)
  if (!ctx) {
    throw new Error("useColorMode must be used within a ColorModeProvider")
  }
  return ctx
}
