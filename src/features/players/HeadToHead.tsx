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
import {
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
} from "recharts"
import type {
  HeadToHeadDetail,
  HeadToHeadGame,
  HeadToHeadGeneralRecord,
  HeadToHeadMapRecord,
  PlayerGameCount,
} from "../../api"
import { PlayersClient } from "../../clients/players"
import { ProfileClient } from "../../clients/profile"
import FormatToggle, { ALL_FORMATS } from "../../components/FormatToggle"
import DisplayGeneral from "../../components/Generals"
import Page from "../../components/Page"
import PlayerChip from "../../components/PlayerChip"
import QueryState from "../../components/QueryState"
import WinRateChip from "../../components/WinRateChip"
import WinShareBar from "../../components/WinShareBar"
import { toGeneralName } from "../../lib/general_utils"
import { usePlayerPalette } from "../../lib/PlayerColorsContext"
import { useUrlChoice, useUrlParam } from "../../lib/useUrlState"
import { displayMapName, formatCash, formatPercent } from "../../lib/utils"
import ShowMatchDetails from "../games/ShowMatchDetails"

const FORMAT_OPTIONS = ALL_FORMATS
type GameFormat = (typeof FORMAT_OPTIONS)[number]

// Phones only, leaving the theme's own responsive sizes alone above that.
const PHONE = "@media (max-width: 599.95px)"

// Long names wrap inside their half instead of pushing the score off-screen.
const NAME_SX = {
  fontWeight: "bold",
  overflowWrap: "anywhere",
  [PHONE]: { fontSize: "1.1rem" },
} as const

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
        <Box sx={{ flex: 1, minWidth: 0, textAlign: "left" }}>
          <Typography variant="h5" sx={{ ...NAME_SX, color: c1 }}>
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
          sx={{
            fontWeight: "bold",
            whiteSpace: "nowrap",
            [PHONE]: { fontSize: "2rem" },
          }}
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
        <Box sx={{ flex: 1, minWidth: 0, textAlign: "right" }}>
          <Typography variant="h5" sx={{ ...NAME_SX, color: c2 }}>
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

// Below this, one side's rate on a general in the matchup is mostly noise.
const H2H_RADAR_MIN_GAMES = 3
// Same floor as the profile page's radar.
const PROFILE_RADAR_MIN_GAMES = 5

type GeneralRecord = { general: number; wins: number; losses: number }

// Both players' per-general win rates overlaid in their colors. Only generals
// both sides have played enough get an axis, so every point on the shape is a
// real rate rather than a missing one drawn as 0%.
function GeneralRadar(props: {
  title: string
  player1: string
  player2: string
  records1: GeneralRecord[]
  records2: GeneralRecord[]
  minGames: number
}) {
  const { player1, player2, minGames } = props
  // Raw hue for the fill, ink for the outline: a yellow line vanishes on white.
  const p1 = usePlayerPalette(player1)
  const p2 = usePlayerPalette(player2)
  const byGeneral2 = new Map(props.records2.map((r) => [r.general, r]))
  const rows = props.records1
    .flatMap((r1) => {
      const r2 = byGeneral2.get(r1.general)
      if (r2 == null) return []
      if (r1.wins + r1.losses < minGames) return []
      if (r2.wins + r2.losses < minGames) return []
      return [
        {
          general: r1.general,
          name: toGeneralName(r1.general),
          p1: Math.round((100 * r1.wins) / (r1.wins + r1.losses)),
          p2: Math.round((100 * r2.wins) / (r2.wins + r2.losses)),
        },
      ]
    })
    .sort((a, b) => a.general - b.general)
  if (rows.length < 3) return null
  return (
    <Box>
      <Typography variant="subtitle1" sx={{ mb: 1, textAlign: "center" }}>
        {props.title}
      </Typography>
      <ResponsiveContainer width="99%" aspect={1}>
        <RadarChart data={rows} outerRadius="72%">
          <PolarGrid />
          <PolarAngleAxis dataKey="name" tick={{ fontSize: 11 }} />
          <PolarRadiusAxis domain={[0, 100]} tick={false} axisLine={false} />
          <Radar
            dataKey="p1"
            name={player1}
            fill={p1.dot}
            fillOpacity={0.25}
            stroke={p1.ink}
            strokeWidth={2}
          />
          <Radar
            dataKey="p2"
            name={player2}
            fill={p2.dot}
            fillOpacity={0.25}
            stroke={p2.ink}
            strokeWidth={2}
            strokeDasharray="4 3"
          />
          <Tooltip formatter={(value, name) => [`${value}%`, name]} />
        </RadarChart>
      </ResponsiveContainer>
    </Box>
  )
}

// Each player's win rate by general across all their games, as their profile
// radar draws it. Shares the profile page's query key, so it's one cache entry.
function OverallGeneralRadar(props: { player1: string; player2: string }) {
  const profile = (player: string) => ({
    queryKey: ["playerProfile", player],
    queryFn: () =>
      ProfileClient.getPlayerProfileApiPlayerProfileGet({ player }),
  })
  const q1 = useQuery(profile(props.player1))
  const q2 = useQuery(profile(props.player2))
  // Secondary panel: a player without a profile just means no overall shape.
  if (q1.data == null || q2.data == null) return null
  return (
    <GeneralRadar
      title="Win rate by general, all games"
      player1={props.player1}
      player2={props.player2}
      records1={q1.data.generals}
      records2={q2.data.generals}
      minGames={PROFILE_RADAR_MIN_GAMES}
    />
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
}) {
  const { game } = props
  const [open, setOpen] = React.useState(false)
  const winnerName = game.player1Won ? props.player1 : props.player2
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
          <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
            <PlayerChip name={winnerName} />
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              won
            </Typography>
          </Stack>
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

export default function HeadToHead() {
  // Both sides live in the URL, so a matchup is a link — which is what the
  // "Nemesis" cards and the ratings table point at. See useUrlState.
  const [player1, setPlayer1] = useUrlParam("player1")
  const [player2, setPlayer2] = useUrlParam("player2")
  const [format, setFormat] = useUrlChoice<GameFormat>(
    "format",
    FORMAT_OPTIONS,
    "All",
  )

  const { data: players = [] } = useQuery({
    queryKey: ["playerGameCounts"],
    queryFn: async () => {
      const counts: PlayerGameCount[] =
        await PlayersClient.getPlayerGameCountsApiPlayerGameCountsGet()
      return counts.map((c) => c.name)
    },
  })

  // A matchup needs two different people; until then there is nothing to ask
  // for, and the empty state below says so.
  const bothPicked = Boolean(player1 && player2 && player1 !== player2)
  const query = useQuery({
    queryKey: ["headToHead", player1, player2, format],
    queryFn: () =>
      PlayersClient.getPlayerHeadToHeadApiPlayerHeadToHeadGet({
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
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <GeneralBreakdown
            player={data.player1}
            records={data.player1ByGeneral}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <GeneralRadar
            title="Win rate by general, head to head"
            player1={data.player1}
            player2={data.player2}
            records1={data.player1ByGeneral}
            records2={data.player2ByGeneral}
            minGames={H2H_RADAR_MIN_GAMES}
          />
        </Grid>
        <Grid size={{ xs: 12, sm: 6, md: 4 }}>
          <GeneralBreakdown
            player={data.player2}
            records={data.player2ByGeneral}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <MapBreakdown
            records={data.byMap}
            player1={data.player1}
            player2={data.player2}
          />
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          <OverallGeneralRadar player1={data.player1} player2={data.player2} />
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
