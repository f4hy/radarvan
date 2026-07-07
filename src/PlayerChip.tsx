import Avatar from "@mui/material/Avatar"
import Chip from "@mui/material/Chip"
import Box from "@mui/material/Box"
import Typography from "@mui/material/Typography"
import { usePlayerColors } from "./PlayerColorsContext"
import { contrastTextColor, getColorHex, playerColor } from "./utils"

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
// we have it. The old deterministic hash-per-name becomes a secondary ring
// cue instead, so two players who do happen to share a color still read as
// distinct. Falls back to hash-as-fill (no ring - nothing to disambiguate)
// for names without enough game data yet.
function useAvatarColors(name: string): {
  bgcolor: string
  textColor: string
  ringColor: string | null
} {
  const actualColor = usePlayerColors()[name]
  const hash = playerColor(name)
  if (actualColor == null) {
    return { bgcolor: hash, textColor: "#fff", ringColor: null }
  }
  const bgcolor = getColorHex(actualColor)
  return { bgcolor, textColor: contrastTextColor(bgcolor), ringColor: hash }
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
