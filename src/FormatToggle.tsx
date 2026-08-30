import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Typography from "@mui/material/Typography"

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
  return (
    <>
      {props.label && (
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          {props.label}
        </Typography>
      )}
      <ToggleButtonGroup
        value={props.value}
        exclusive
        size="small"
        onChange={(_, next: T | null) => next !== null && props.onChange(next)}
      >
        {props.options.map((option) => (
          <ToggleButton key={option} value={option}>
            {option}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </>
  )
}
