import * as React from "react"
import Box from "@mui/material/Box"

// A two-tone horizontal bar: the left color fills `fraction` (0..1) of the
// width, the right color shows through the remainder. Used for win-share /
// probability splits (HeadToHead scoreboard, AI pre-game prediction).
export default function WinShareBar(props: {
  fraction: number
  leftColor: string
  rightColor: string
  height?: number
}) {
  return (
    <Box
      sx={{
        position: "relative",
        height: props.height ?? 14,
        borderRadius: 1,
        overflow: "hidden",
        bgcolor: props.rightColor,
      }}
    >
      <Box
        sx={{
          position: "absolute",
          inset: 0,
          width: `${props.fraction * 100}%`,
          bgcolor: props.leftColor,
        }}
      />
    </Box>
  )
}
