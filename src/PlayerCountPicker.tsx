import * as React from "react"
import Button from "@mui/material/Button"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"

// Shared "how many players?" chooser used by the Map Voting and Choose Map pages.
export default function PlayerCountPicker({
  title,
  subtitle,
  counts,
  onPick,
}: {
  title: string
  subtitle?: string
  counts: number[]
  onPick: (count: number) => void
}) {
  return (
    <Stack spacing={2} alignItems="center" sx={{ mt: 4 }}>
      <Typography variant="h6">{title}</Typography>
      {subtitle && (
        <Typography variant="body2" color="text.secondary">
          {subtitle}
        </Typography>
      )}
      <Stack
        direction="row"
        spacing={1}
        flexWrap="wrap"
        justifyContent="center"
      >
        {counts.map((c) => (
          <Button key={c} variant="outlined" onClick={() => onPick(c)}>
            {c} players
          </Button>
        ))}
      </Stack>
    </Stack>
  )
}
