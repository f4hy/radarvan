import LinearProgress from "@mui/material/LinearProgress"
import Skeleton from "@mui/material/Skeleton"
import Stack from "@mui/material/Stack"
import Box from "@mui/material/Box"
import * as React from "react"

// Generic page loader: an indeterminate top bar plus a skeleton that mirrors the
// shape most stat pages settle into (a title, a filter row, a band of cards, and
// a wide chart block) so a page fades in toward its real layout instead of
// flashing a pair of grey rectangles.
export default function Loading() {
  return (
    <Stack spacing={2}>
      <LinearProgress />
      <Box>
        <Skeleton variant="text" width="32%" height={36} animation="wave" />
        <Skeleton variant="text" width="52%" animation="wave" />
      </Box>
      <Stack direction="row" spacing={1.5} flexWrap="wrap" useFlexGap>
        {[...Array(4)].map((_, i) => (
          <Skeleton
            key={i}
            variant="rounded"
            animation="wave"
            sx={{ flex: "1 1 160px", height: 96 }}
          />
        ))}
      </Stack>
      <Skeleton
        variant="rounded"
        animation="wave"
        sx={{ width: "100%", height: 280 }}
      />
    </Stack>
  )
}

export function MatchesLoading() {
  return (
    <Stack spacing={1}>
      <LinearProgress />
      <Stack direction="row" spacing={1}>
        <Skeleton variant="rounded" width="50%" height={120} animation="wave" />
        <Skeleton variant="rounded" width="50%" height={120} animation="wave" />
      </Stack>
      {[...Array(8)].map((_, i) => (
        <Skeleton key={i} variant="rounded" height={48} animation="wave" />
      ))}
    </Stack>
  )
}

export function MatchRowLoading() {
  return (
    <Stack spacing={1} sx={{ p: 1 }}>
      <Skeleton variant="text" width="60%" animation="wave" />
      <Stack direction="row" spacing={1}>
        <Skeleton variant="rounded" width="45%" height={100} animation="wave" />
        <Skeleton variant="rounded" width="45%" height={100} animation="wave" />
        <Skeleton variant="rounded" width="10%" height={100} animation="wave" />
      </Stack>
    </Stack>
  )
}
