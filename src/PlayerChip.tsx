import Avatar from "@mui/material/Avatar"
import Chip from "@mui/material/Chip"
import Box from "@mui/material/Box"
import Typography from "@mui/material/Typography"
import { useTheme } from "@mui/material/styles"
import { usePlayerAccentColor, usePlayerColors } from "./PlayerColorsContext"
import { usePlayerNav } from "./PlayerNavContext"
import { playerColor } from "./utils"

/**
 * Consistent player identity used across the app. A small initial avatar
 * plus the name, so the same player reads as the same color everywhere and
 * lists scan fast.
 */

function initial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "?"
}

// This community's players rarely contest the same color, so the avatar
// fill is the player's actual most-common in-game color (from data) when
// we have it - usePlayerAccentColor already picks that (or the deterministic
// hash-per-name fallback). The hash becomes a secondary ring cue on top, so
// two players who do happen to share a color still read as distinct; no
// ring when we're already falling back to the hash (nothing to disambiguate).
function useAvatarColors(name: string): {
  bgcolor: string
  textColor: string
  ringColor: string | null
} {
  const theme = useTheme()
  const bgcolor = usePlayerAccentColor(name)
  const hasActualColor = usePlayerColors()[name] != null
  return {
    bgcolor,
    textColor: theme.palette.getContrastText(bgcolor),
    ringColor: hasActualColor ? playerColor(name) : null,
  }
}

export function PlayerChip(props: {
  name: string
  size?: "small" | "medium"
  /** Overrides the default (open this player's profile). */
  onClick?: () => void
  /** Opt out of navigation entirely — for a chip inside another control. */
  disableNav?: boolean
}) {
  const { bgcolor, textColor, ringColor } = useAvatarColors(props.name)
  const nav = usePlayerNav()
  // Navigating to the profile is the default, not something each call site has
  // to remember: every chip in the app is a link to that player unless it's
  // told otherwise, which is what makes the stats browsable rather than a set
  // of unconnected reports.
  const onClick =
    props.onClick ??
    (props.disableNav || !nav.enabled
      ? undefined
      : () => nav.goToPlayerProfile(props.name))
  return (
    <Chip
      avatar={
        <Avatar
          sx={{
            bgcolor,
            color: `${textColor} !important`,
            ...(ringColor && { border: `2px solid ${ringColor}` }),
          }}
        >
          {initial(props.name)}
        </Avatar>
      }
      label={props.name}
      size={props.size ?? "small"}
      variant="outlined"
      clickable={onClick != null}
      onClick={onClick}
      sx={{ fontWeight: 600 }}
    />
  )
}

/** Bare avatar + name, no chip border — for inline use in dense rows. */
export function PlayerLabel(props: {
  name: string
  avatarSize?: number
  bold?: boolean
  disableNav?: boolean
  /** Type scale for the name — defaults to body2 for dense rows. */
  variant?: "body2" | "subtitle1" | "h6"
}) {
  const { bgcolor, textColor, ringColor } = useAvatarColors(props.name)
  const nav = usePlayerNav()
  const s = props.avatarSize ?? 22
  const clickable = !props.disableNav && nav.enabled
  return (
    <Box
      component={clickable ? "button" : "span"}
      type={clickable ? "button" : undefined}
      onClick={clickable ? () => nav.goToPlayerProfile(props.name) : undefined}
      sx={{
        display: "inline-flex",
        alignItems: "center",
        gap: 0.75,
        ...(clickable && {
          border: 0,
          p: 0,
          bgcolor: "transparent",
          font: "inherit",
          color: "inherit",
          cursor: "pointer",
          textAlign: "left",
          "&:hover .MuiTypography-root": { textDecoration: "underline" },
        }),
      }}
    >
      <Avatar
        sx={{
          width: s,
          height: s,
          bgcolor,
          color: `${textColor} !important`,
          fontSize: s * 0.5,
          ...(ringColor && { border: `2px solid ${ringColor}` }),
        }}
      >
        {initial(props.name)}
      </Avatar>
      <Typography
        variant={props.variant ?? "body2"}
        component="span"
        sx={{ fontWeight: props.bold ? 700 : 500 }}
      >
        {props.name}
      </Typography>
    </Box>
  )
}

export default PlayerChip
