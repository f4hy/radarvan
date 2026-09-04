import { createTheme, responsiveFontSizes } from "@mui/material/styles"
import type { PaletteMode } from "@mui/material"

/**
 * Central design tokens for the whole app — light AND dark.
 *
 * Surface hierarchy: a cool canvas (`background.default`) with cards floating
 * on it, plus a neutral dark-slate top bar (never blue, in either mode) so
 * the blue stays reserved for interactive elements.
 *
 * Two color rules keep things consistent:
 *  1. Blue means "interactive" only (links, primary buttons, selected state).
 *  2. Win is green, loss is red — for single indicators (pills, dots, deltas).
 *     Import the constants below instead of hand-picking hexes so recharts
 *     (which can't read the MUI theme) stays in sync with MUI.
 *
 * The result/brand/chart hexes are mode-independent by design — they were
 * picked at a middle lightness specifically so the same value reads clearly
 * against both a light and a dark canvas; only the *surfaces* (backgrounds,
 * borders, ink) swap per mode.
 */

// Semantic result colors — the single source of truth for win/loss.
// Muted, slightly desaturated tones so single indicators (pills, dots, deltas)
// read as "calm green / calm red" rather than vivid primaries.
export const WIN_COLOR = "#4a9d6e" // muted green: a win
export const LOSS_COLOR = "#cb6565" // muted red: a loss
export const WIN_COLOR_SOFT = "#9bccb1"
export const LOSS_COLOR_SOFT = "#e0a6a6"
export const NEUTRAL_COLOR = "#9aa4b2"

// Paired win/loss COUNT bars (general/player stats): wins are the hero color,
// losses are a neutral slate so the two adjacent full-height bars don't read as
// garish green+red. Grey-for-loss is safe here because observers never appear
// in these charts — in match cards (where observers ARE grey) losses stay red.
export const CHART_WIN = WIN_COLOR
export const CHART_LOSS = "#9aa4b2"

// Brand / chart accent (the "interactive" blue, used for non-result series).
export const BRAND_COLOR = "#2f6df0"

// Ordered palette for multi-series charts that aren't win/loss.
export const CHART_PALETTE = [
  BRAND_COLOR,
  "#7c4dff",
  "#00897b",
  "#f5a623",
  "#e0457b",
  "#3949ab",
]

// Page ink and hairline borders for LIGHT mode. Exported because non-MUI code
// needs them too (utils.playerPalette derives player chips from INK; recharts
// can't read the theme) — the alternative is re-spelling `rgba(26, 34, 48, …)`
// per call site. `INK_DARK` is the dark-mode equivalent for the same call
// sites (a light ink on a dark canvas).
export const INK = "#1a2230"
export const INK_DARK = "#e7ebf2"
export const BORDER_COLOR = "rgba(26, 34, 48, 0.10)"
export const BORDER_COLOR_DARK = "rgba(231, 235, 242, 0.12)"

// App chrome — deliberately the same dark slate in both modes.
const APPBAR_BG = "#1f2733"

const FONT_STACK = [
  "-apple-system",
  "BlinkMacSystemFont",
  "Segoe UI",
  "Roboto",
  "Helvetica Neue",
  "Arial",
  "sans-serif",
].join(",")

interface SurfaceTokens {
  pageBg: string
  paperBg: string
  border: string
  ink: string
  inkSecondary: string
  hairline: string
  selectedTint: string
  selectedTintStrong: string
}

const LIGHT_SURFACES: SurfaceTokens = {
  // Deepened a touch from near-white so white cards read as distinct surfaces
  // floating on the canvas rather than blending into it.
  pageBg: "#e9ecf1",
  paperBg: "#ffffff",
  border: BORDER_COLOR,
  ink: INK,
  inkSecondary: "#5b6675",
  hairline: "rgba(26, 34, 48, 0.08)",
  selectedTint: "rgba(47, 109, 240, 0.12)",
  selectedTintStrong: "rgba(47, 109, 240, 0.18)",
}

const DARK_SURFACES: SurfaceTokens = {
  // A cool near-black canvas with a slightly lighter paper, mirroring the
  // light theme's "canvas vs. floating card" hierarchy rather than flipping
  // straight to pure black-on-white.
  pageBg: "#10141b",
  paperBg: "#1a212c",
  border: BORDER_COLOR_DARK,
  ink: INK_DARK,
  inkSecondary: "#a7b1c2",
  hairline: "rgba(231, 235, 242, 0.10)",
  selectedTint: "rgba(47, 109, 240, 0.20)",
  selectedTintStrong: "rgba(47, 109, 240, 0.28)",
}

export function buildTheme(mode: PaletteMode) {
  const s = mode === "dark" ? DARK_SURFACES : LIGHT_SURFACES

  let theme = createTheme({
    palette: {
      mode,
      primary: { main: BRAND_COLOR },
      success: { main: WIN_COLOR },
      error: { main: LOSS_COLOR },
      background: {
        default: s.pageBg,
        paper: s.paperBg,
      },
      text: {
        primary: s.ink,
        secondary: s.inkSecondary,
      },
      divider: s.border,
    },
    shape: { borderRadius: 10 },
    typography: {
      fontFamily: FONT_STACK,
      h4: { fontWeight: 700, letterSpacing: "-0.01em" },
      h5: { fontWeight: 700, letterSpacing: "-0.01em" },
      h6: { fontWeight: 700 },
      subtitle1: { fontWeight: 600 },
      subtitle2: { fontWeight: 600 },
      button: { textTransform: "none", fontWeight: 600 },
    },
    components: {
      MuiAppBar: {
        defaultProps: { elevation: 0 },
        styleOverrides: {
          root: {
            backgroundColor: APPBAR_BG,
            backgroundImage: "none",
            borderBottom: "1px solid rgba(255,255,255,0.06)",
          },
        },
      },
      MuiPaper: {
        styleOverrides: {
          outlined: { borderColor: s.border },
          // Softer, lower shadows than MUI defaults for a flatter, modern feel.
          elevation1: {
            boxShadow:
              mode === "dark"
                ? "0 1px 2px rgba(0, 0, 0, 0.4)"
                : "0 1px 2px rgba(16, 24, 40, 0.06)",
            border: `1px solid ${s.hairline}`,
          },
        },
      },
      MuiCard: {
        defaultProps: { variant: "outlined" },
        styleOverrides: {
          root: { borderColor: s.border },
        },
      },
      MuiButton: {
        defaultProps: { disableElevation: true },
        styleOverrides: {
          root: { borderRadius: 8 },
        },
      },
      MuiToggleButton: {
        styleOverrides: {
          root: {
            textTransform: "none",
            fontWeight: 600,
            borderColor:
              mode === "dark"
                ? "rgba(231, 235, 242, 0.20)"
                : "rgba(26, 34, 48, 0.16)",
            "&.Mui-selected": {
              backgroundColor: s.selectedTint,
              color: BRAND_COLOR,
              "&:hover": { backgroundColor: s.selectedTintStrong },
            },
          },
        },
      },
      MuiChip: {
        styleOverrides: {
          root: { fontWeight: 500 },
          outlined: {
            borderColor:
              mode === "dark"
                ? "rgba(231, 235, 242, 0.22)"
                : "rgba(26, 34, 48, 0.18)",
          },
        },
      },
      MuiTab: {
        styleOverrides: {
          root: { textTransform: "none", fontWeight: 600, minHeight: 44 },
        },
      },
      MuiTableCell: {
        styleOverrides: {
          head: { fontWeight: 700, color: s.inkSecondary },
          root: { borderColor: s.hairline },
        },
      },
      MuiListItemButton: {
        styleOverrides: {
          root: {
            "&.Mui-selected": {
              backgroundColor: s.selectedTint,
              "&:hover": { backgroundColor: s.selectedTintStrong },
            },
          },
        },
      },
    },
  })

  theme = responsiveFontSizes(theme, { factor: 3 })
  return theme
}

// Default (light) theme — kept for any code that isn't mode-aware yet.
const theme = buildTheme("light")
export default theme
