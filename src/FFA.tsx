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
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Tooltip from "@mui/material/Tooltip"
import Chip from "@mui/material/Chip"
import Typography from "@mui/material/Typography"
import { useTheme } from "@mui/material/styles"
import useMediaQuery from "@mui/material/useMediaQuery"
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined"
import { useQuery } from "@tanstack/react-query"
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

import Page from "./Page"
import QueryState from "./QueryState"
import { PlayerLabel } from "./PlayerChip"
import WinRateChip from "./WinRateChip"
import WinRateRadar from "./WinRateRadar"
import DisplayGeneral from "./Generals"
import { toGeneralName } from "./general_utils"
import type { FFAStats, FFAPlayerStat } from "./api"
import { Client } from "./Client"
import { CHART_PALETTE } from "./theme"

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

/** AI rows have no player profile to navigate to, so they read as plain text. */
function LeaderboardName(props: { player: FFAPlayerStat; bold: boolean }) {
  const { player, bold } = props
  if (!player.isCpu) {
    return <PlayerLabel name={player.name} bold={bold} />
  }
  return (
    <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
      <Typography
        variant="body2"
        sx={{ fontWeight: bold ? 700 : 500, color: "text.secondary" }}
      >
        {player.name}
      </Typography>
      <Chip label="AI" size="small" variant="outlined" sx={{ height: 18 }} />
    </Stack>
  )
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
        <InfoTip title="Free-for-all record per player (min 8 FFA games). Dominance compares actual wins to the wins you'd expect if every player in each game were equally likely to win (1/N): 1.0 is exactly average, above 1 means you win more FFAs than your share of the field." />
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
                  <LeaderboardName player={p} bold={i < 3} />
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
                height="auto"
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

// --- Field toggle ---------------------------------------------------------

// Two corpora, not a display filter: the choice goes to the server, which
// re-derives every number over the games it selects. "All FFA" counts the AI
// slots as real entrants (they size the field, and they can win), so a human's
// dominance there is measured against a field that included the AIs.
const FIELDS = ["Humans only", "All FFA"] as const
type Field = (typeof FIELDS)[number]

function FieldToggle(props: {
  value: Field
  onChange: (value: Field) => void
}) {
  return (
    <>
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Field:
      </Typography>
      <ToggleButtonGroup
        value={props.value}
        exclusive
        size="small"
        onChange={(_, next: Field | null) =>
          next !== null && props.onChange(next)
        }
      >
        {FIELDS.map((option) => (
          <ToggleButton key={option} value={option}>
            {option}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
      <InfoTip title="Humans only counts free-for-alls with no AI in them. All FFA adds the games that had AI players, counting each AI as a full entrant: it sizes the field, holds its own leaderboard row, and a game an AI won is that AI's win." />
    </>
  )
}

export default function DisplayFFAStats() {
  const [field, setField] = React.useState<Field>("Humans only")
  const query = useQuery({
    queryKey: ["ffaStats", field],
    queryFn: () =>
      Client.getFfaStatsApiFfastatsGet({ includeCpu: field === "All FFA" }),
  })

  // The toggle renders in every state on purpose: an empty result is itself a
  // reason to reach for the other corpus, so it must not take the control away.
  const actions = <FieldToggle value={field} onChange={setField} />

  return (
    <Page
      title="Free-For-All"
      description="Every player for themselves. Team games and comp-stomps are counted elsewhere."
      actions={actions}
    >
      <QueryState query={query} what="free-for-all stats">
        {(stats) =>
          stats.totalGames === 0 ? (
            <>
              <Typography variant="h6">No FFA games found yet.</Typography>
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                Free-for-all games (3+ players, every player for themselves)
                will show up here once they&apos;ve been played.
              </Typography>
            </>
          ) : (
            <>
              <SummaryCards stats={stats} />
              <Divider sx={{ mb: 2 }} />
              <PlayerLeaderboard players={stats.playerStats} />
              <Divider sx={{ mb: 2 }} />
              <GeneralWinRates stats={stats} />
              <Divider sx={{ mb: 2 }} />
              <MapBreakdown stats={stats} />
            </>
          )
        }
      </QueryState>
    </Page>
  )
}
