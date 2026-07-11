import Box from "@mui/material/Box"
import Divider from "@mui/material/Divider"
import Grid from "@mui/material/Grid"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TableSortLabel from "@mui/material/TableSortLabel"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import { useTheme } from "@mui/material/styles"
import useMediaQuery from "@mui/material/useMediaQuery"
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined"
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts"

import Loading from "./Loading"
import WinRateChip from "./WinRateChip"
import WinRateRadar from "./WinRateRadar"
import DisplayGeneral from "./Generals"
import { toGeneralName } from "./general_utils"
import { FFAStats, FFAPlayerStat } from "./api"
import { Client } from "./Client"
import { useErrorSnackbar } from "./useErrorSnackbar"
import { CHART_PALETTE } from "./theme"

const empty: FFAStats = {
  totalGames: 0,
  distinctPlayers: 0,
  avgPlayersPerGame: 0,
  mostRecent: null,
  playerStats: [],
  generalStats: [],
  mapStats: [],
}

function InfoTip(props: { title: string }) {
  return (
    <Tooltip title={props.title}>
      <InfoOutlinedIcon
        fontSize="small"
        sx={{ color: "text.secondary", cursor: "default" }}
      />
    </Tooltip>
  )
}

function StatCard(props: { label: string; value: string; hint?: string }) {
  return (
    <Paper
      variant="outlined"
      sx={{ p: 2, textAlign: "center", height: "100%" }}
    >
      <Typography
        variant="h4"
        sx={{
          fontWeight: "bold",
        }}
      >
        {props.value}
      </Typography>
      <Typography
        variant="subtitle2"
        sx={{
          color: "text.secondary",
        }}
      >
        {props.label}
      </Typography>
      {props.hint && (
        <Typography
          variant="caption"
          sx={{
            color: "text.disabled",
            display: "block",
          }}
        >
          {props.hint}
        </Typography>
      )}
    </Paper>
  )
}

function SummaryCards(props: { stats: FFAStats }) {
  const s = props.stats
  return (
    <Grid container spacing={2} sx={{ mb: 2 }}>
      <Grid size={{ xs: 6, md: 3 }}>
        <StatCard label="FFA Games" value={s.totalGames.toLocaleString()} />
      </Grid>
      <Grid size={{ xs: 6, md: 3 }}>
        <StatCard label="Players" value={s.distinctPlayers.toLocaleString()} />
      </Grid>
      <Grid size={{ xs: 6, md: 3 }}>
        <StatCard
          label="Avg Players / Game"
          value={s.avgPlayersPerGame.toFixed(1)}
        />
      </Grid>
      <Grid size={{ xs: 6, md: 3 }}>
        <StatCard
          label="Most Recent FFA"
          value={s.mostRecent?.winner ?? "—"}
          hint={s.mostRecent ? `Match #${s.mostRecent.matchId}` : undefined}
        />
      </Grid>
    </Grid>
  )
}

// --- Player leaderboard ---------------------------------------------------

type SortKey = "wins" | "games" | "winRate" | "dominance"

const SORT_LABELS: Record<SortKey, string> = {
  wins: "Wins",
  games: "Games",
  winRate: "Win Rate",
  dominance: "Dominance",
}

function dominanceColor(d: number): string {
  if (d >= 1.25) return "success.main"
  if (d <= 0.75) return "error.main"
  return "text.primary"
}

function PlayerLeaderboard(props: { players: FFAPlayerStat[] }) {
  const [sortKey, setSortKey] = React.useState<SortKey>("wins")

  const rows = React.useMemo(() => {
    const sorted = [...props.players]
    sorted.sort((a, b) => {
      const primary = b[sortKey] - a[sortKey]
      // Tie-break on games so a 1/1 player doesn't top a 40/80 player.
      return primary !== 0 ? primary : b.games - a.games
    })
    return sorted
  }, [props.players, sortKey])

  const handleSort = (key: SortKey) => () => setSortKey(key)

  return (
    <Box sx={{ mb: 2 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          mb: 1,
        }}
      >
        <Typography variant="h5">Player Leaderboard</Typography>
        <InfoTip title="Free-for-all record per player (min 3 FFA games). Dominance compares actual wins to the wins you'd expect if every player in each game were equally likely to win (1/N): 1.0 is exactly average, above 1 means you win more FFAs than your share of the field." />
      </Stack>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell>
                <strong>#</strong>
              </TableCell>
              <TableCell>
                <strong>Player</strong>
              </TableCell>
              {(["games", "wins", "winRate", "dominance"] as SortKey[]).map(
                (key) => (
                  <TableCell key={key} align="right" sortDirection="desc">
                    <TableSortLabel
                      active={sortKey === key}
                      direction="desc"
                      onClick={handleSort(key)}
                    >
                      <strong>{SORT_LABELS[key]}</strong>
                    </TableSortLabel>
                  </TableCell>
                ),
              )}
            </TableRow>
          </TableHead>
          <TableBody>
            {rows.map((p, i) => (
              <TableRow key={p.name} hover>
                <TableCell>{i + 1}</TableCell>
                <TableCell>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: i < 3 ? 700 : 400,
                    }}
                  >
                    {p.name}
                  </Typography>
                </TableCell>
                <TableCell align="right">{p.games}</TableCell>
                <TableCell align="right">{p.wins}</TableCell>
                <TableCell align="right">
                  <WinRateChip wins={p.wins} losses={p.games - p.wins} />
                </TableCell>
                <TableCell align="right">
                  <Tooltip title={`Expected ${p.expectedWins.toFixed(1)} wins`}>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: 600,
                        color: dominanceColor(p.dominance),
                      }}
                    >
                      {p.dominance.toFixed(2)}×
                    </Typography>
                  </Tooltip>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

// --- Generals -------------------------------------------------------------

function GeneralWinRates(props: { stats: FFAStats }) {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"))

  const sorted = React.useMemo(
    () => [...props.stats.generalStats].sort((a, b) => b.winRate - a.winRate),
    [props.stats.generalStats],
  )

  const barData = React.useMemo(
    () =>
      sorted.map((g) => ({
        name: toGeneralName(g.general),
        rate: Math.round(g.winRate * 100),
        games: g.games,
        wins: g.wins,
      })),
    [sorted],
  )

  const radarData = React.useMemo(
    () =>
      props.stats.generalStats.map((g) => ({
        name: toGeneralName(g.general),
        winRate: Math.round(g.winRate * 100),
      })),
    [props.stats.generalStats],
  )

  if (sorted.length === 0) return null

  return (
    <Box sx={{ mb: 2 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          mb: 1,
        }}
      >
        <Typography variant="h5">General Win Rates in FFA</Typography>
        <InfoTip title="Win rate of each general across FFA games. Note the expected rate is roughly 1 / (players per game), so a general above the field average is genuinely strong in the chaos of a free-for-all." />
      </Stack>
      <Grid
        container
        spacing={2}
        sx={{
          alignItems: "center",
        }}
      >
        <Grid size={{ xs: 12, md: 7 }}>
          <ResponsiveContainer width="99%" height={isMobile ? 320 : 400}>
            <BarChart
              data={barData}
              margin={{ top: 20, right: 10, left: 0, bottom: 60 }}
            >
              <CartesianGrid strokeDasharray="5 5" vertical={false} />
              <Bar dataKey="rate" name="Win %">
                {barData.map((entry, i) => (
                  <Cell
                    key={entry.name}
                    fill={CHART_PALETTE[i % CHART_PALETTE.length]}
                  />
                ))}
                <LabelList
                  dataKey="rate"
                  position="top"
                  fontSize={11}
                  formatter={(v) => `${v}%`}
                />
              </Bar>
              <XAxis
                dataKey="name"
                angle={-35}
                textAnchor="end"
                interval={0}
                tick={{ fontSize: isMobile ? 9 : 12 }}
              />
              <YAxis
                tick={{ fontSize: isMobile ? 9 : 12 }}
                tickFormatter={(v) => `${v}%`}
              />
              <RechartsTooltip
                cursor={false}
                formatter={(value, _name, item) => [
                  `${value}% (${item?.payload?.wins}W / ${item?.payload?.games} games)`,
                  "Win rate",
                ]}
              />
            </BarChart>
          </ResponsiveContainer>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <WinRateRadar data={radarData} aspect={1.2} />
        </Grid>
      </Grid>
      <Grid container spacing={1} sx={{ mt: 1 }}>
        {sorted.map((g) => (
          <Grid key={g.general} size={{ xs: 6, sm: 4, md: 3, lg: 2 }}>
            <Paper variant="outlined" sx={{ p: 1, textAlign: "center" }}>
              <DisplayGeneral general={g.general} />
              <Typography variant="subtitle2" sx={{ mt: 0.5 }}>
                {toGeneralName(g.general)}
              </Typography>
              <WinRateChip wins={g.wins} losses={g.games - g.wins} />
              <Typography
                variant="caption"
                sx={{
                  color: "text.secondary",
                  display: "block",
                }}
              >
                {g.games} games
              </Typography>
            </Paper>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

// --- Maps -----------------------------------------------------------------

function mapBasename(map: string): string {
  const parts = map.split("/")
  return parts[parts.length - 1] || map
}

function MapBreakdown(props: { stats: FFAStats }) {
  if (props.stats.mapStats.length === 0) return null
  return (
    <Box sx={{ mb: 2 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          mb: 1,
        }}
      >
        <Typography variant="h5">Most Played FFA Maps</Typography>
      </Stack>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>
                <strong>Map</strong>
              </TableCell>
              <TableCell align="right">
                <strong>Games</strong>
              </TableCell>
              <TableCell align="right">
                <strong>Avg Players</strong>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {props.stats.mapStats.map((m) => (
              <TableRow key={m.map} hover>
                <TableCell>{mapBasename(m.map)}</TableCell>
                <TableCell align="right">{m.games}</TableCell>
                <TableCell align="right">{m.avgPlayers.toFixed(1)}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

export default function DisplayFFAStats() {
  const [stats, setStats] = React.useState<FFAStats>(empty)
  const [loaded, setLoaded] = React.useState(false)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    setLoaded(false)
    Client.getFfaStatsApiFfastatsGet()
      .then((s) => {
        setStats(s)
        setLoaded(true)
      })
      .catch(showError)
  }, [showError])

  if (!loaded) {
    return <Loading />
  }

  if (stats.totalGames === 0) {
    return (
      <Paper sx={{ p: 3 }}>
        <Typography variant="h6">No FFA games found yet.</Typography>
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
          }}
        >
          Free-for-all games (3+ human players, every player for themselves)
          will show up here once they've been played.
        </Typography>
      </Paper>
    )
  }

  return (
    <Paper sx={{ p: 2 }}>
      <Typography variant="h4" sx={{ mb: 0.5 }}>
        Free-For-All
      </Typography>
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
          mb: 2,
        }}
      >
        Every player for themselves. Stats below cover human FFA games only.
      </Typography>
      <SummaryCards stats={stats} />
      <Divider sx={{ mb: 2 }} />
      <PlayerLeaderboard players={stats.playerStats} />
      <Divider sx={{ mb: 2 }} />
      <GeneralWinRates stats={stats} />
      <Divider sx={{ mb: 2 }} />
      <MapBreakdown stats={stats} />
      {errorSnackbar}
    </Paper>
  )
}
