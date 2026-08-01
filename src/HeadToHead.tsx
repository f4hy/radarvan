import ExpandLessIcon from "@mui/icons-material/ExpandLess"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import Autocomplete from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import Grid from "@mui/material/Grid"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TextField from "@mui/material/TextField"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Typography from "@mui/material/Typography"
import * as React from "react"
import {
  HeadToHeadDetail,
  HeadToHeadGame,
  HeadToHeadGeneralRecord,
  HeadToHeadMapRecord,
  PlayerGameCount,
} from "./api"
import { Client } from "./Client"
import DisplayGeneral from "./Generals"
import { toGeneralName } from "./general_utils"
import Loading from "./Loading"
import ShowMatchDetails from "./ShowMatchDetails"
import { useErrorSnackbar } from "./useErrorSnackbar"
import { displayMapName, formatPercent, playerColor } from "./utils"
import WinRateChip from "./WinRateChip"
import WinShareBar from "./WinShareBar"

const FORMAT_OPTIONS = ["All", "1v1", "2v2", "3v3", "4v4"] as const
type GameFormat = (typeof FORMAT_OPTIONS)[number]

const compactCash = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
})
const formatValue = (n: number) => `$${compactCash.format(n)}`

// The big "12 — 7" scoreboard with a win-share bar colored per player.
function Scoreboard(props: { data: HeadToHeadDetail }) {
  const {
    player1,
    player2,
    player1Wins,
    player2Wins,
    teammateGames,
    teammateWins,
    player1ValueDestroyed,
    player2ValueDestroyed,
  } = props.data
  const total = player1Wins + player2Wins
  const share1 = total > 0 ? player1Wins / total : 0.5
  const c1 = playerColor(player1)
  const c2 = playerColor(player2)
  const v1 = player1ValueDestroyed ?? 0
  const v2 = player2ValueDestroyed ?? 0
  const valueTotal = v1 + v2
  const valueShare1 = valueTotal > 0 ? v1 / valueTotal : 0.5

  return (
    <Box sx={{ mb: 3 }}>
      <Stack
        direction="row"
        spacing={2}
        sx={{
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Box sx={{ flex: 1, textAlign: "left" }}>
          <Typography variant="h5" sx={{ color: c1, fontWeight: "bold" }}>
            {player1}
          </Typography>
          <Typography
            variant="caption"
            sx={{
              color: "text.secondary",
            }}
          >
            {formatPercent(share1)} of decided games
          </Typography>
        </Box>
        <Typography
          variant="h3"
          sx={{ fontWeight: "bold", whiteSpace: "nowrap" }}
        >
          <Box component="span" sx={{ color: c1 }}>
            {player1Wins}
          </Box>
          <Box component="span" sx={{ color: "text.secondary" }}>
            {" — "}
          </Box>
          <Box component="span" sx={{ color: c2 }}>
            {player2Wins}
          </Box>
        </Typography>
        <Box sx={{ flex: 1, textAlign: "right" }}>
          <Typography variant="h5" sx={{ color: c2, fontWeight: "bold" }}>
            {player2}
          </Typography>
          <Typography
            variant="caption"
            sx={{
              color: "text.secondary",
            }}
          >
            {formatPercent(1 - share1)} of decided games
          </Typography>
        </Box>
      </Stack>
      <Box sx={{ mt: 1.5 }}>
        <WinShareBar
          fraction={share1}
          leftColor={c1}
          rightColor={c2}
          height={16}
        />
      </Box>
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
          mt: 0.5,
          textAlign: "center",
        }}
      >
        {total} head-to-head game{total === 1 ? "" : "s"}
      </Typography>
      {teammateGames > 0 && (
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            textAlign: "center",
          }}
        >
          Also teammates in {teammateGames} game{teammateGames === 1 ? "" : "s"}{" "}
          ({teammateWins}-{teammateGames - teammateWins} together)
        </Typography>
      )}
      {valueTotal > 0 && (
        <Box sx={{ mt: 2 }}>
          <Stack
            direction="row"
            spacing={2}
            sx={{
              alignItems: "center",
              justifyContent: "space-between",
            }}
          >
            <Typography variant="body2" sx={{ color: c1, fontWeight: "bold" }}>
              {formatValue(v1)} destroyed
            </Typography>
            <Typography
              variant="caption"
              sx={{
                color: "text.secondary",
              }}
            >
              Value destroyed (recent games)
            </Typography>
            <Typography variant="body2" sx={{ color: c2, fontWeight: "bold" }}>
              {formatValue(v2)} destroyed
            </Typography>
          </Stack>
          <Box sx={{ mt: 0.5 }}>
            <WinShareBar
              fraction={valueShare1}
              leftColor={c1}
              rightColor={c2}
              height={8}
            />
          </Box>
        </Box>
      )}
    </Box>
  )
}

// Per-player record by the general they piloted, with confidence-aware chips.
function GeneralBreakdown(props: {
  player: string
  records: HeadToHeadGeneralRecord[]
}) {
  if (props.records.length === 0) return null
  return (
    <Box>
      <Typography
        variant="subtitle1"
        sx={{ color: playerColor(props.player), mb: 1 }}
      >
        {props.player} by general
      </Typography>
      <Stack spacing={0.5}>
        {props.records.map((r) => (
          <Stack
            key={r.general}
            direction="row"
            spacing={1}
            sx={{
              alignItems: "center",
            }}
          >
            <DisplayGeneral general={r.general} />
            <Typography variant="body2" sx={{ flex: 1 }}>
              {toGeneralName(r.general)}
            </Typography>
            <WinRateChip wins={r.wins} losses={r.losses} />
          </Stack>
        ))}
      </Stack>
    </Box>
  )
}

function MapBreakdown(props: {
  records: HeadToHeadMapRecord[]
  player1: string
  player2: string
}) {
  if (props.records.length === 0) return null
  const c1 = playerColor(props.player1)
  const c2 = playerColor(props.player2)
  return (
    <Box>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        By map
      </Typography>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>
                <strong>Map</strong>
              </TableCell>
              <TableCell align="center" sx={{ color: c1 }}>
                <strong>{props.player1}</strong>
              </TableCell>
              <TableCell align="center" sx={{ color: c2 }}>
                <strong>{props.player2}</strong>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {props.records.map((r) => (
              <TableRow key={r.map} hover>
                <TableCell>{displayMapName(r.map)}</TableCell>
                <TableCell align="center" sx={{ color: c1 }}>
                  {r.player1Wins}
                </TableCell>
                <TableCell align="center" sx={{ color: c2 }}>
                  {r.player2Wins}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

function GameRow(props: {
  game: HeadToHeadGame
  player1: string
  player2: string
}) {
  const { game } = props
  const [open, setOpen] = React.useState(false)
  const winnerName = game.player1Won ? props.player1 : props.player2
  const winnerColor = playerColor(winnerName)
  return (
    <>
      <TableRow
        hover
        sx={{ "& > *": { borderBottom: open ? "unset" : undefined } }}
      >
        <TableCell>{game.date.toISOString().substring(0, 10)}</TableCell>
        <TableCell>{displayMapName(game.map)}</TableCell>
        <TableCell>
          <Chip
            size="small"
            label={game.gameFormat ?? "?"}
            variant="outlined"
          />
        </TableCell>
        <TableCell align="center">
          <Stack
            direction="row"
            spacing={0.5}
            sx={{
              alignItems: "center",
            }}
          >
            <DisplayGeneral general={game.player1General} />
            <Box component="span" sx={{ color: "text.secondary" }}>
              vs
            </Box>
            <DisplayGeneral general={game.player2General} />
          </Stack>
        </TableCell>
        <TableCell>
          <Chip
            size="small"
            label={`${winnerName} won`}
            sx={{ bgcolor: winnerColor, color: "common.white" }}
          />
        </TableCell>
        <TableCell align="right">
          <Button size="small" onClick={() => setOpen((v) => !v)}>
            {open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
            details
          </Button>
        </TableCell>
      </TableRow>
      {open && (
        <TableRow>
          <TableCell colSpan={6} sx={{ py: 1 }}>
            <ShowMatchDetails id={game.matchId} />
          </TableCell>
        </TableRow>
      )}
    </>
  )
}

// Decoupled from HeadToHeadDetail (only ever needs the game list plus the
// two names GameRow uses to label who won) so other pages - e.g. the
// bracket's per-matchup popup - can reuse this table for a games list they
// assembled themselves, without carrying the full aggregate record along.
export function GamesTable(props: {
  games: HeadToHeadGame[]
  player1: string
  player2: string
}) {
  return (
    <Box>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Games (most recent first)
      </Typography>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>
                <strong>Date</strong>
              </TableCell>
              <TableCell>
                <strong>Map</strong>
              </TableCell>
              <TableCell>
                <strong>Format</strong>
              </TableCell>
              <TableCell align="center">
                <strong>Matchup</strong>
              </TableCell>
              <TableCell>
                <strong>Result</strong>
              </TableCell>
              <TableCell />
            </TableRow>
          </TableHead>
          <TableBody>
            {props.games.map((g) => (
              <GameRow
                key={g.matchId}
                game={g}
                player1={props.player1}
                player2={props.player2}
              />
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

// Mirrors PlayerProfile.tsx's playerFromUrl() - read once at mount (Menu
// unmounts/remounts this page fresh on every navigation, so that's the only
// time it needs to matter) so a link can deep-link straight to a matchup.
function playersFromUrl(): { player1: string | null; player2: string | null } {
  const params = new URLSearchParams(window.location.search)
  return { player1: params.get("player1"), player2: params.get("player2") }
}

export default function HeadToHead() {
  const [players, setPlayers] = React.useState<string[]>([])
  const [player1, setPlayer1] = React.useState<string | null>(
    () => playersFromUrl().player1,
  )
  const [player2, setPlayer2] = React.useState<string | null>(
    () => playersFromUrl().player2,
  )
  const [format, setFormat] = React.useState<GameFormat>("All")
  const [data, setData] = React.useState<HeadToHeadDetail | null>(null)
  const [loading, setLoading] = React.useState(false)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    Client.getPlayerGameCountsApiPlayerGameCountsGet()
      .then((counts: PlayerGameCount[]) =>
        setPlayers(counts.map((c) => c.name)),
      )
      .catch(showError)
  }, [showError])

  React.useEffect(() => {
    if (!player1 || !player2 || player1 === player2) {
      setData(null)
      return
    }
    let cancelled = false
    setLoading(true)
    Client.getPlayerHeadToHeadApiPlayerHeadToHeadGet({
      player1,
      player2,
      gameFormat: format === "All" ? undefined : format,
    })
      .then((d) => !cancelled && setData(d))
      .catch((e) => {
        if (!cancelled) {
          setData(null)
          showError(e)
        }
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [player1, player2, format, showError])

  return (
    <Paper sx={{ p: 2, maxWidth: 1400 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Head to Head
      </Typography>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        sx={{
          alignItems: "center",
          mb: 2,
        }}
      >
        <Autocomplete
          options={players}
          value={player1}
          onChange={(_, v) => setPlayer1(v)}
          sx={{ minWidth: 200, flex: 1 }}
          renderInput={(params) => (
            <TextField {...params} label="Player 1" size="small" />
          )}
        />
        <Typography
          variant="h6"
          sx={{
            color: "text.secondary",
          }}
        >
          vs
        </Typography>
        <Autocomplete
          options={players}
          value={player2}
          onChange={(_, v) => setPlayer2(v)}
          sx={{ minWidth: 200, flex: 1 }}
          renderInput={(params) => (
            <TextField {...params} label="Player 2" size="small" />
          )}
        />
        <ToggleButtonGroup
          value={format}
          exclusive
          onChange={(_, v) => v && setFormat(v)}
          size="small"
        >
          {FORMAT_OPTIONS.map((f) => (
            <ToggleButton key={f} value={f}>
              {f}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Stack>
      {player1 && player2 && player1 === player2 && (
        <Typography
          sx={{
            color: "text.secondary",
          }}
        >
          Pick two different players.
        </Typography>
      )}
      {loading && <Loading />}
      {!loading && data && data.games.length === 0 && (
        <Typography
          sx={{
            color: "text.secondary",
          }}
        >
          No head-to-head games found for {data.player1} vs {data.player2}
          {format === "All" ? "" : ` in ${format}`}.
        </Typography>
      )}
      {!loading && data && data.games.length > 0 && (
        <>
          <Scoreboard data={data} />
          <Grid container spacing={3} sx={{ mb: 3 }}>
            <Grid size={{ xs: 12, md: 4 }}>
              <MapBreakdown
                records={data.byMap}
                player1={data.player1}
                player2={data.player2}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 4 }}>
              <GeneralBreakdown
                player={data.player1}
                records={data.player1ByGeneral}
              />
            </Grid>
            <Grid size={{ xs: 12, sm: 6, md: 4 }}>
              <GeneralBreakdown
                player={data.player2}
                records={data.player2ByGeneral}
              />
            </Grid>
          </Grid>
          <GamesTable
            games={data.games}
            player1={data.player1}
            player2={data.player2}
          />
        </>
      )}
      {errorSnackbar}
    </Paper>
  )
}
