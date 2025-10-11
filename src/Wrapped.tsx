import NavigateBeforeIcon from "@mui/icons-material/NavigateBefore"
import NavigateNextIcon from "@mui/icons-material/NavigateNext"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import CircularProgress from "@mui/material/CircularProgress"
import IconButton from "@mui/material/IconButton"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { Wrapped } from "./proto/match"
import { General } from "./proto/match"

const players = ["Bill", "Brendan", "Jared", "Sean"]
const maxPage = 4
const clamp = (num: number) => Math.min(Math.max(num, 0), maxPage)

function getWrapped(player: string, callback: (m: Wrapped) => void) {
  fetch("/api/wrapped/" + player).then((r) =>
    r
      .blob()
      .then((b) => b.arrayBuffer())
      .then((j) => {
        const a = new Uint8Array(j)
        const wrapped = Wrapped.decode(a)
        console.log(JSON.stringify(wrapped))
        callback(wrapped)
      })
      .catch((e) => alert(e))
  )
}

function color(n: number) {
  switch (n) {
    case 0:
      return "primary.dark"
    case 1:
      return "secondary.dark"
    case 2:
      return "primary.light"
    case 3:
      return "secondary.light"
    default:
      return "primary.main"
  }
}

function WrappedPage(props: {
  player: string | null
  page: number
  data: Wrapped
}) {
  const w = props.data
  if (props.player === null) {
    return (
      <Typography variant="h2">Select your name for your wrapped</Typography>
    )
  }
  if (props.page < 1) {
    return (
      <Typography variant="h2">
        {props.player + " Welcome to your Generals 2022 Wrapped."}
      </Typography>
    )
  }
  if (props.page === 1) {
    return (
      <Stack spacing={8} direction="column">
        <Typography variant="h2">
          {"Wow you have played " + w.gamesPlayed + " games of Generals."}
        </Typography>
        <Typography variant="h2">
          {"Thats " + w.hoursPlayed.toFixed(2) + " Hours of your life."}
        </Typography>
      </Stack>
    )
  }
  if (props.page === 2) {
    return (
      <Stack spacing={8} direction="column">
        <Typography variant="h2">
          {"Your most played General is " + General[w.mostPlayed]}
        </Typography>{" "}
        <Typography variant="h2">
          {"You have a winrate of " +
            (100 * w.mostPlayedWinrate).toFixed(1) +
            "% with " +
            General[w.mostPlayed] +
            "."}
        </Typography>
      </Stack>
    )
  }
  if (props.page === 3) {
    return (
      <Stack spacing={8} direction="column">
        <Typography variant="h2">
          {"Your most built unit is " + w.mostBuilt}
        </Typography>
        <Typography variant="h2">
          {"Building " +
            w.mostBuiltCount +
            " this year  and spending $" +
            w.mostBuiltSpent +
            " total"}
        </Typography>
        <Typography variant="h2">
          {w.mostBuiltMore > 0
            ? "That is " + w.mostBuiltMore + " more than anyone else"
            : "That is " + -w.mostBuiltMore + " fewer than someone else"}
        </Typography>
      </Stack>
    )
  }
  if (props.page > 3) {
    return (
      <Stack spacing={8} direction="column">
        <Typography variant="h2">
          {"Your relative best General is " +
            General[w.bestGeneral] +
            " with a winrate of " +
            (100 * w.bestWinrate).toFixed(1) +
            "%"}
        </Typography>
        <Typography variant="h2">
          {"Compared to the average for " +
            General[w.bestGeneral] +
            " of " +
            (100 * w.bestAverage).toFixed(1) +
            "%"}
        </Typography>
      </Stack>
    )
  }
  return <Typography variant="h2">Select your name for your wrapped</Typography>
}

export default function WrappedYear() {
  const [player, setPlayer] = React.useState<string | null>(null)
  const [progress, setProgress] = React.useState(0)
  const [page, setPage] = React.useState(0)
  const [wrappedData, setWrappedData] = React.useState<Wrapped | null>(null)

  React.useEffect(() => {
    const timer = setInterval(() => {
      setProgress((prevProgress) => {
        if (prevProgress >= 100) {
          setPage(clamp(page + 1))
          return 0
        } else {
          return prevProgress + 1
        }
      })
    }, 100)
    return () => {
      clearInterval(timer)
    }
  }, [page])

  return (
    <Paper>
      <Stack spacing={2} direction="column">
        <Stack
          spacing={8}
          direction="row"
          alignItems="center"
          justifyContent="center"
        >
          {players.map((p) => (
            <Button
              variant="contained"
              onClick={() => {
                setPlayer(p)
                setProgress(0)
                setPage(0)
                getWrapped(p, setWrappedData)
              }}
            >
              {p}
            </Button>
          ))}
        </Stack>
        <Stack spacing={2} direction="column">
          <Box
            sx={{
              height: "80%",
              minHeight: "30vw",
              backgroundColor: color(page),
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            {wrappedData ? (
              <WrappedPage player={player} page={page} data={wrappedData} />
            ) : null}
          </Box>
          <Stack
            spacing={2}
            direction="row"
            alignItems="center"
            justifyContent="center"
          >
            <IconButton
              disabled={page <= 0}
              color="primary"
              onClick={() => {
                setPage(clamp(page - 1))
                setProgress(0)
              }}
            >
              <NavigateBeforeIcon />
            </IconButton>
            <Typography>{page + "/" + maxPage}</Typography>
            <CircularProgress variant="determinate" value={progress} />
            <IconButton
              disabled={page >= maxPage}
              color="primary"
              onClick={() => {
                setPage(clamp(page + 1))
                setProgress(0)
              }}
            >
              <NavigateNextIcon />
            </IconButton>
          </Stack>
        </Stack>
      </Stack>
    </Paper>
  )
}
