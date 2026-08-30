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
import Typography from "@mui/material/Typography"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import type {
  HeadToHeadDetail,
  HeadToHeadGame,
  HeadToHeadGeneralRecord,
  HeadToHeadMapRecord,
  PlayerGameCount,
} from "./api"
import { Client } from "./Client"
import DisplayGeneral from "./Generals"
import { toGeneralName } from "./general_utils"
import FormatToggle, { ALL_FORMATS } from "./FormatToggle"
import Page from "./Page"
import QueryState from "./QueryState"
import ShowMatchDetails from "./ShowMatchDetails"
import { usePlayerPalette } from "./PlayerColorsContext"
import { displayMapName, formatCash, formatPercent } from "./utils"
import WinRateChip from "./WinRateChip"
import WinShareBar from "./WinShareBar"
import { useUrlParam } from "./useUrlState"

const FORMAT_OPTIONS = ALL_FORMATS
type GameFormat = (typeof FORMAT_OPTIONS)[number]

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
  // Their real in-game color, same as their PlayerChip and their profile — but
  // through the palette, so a yellow player's name is legible on white. The
  // raw hue stays on the win-share bar, where it is a fill and not text.
  const p1Palette = usePlayerPalette(player1)
  const p2Palette = usePlayerPalette(player2)
  const c1 = p1Palette.ink
  const c2 = p2Palette.ink
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
          leftColor={p1Palette.dot}
          rightColor={p2Palette.dot}
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
              {formatCash(v1)} destroyed
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
              {formatCash(v2)} destroyed
            </Typography>
          </Stack>
          <Box sx={{ mt: 0.5 }}>
            <WinShareBar
              fraction={valueShare1}
              leftColor={p1Palette.dot}
              rightColor={p2Palette.dot}
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
  const { ink } = usePlayerPalette(props.player)
  if (props.records.length === 0) return null
  return (
    <Box>
      <Typography variant="subtitle1" sx={{ color: ink, mb: 1 }}>
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
  const c1 = usePlayerPalette(props.player1).ink
  const c2 = usePlayerPalette(props.player2).ink
  if (props.records.length === 0) return null
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
  color1: string
  color2: string
}) {
  const { game } = props
  const [open, setOpen] = React.useState(false)
  const winnerName = game.player1Won ? props.player1 : props.player2
  const winnerColor = game.player1Won ? props.color1 : props.color2
  return (
    <>
      <TableRow
        hover
        sx={{ "& > *": { borderBottom: open ? "unset" : undefined } }}
      >
        {/* Rendered in the viewer's own timezone, not UTC-truncated:
            toISOString() dates a 9pm US game as the next day. Same reasoning as
            Matches.tsx:MatchDateSummary and GameNight.tsx:localDate. */}
        <TableCell sx={{ whiteSpace: "nowrap" }}>
          {game.date.toLocaleDateString("en-CA")}
        </TableCell>
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
  // Constant for the whole table, so they are resolved here rather than per row.
  const color1 = usePlayerPalette(props.player1).ink
  const color2 = usePlayerPalette(props.player2).ink
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
                color1={color1}
                color2={color2}
              />
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default function HeadToHead() {
  // Both sides live in the URL, so a matchup is a link — which is what the
  // "Nemesis" cards and the ratings table point at. See useUrlState.
  const [player1, setPlayer1] = useUrlParam("player1")
  const [player2, setPlayer2] = useUrlParam("player2")
  const [format, setFormat] = React.useState<GameFormat>("All")

  const { data: players = [] } = useQuery({
    queryKey: ["playerGameCounts"],
    queryFn: async () => {
      const counts: PlayerGameCount[] =
        await Client.getPlayerGameCountsApiPlayerGameCountsGet()
      return counts.map((c) => c.name)
    },
  })

  // A matchup needs two different people; until then there is nothing to ask
  // for, and the empty state below says so.
  const bothPicked = Boolean(player1 && player2 && player1 !== player2)
  const query = useQuery({
    queryKey: ["headToHead", player1, player2, format],
    queryFn: () =>
      Client.getPlayerHeadToHeadApiPlayerHeadToHeadGet({
        player1: player1 as string,
        player2: player2 as string,
        gameFormat: format === "All" ? undefined : format,
      }),
    enabled: bothPicked,
  })

  return (
    <Page
      title="Head to Head"
      description="Two players' record against each other, split by map and by general, with every game they have played on opposite sides."
    >
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
        <FormatToggle
          options={FORMAT_OPTIONS}
          value={format}
          onChange={setFormat}
        />
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
      {bothPicked && (
        <QueryState query={query} what="this matchup">
          {(data) => <MatchupResults data={data} format={format} />}
        </QueryState>
      )}
    </Page>
  )
}

function MatchupResults(props: { data: HeadToHeadDetail; format: GameFormat }) {
  const { data, format } = props
  if (data.games.length === 0) {
    return (
      <Typography sx={{ color: "text.secondary" }}>
        No head-to-head games found for {data.player1} vs {data.player2}
        {format === "All" ? "" : ` in ${format}`}.
      </Typography>
    )
  }
  return (
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
  )
}
