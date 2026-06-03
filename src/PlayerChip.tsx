import Avatar from "@mui/material/Avatar"
import Chip from "@mui/material/Chip"
import Box from "@mui/material/Box"
import Typography from "@mui/material/Typography"
import { playerColor } from "./utils"

/**
 * Consistent player identity used across the app. A small color-coded initial
 * avatar (deterministic per name via `playerColor`) plus the name, so the same
 * player reads as the same color everywhere and lists scan fast.
 */

function initial(name: string): string {
  return name.trim().charAt(0).toUpperCase() || "?"
}

export function PlayerChip(props: {
  name: string
  size?: "small" | "medium"
  onClick?: () => void
}) {
  const color = playerColor(props.name)
  return (
    <Chip
      avatar={
        <Avatar sx={{ bgcolor: color, color: "#fff !important" }}>
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
  const color = playerColor(props.name)
  const s = props.avatarSize ?? 22
  return (
    <Box sx={{ display: "inline-flex", alignItems: "center", gap: 0.75 }}>
      <Avatar sx={{ width: s, height: s, bgcolor: color, fontSize: s * 0.5 }}>
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
