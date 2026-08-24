import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { usePlayerPalette } from "./PlayerColorsContext"
import { usePlayerNav } from "./PlayerNavContext"

/**
 * The player identity used everywhere in the app: a swatch of the color they
 * actually play, their name, and a click through to their profile.
 *
 * The swatch is the raw in-game color; everything around it is derived from
 * that hue (utils.playerPalette) so the chip reads as *theirs* without putting
 * `#FF0000` next to `#FFFF00` on an otherwise muted page.
 *
 * This used to be an initial-in-a-circle filled with the raw color and ringed
 * in a second, hash-derived color. The ring was there to separate two players
 * who happen to play the same color — but the name is written right beside it,
 * so there was no ambiguity for it to resolve, and carrying two colors meant
 * neither one read as "this player's color". One color per player now, and the
 * hash keeps its real job: standing in when we don't know someone's yet.
 *
 * Both exports are memoized: they are the most-repeated element in the app
 * (a few hundred on the Team Stats 3v3 tab), and every prop is a primitive.
 */

/** A player's color as a plain dot. Deliberately not a `Box`/`sx`: this is the
 * hottest leaf in the app and none of these six properties reads a theme
 * token, so going through emotion would buy nothing but a serialize-and-hash
 * per chip. */
export const PlayerDot = React.memo(function PlayerDot(props: {
  color: string
  size?: number
}) {
  const size = props.size ?? 9
  return (
    <span
      style={{
        width: size,
        height: size,
        borderRadius: "50%",
        background: props.color,
        flexShrink: 0,
        // A hairline of the page's own ink so a pale swatch (yellow, silver)
        // still has an edge against the surface behind it.
        boxShadow: "inset 0 0 0 1px rgba(26, 34, 48, 0.22)",
      }}
    />
  )
})

export const PlayerChip = React.memo(function PlayerChip(props: {
  name: string
  size?: "small" | "medium"
  /** Opt out of navigation — for a chip inside another control. */
  disableNav?: boolean
}) {
  const palette = usePlayerPalette(props.name)
  const nav = usePlayerNav()
  // Navigating to the profile is the default, not something each call site has
  // to remember: every chip in the app is a link to that player unless it's
  // told otherwise, which is what makes the stats browsable rather than a set
  // of unconnected reports.
  const onClick = props.disableNav
    ? undefined
    : () => nav.goToPlayerProfile(props.name)
  const medium = props.size === "medium"
  return (
    <Chip
      icon={<PlayerDot color={palette.dot} size={medium ? 11 : 9} />}
      label={props.name}
      size={props.size ?? "small"}
      variant="filled"
      clickable={onClick != null}
      onClick={onClick}
      sx={{
        bgcolor: palette.tint,
        color: palette.ink,
        border: `1px solid ${palette.edge}`,
        fontWeight: 600,
        "& .MuiChip-icon": { ml: medium ? 1 : 0.75, mr: -0.25 },
        "& .MuiChip-label": { px: medium ? 1 : 0.85 },
        ...(onClick && {
          "&:hover, &:focus-visible": { bgcolor: palette.tintStrong },
        }),
      }}
    />
  )
})

/** Swatch + name with no chip around it, for dense rows and table cells. */
export const PlayerLabel = React.memo(function PlayerLabel(props: {
  name: string
  bold?: boolean
  /** Type scale for the name — defaults to body2 for dense rows. */
  variant?: "body2" | "h6"
}) {
  const palette = usePlayerPalette(props.name)
  const nav = usePlayerNav()
  const large = props.variant === "h6"
  return (
    <Box
      component="button"
      type="button"
      onClick={() => nav.goToPlayerProfile(props.name)}
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: large ? 1 : 0.75,
        border: 0,
        p: 0,
        bgcolor: "transparent",
        font: "inherit",
        color: "inherit",
        cursor: "pointer",
        textAlign: "left",
        "&:hover .MuiTypography-root": { color: palette.ink },
      }}
    >
      <PlayerDot color={palette.dot} size={large ? 12 : 9} />
      <Typography
        variant={props.variant ?? "body2"}
        component="span"
        sx={{ fontWeight: props.bold ? 700 : 500, transition: "color 120ms" }}
      >
        {props.name}
      </Typography>
    </Box>
  )
})

export default PlayerChip
