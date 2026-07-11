import Avatar from "@mui/material/Avatar"
import Chip from "@mui/material/Chip"
import Box from "@mui/material/Box"
import Typography from "@mui/material/Typography"
import { useTheme } from "@mui/material/styles"
import { usePlayerAccentColor, usePlayerColors } from "./PlayerColorsContext"
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
  onClick?: () => void
}) {
  const { bgcolor, textColor, ringColor } = useAvatarColors(props.name)
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
      clickable={props.onClick != null}
      onClick={props.onClick}
      sx={{ fontWeight: 600 }}
    />
  )
}

/** Bare avatar + name, no chip border — for inline use in dense rows. */
export function PlayerLabel(props: {
  name: string
  avatarSize?: number
  bold?: boolean
}) {
  const { bgcolor, textColor, ringColor } = useAvatarColors(props.name)
  const s = props.avatarSize ?? 22
  return (
    <Box sx={{ display: "inline-flex", alignItems: "center", gap: 0.75 }}>
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
        variant="body2"
        component="span"
        sx={{ fontWeight: props.bold ? 700 : 500 }}
      >
        {props.name}
      </Typography>
    </Box>
  )
}

export default PlayerChip
