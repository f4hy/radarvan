import LinearProgress from "@mui/material/LinearProgress"
import Skeleton from "@mui/material/Skeleton"
import Stack from "@mui/material/Stack"
import * as React from "react"

export default function Loading() {
  return (
    <Stack>
      <LinearProgress />
      <Stack direction="row">
        <Skeleton
          variant="rectangular"
          width="50%"
          height={150}
          animation="wave"
        />
        <Skeleton
          variant="rectangular"
          width="50%"
          height={150}
          animation="wave"
        />
      </Stack>
    </Stack>
  )
}

export function MatchesLoading() {
  return (
    <Stack spacing={1}>
      <LinearProgress />
      <Stack direction="row" spacing={1}>
        <Skeleton
          variant="rectangular"
          width="50%"
          height={120}
          animation="wave"
        />
        <Skeleton
          variant="rectangular"
          width="50%"
          height={120}
          animation="wave"
        />
      </Stack>
      {[...Array(8)].map((_, i) => (
        <Skeleton key={i} variant="rectangular" height={48} animation="wave" />
      ))}
    </Stack>
  )
}

export function MatchRowLoading() {
  return (
    <Stack spacing={1} sx={{ p: 1 }}>
      <Skeleton variant="text" width="60%" animation="wave" />
      <Stack direction="row" spacing={1}>
        <Skeleton
          variant="rectangular"
          width="45%"
          height={100}
          animation="wave"
        />
        <Skeleton
          variant="rectangular"
          width="45%"
          height={100}
          animation="wave"
        />
        <Skeleton
          variant="rectangular"
          width="10%"
          height={100}
          animation="wave"
        />
      </Stack>
    </Stack>
  )
}
