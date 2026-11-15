import Box from "@mui/material/Box"
import Stack from "@mui/material/Stack"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Typography from "@mui/material/Typography"
import { EASE } from "../lib/motion"
import { selectedTintSx } from "../lib/theme"
import { indicatorSx, useSlidingIndicator } from "../lib/useSlidingIndicator"

/**
 * The game-format filter, in one place.
 *
 * Six pages offered this control and it read three different ways: two pages
 * hand-rolled an identical label-plus-group into their `Page` actions slot,
 * three rendered a bare group with no label, and one used an `h6` "Game
 * Format:" heading. The `Page` actions slot should receive a component, not a
 * markup pattern for each page to re-type.
 *
 * `options` stays a parameter because the sets genuinely differ — Player Stats
 * has no 1v1 column, Player Synergy offers its own spread.
 */
export const ALL_FORMATS = ["All", "1v1", "2v2", "3v3", "4v4"] as const
export const TEAM_FORMATS = ["All", "2v2", "3v3", "4v4"] as const

export default function FormatToggle<T extends string>(props: {
  options: readonly T[]
  value: T
  onChange: (value: T) => void
  /** Omit for a bare group, where the surrounding row already says what it is. */
  label?: string
}) {
  const { ref, rect } = useSlidingIndicator<HTMLDivElement>(
    ".Mui-selected",
    `${props.value}|${props.options.join("|")}`,
  )
  const selected = props.options.indexOf(props.value)
  const first = selected === 0
  const last = selected === props.options.length - 1
  // The indicator sits beside the group, not inside it: ToggleButtonGroup
  // styles its first and last child as the end buttons.
  const group = (
    <Box ref={ref} sx={{ position: "relative", display: "inline-flex" }}>
      <Box
        aria-hidden
        sx={(t) => {
          // Square against a neighbour, rounded where it meets the group's end.
          const l = first ? t.shape.borderRadius : 0
          const r = last ? t.shape.borderRadius : 0
          return {
            ...indicatorSx(rect),
            borderRadius: `${l}px ${r}px ${r}px ${l}px`,
            ...selectedTintSx(t),
          }
        }}
      />
      <ToggleButtonGroup
        value={props.value}
        exclusive
        size="small"
        onChange={(_, next: T | null) => next !== null && props.onChange(next)}
        sx={{
          // The selected tint is the sliding indicator, not the button's own.
          "& .MuiToggleButton-root.Mui-selected, & .MuiToggleButton-root.Mui-selected:hover":
            { bgcolor: "transparent" },
          "& .MuiToggleButton-root": { transition: `color 200ms ${EASE}` },
        }}
      >
        {props.options.map((option) => (
          <ToggleButton key={option} value={option}>
            {option}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </Box>
  )
  if (!props.label) return group
  // One flex item, so a wrapping actions row can't strand the label at the end
  // of one line and its buttons at the start of the next.
  return (
    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        {props.label}
      </Typography>
      {group}
    </Stack>
  )
}
