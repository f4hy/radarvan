import { createTheme, responsiveFontSizes } from "@mui/material/styles"

/**
 * Central design tokens for the whole app — LIGHT theme.
 *
 * Surface hierarchy: a cool light-grey canvas (`background.default`) with white
 * cards floating on it, plus a neutral dark-slate top bar (never blue) so the
 * blue stays reserved for interactive elements.
 *
 * Two color rules keep things consistent:
 *  1. Blue means "interactive" only (links, primary buttons, selected state).
 *  2. Win is green, loss is red — for single indicators (pills, dots, deltas).
 *     Import the constants below instead of hand-picking hexes so recharts
 *     (which can't read the MUI theme) stays in sync with MUI.
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

// App chrome.
const APPBAR_BG = "#1f2733"
const PAGE_BG = "#f5f6f8"
const BORDER = "rgba(26, 34, 48, 0.10)"

let theme = createTheme({
  palette: {
    primary: { main: BRAND_COLOR },
    success: { main: WIN_COLOR },
    error: { main: LOSS_COLOR },
    background: {
      default: PAGE_BG,
      paper: "#ffffff",
    },
    text: {
      primary: "#1a2230",
      secondary: "#5b6675",
    },
    divider: BORDER,
  },
  shape: { borderRadius: 10 },
  typography: {
    fontFamily: [
      "-apple-system",
      "BlinkMacSystemFont",
      "Segoe UI",
      "Roboto",
      "Helvetica Neue",
      "Arial",
      "sans-serif",
    ].join(","),
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
        outlined: { borderColor: BORDER },
        // Softer, lower shadows than MUI defaults for a flatter, modern feel.
        elevation1: {
          boxShadow: "0 1px 2px rgba(16, 24, 40, 0.06)",
          border: "1px solid rgba(26, 34, 48, 0.07)",
        },
      },
    },
    MuiCard: {
      defaultProps: { variant: "outlined" },
      styleOverrides: {
        root: { borderColor: BORDER },
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
          borderColor: "rgba(26, 34, 48, 0.16)",
          "&.Mui-selected": {
            backgroundColor: "rgba(47, 109, 240, 0.12)",
            color: BRAND_COLOR,
            "&:hover": { backgroundColor: "rgba(47, 109, 240, 0.18)" },
          },
        },
      },
    },
    MuiChip: {
      styleOverrides: {
        root: { fontWeight: 500 },
        outlined: { borderColor: "rgba(26, 34, 48, 0.18)" },
      },
    },
    MuiTab: {
      styleOverrides: {
        root: { textTransform: "none", fontWeight: 600, minHeight: 44 },
      },
    },
    MuiTableCell: {
      styleOverrides: {
        head: { fontWeight: 700, color: "#5b6675" },
        root: { borderColor: "rgba(26, 34, 48, 0.08)" },
      },
    },
    MuiListItemButton: {
      styleOverrides: {
        root: {
          "&.Mui-selected": {
            backgroundColor: "rgba(47, 109, 240, 0.12)",
            "&:hover": { backgroundColor: "rgba(47, 109, 240, 0.18)" },
          },
        },
      },
    },
  },
})

theme = responsiveFontSizes(theme, { factor: 3 })

export default theme
