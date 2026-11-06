import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Tooltip from "@mui/material/Tooltip"
import { Link } from "react-router"
import type { MapEntry } from "../lib/mapGeneralStats"
import { displayMapName, winRate } from "../lib/utils"

// A best/worst-map chip that truncates the map name and never the percentage,
// so it can sit in a fixed-width grid column without wrapping.
export default function MapRateChip(props: {
  entry: MapEntry
  variant: "best" | "worst"
  /** A link to follow, or a click handler (Map Stats scrolls in place). */
  to?: string
  onClick?: () => void
  hint?: string
}) {
  const { entry } = props
  const name = displayMapName(entry.mapName)
  const total = entry.wins + entry.losses
  const label = (
    <Box sx={{ display: "flex", gap: 0.75, minWidth: 0 }}>
      <Box
        component="span"
        sx={{
          overflow: "hidden",
          textOverflow: "ellipsis",
          color: "text.primary",
        }}
      >
        {name}
      </Box>
      <Box component="span" sx={{ fontWeight: 700, flexShrink: 0 }}>
        {(winRate(entry.wins, entry.losses) * 100).toFixed(0)}%
      </Box>
    </Box>
  )
  const common = {
    size: "small",
    color: props.variant === "best" ? "success" : "error",
    variant: "outlined",
    label,
    sx: { maxWidth: "100%", justifySelf: "start", fontSize: "0.7rem" },
  } as const
  return (
    <Tooltip
      title={`${name}: ${entry.wins}W–${entry.losses}L (${total} games)${props.hint ? ` — ${props.hint}` : ""}`}
    >
      {props.to !== undefined ? (
        <Chip {...common} component={Link} to={props.to} clickable />
      ) : (
        <Chip {...common} onClick={props.onClick} />
      )}
    </Tooltip>
  )
}
