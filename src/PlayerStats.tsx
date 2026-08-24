import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Collapse from "@mui/material/Collapse"
import IconButton from "@mui/material/IconButton"
import Loading from "./Loading"
import Page from "./Page"
import { PlayerLabel } from "./PlayerChip"
import { useFetch } from "./useFetch"
import Divider from "@mui/material/Divider"
import Grid from "@mui/material/Grid"
import List from "@mui/material/List"
import ListItem from "@mui/material/ListItem"
import ListItemAvatar from "@mui/material/ListItemAvatar"
import ListItemText from "@mui/material/ListItemText"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Tooltip from "@mui/material/Tooltip"
import useMediaQuery from "@mui/material/useMediaQuery"
import { useTheme } from "@mui/material/styles"
import Typography from "@mui/material/Typography"
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import ExpandLessIcon from "@mui/icons-material/ExpandLess"
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip as RechartsTooltip,
  XAxis,
  YAxis,
} from "recharts"
import DisplayGeneral from "./Generals"
import { toGeneralName } from "./general_utils"

import {
  General,
  GeneralFromJSON,
  instanceOfGeneral,
  PlayerStat,
  PlayerStats,
  WinLoss,
} from "./api"
import { Client } from "./Client"
import { useIsAdmin } from "./AuthContext"
import { winRate, wilsonLowerBound } from "./utils"
import { CHART_WIN, CHART_LOSS } from "./theme"
import WinRateRadar from "./WinRateRadar"
import WinRateChip from "./WinRateChip"
import { useErrorSnackbar } from "./useErrorSnackbar"

const FORMAT_OPTIONS = ["All", "2v2", "3v3", "4v4"] as const
type GameFormat = (typeof FORMAT_OPTIONS)[number]

function fetchPlayerStats(gameFormat: GameFormat): Promise<PlayerStats> {
  const params = gameFormat === "All" ? {} : { gameFormat }
  return Client.getPlayerStatsApiPlayerstatsGet(params)
}

function toGeneral(s: string | number): General {
  let num = typeof s === "string" ? parseInt(s) : s
  if (instanceOfGeneral(num)) {
    return GeneralFromJSON(num)
  }
  return General.NUMBER_MINUS_1
}

function roundUpNearestN(num: number, N: number) {
  return Math.ceil(num / N) * N
}

const FORMAT_ORDER = ["total", "1v1", "2v2", "3v3", "4v4"]

function GameCountsTable(props: { playerStats: PlayerStats }) {
  const [open, setOpen] = React.useState(false)

  const columns = React.useMemo(
    () =>
      FORMAT_ORDER.filter((fmt) =>
        props.playerStats.playerStats.some((s) => s.gameCounts?.[fmt] != null),
      ),
    [props.playerStats.playerStats],
  )

  const rows = React.useMemo(
    () =>
      [...props.playerStats.playerStats].sort(
        (a, b) =>
          (b.gameCounts?.["total"] ?? 0) - (a.gameCounts?.["total"] ?? 0),
      ),
    [props.playerStats.playerStats],
  )

  return (
    <Box sx={{ mb: 2 }}>
      <Paper
        variant="outlined"
        onClick={() => setOpen((v) => !v)}
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2,
          py: 1,
          cursor: "pointer",
          userSelect: "none",
          bgcolor: open ? "action.selected" : "action.hover",
          "&:hover": { bgcolor: "action.selected" },
          borderBottomLeftRadius: open ? 0 : undefined,
          borderBottomRightRadius: open ? 0 : undefined,
        }}
      >
        <Typography variant="h6">Game Counts</Typography>
        <Stack
          direction="row"
          spacing={0.5}
          sx={{
            alignItems: "center",
          }}
        >
          <Typography
            variant="caption"
            sx={{
              color: "text.secondary",
            }}
          >
            {open ? "collapse" : "expand"}
          </Typography>
          <IconButton size="small" tabIndex={-1}>
            {open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Stack>
      </Paper>
      <Collapse in={open}>
        <TableContainer
          component={Paper}
          variant="outlined"
          sx={{ borderTop: 0, borderTopLeftRadius: 0, borderTopRightRadius: 0 }}
        >
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>
                  <strong>Player</strong>
                </TableCell>
                {columns.map((fmt) => (
                  <TableCell key={fmt} align="right">
                    <strong>{fmt}</strong>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((s) => (
                <TableRow key={s.playerName} hover>
                  <TableCell>
                    <PlayerLabel name={s.playerName} />
                  </TableCell>
                  {columns.map((fmt) => (
                    <TableCell key={fmt} align="right">
                      {s.gameCounts?.[fmt] ?? 0}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Collapse>
    </Box>
  )
}

function PlayerBanner(props: {
  name: string
  counts: { [key: string]: number } | undefined
  debug: boolean
  totalWins: number
  totalGames: number
}) {
  const entries = FORMAT_ORDER.filter(
    (k) => props.counts != null && props.counts[k] != null,
  ).map((k) => [k, props.counts![k]] as const)
  const winRate =
    props.totalGames > 0
      ? ((props.totalWins / props.totalGames) * 100).toFixed(1)
      : "0"

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 2,
        px: 2,
        py: 1,
        bgcolor: "action.hover",
        borderRadius: 1,
        mb: 1,
      }}
    >
      <Box sx={{ minWidth: 140 }}>
        <PlayerLabel name={props.name} bold variant="h6" />
      </Box>
      {props.debug && (
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
          }}
        >
          {props.totalWins}/{props.totalGames} ({winRate}%)
        </Typography>
      )}
      <Stack
        direction="row"
        spacing={1}
        sx={{
          flexWrap: "wrap",
        }}
      >
        {entries.map(([format, count]) => (
          <Chip
            key={format}
            label={`${format}: ${count}`}
            size="small"
            variant={format === "total" ? "filled" : "outlined"}
          />
        ))}
      </Stack>
    </Box>
  )
}

function PlayerListItem(props: { general: General; winLoss: WinLoss }) {
  const wins = props.winLoss?.wins ?? 0
  const losses = props.winLoss?.losses ?? 0
  return (
    <ListItem disableGutters dense>
      <ListItemAvatar>
        <DisplayGeneral general={props.general} />
      </ListItemAvatar>
      <ListItemText primary={toGeneralName(props.general)} />
      <WinRateChip wins={wins} losses={losses} />
    </ListItem>
  )
}

function DisplayPlayerStat(props: {
  stat: PlayerStat
  max: number
  debug: boolean
  isMobile: boolean
}) {
  const { data, radarData, total_wins, total_games } = React.useMemo(() => {
    let total_wins = 0
    let total_games = 0
    const entries = Object.entries(props.stat.stats).map(
      ([general, winLoss]) => {
        const wins = winLoss?.wins ?? 0
        total_wins += wins
        const losses = winLoss?.losses ?? 0
        total_games += wins + losses
        const wr = winRate(wins, losses)
        const name = toGeneralName(toGeneral(general))
        return { name, wins, losses, wr }
      },
    )
    const data = entries.map(({ name, wins, losses, wr }) => ({
      general: `${name}:${(wr * 100).toFixed()}%`,
      wins,
      losses,
    }))
    const radarData = entries.map(({ name, wr }) => ({
      name,
      winRate: Math.round(wr * 100),
    }))
    return { data, radarData, total_wins, total_games }
  }, [props.stat])
  return (
    <Box sx={{ flexGrow: 1 }}>
      <PlayerBanner
        name={props.stat.playerName}
        counts={props.stat.gameCounts}
        debug={props.debug}
        totalWins={total_wins}
        totalGames={total_games}
      />
      <Grid container spacing={3}>
        <Grid size={{ xs: 12, md: 2 }}>
          <List dense>
            {Object.entries(props.stat.stats).map(([general, winLoss]) => (
              <PlayerListItem
                key={general}
                general={toGeneral(general)}
                winLoss={winLoss}
              />
            ))}
          </List>
        </Grid>
        <Grid size={{ xs: 12, md: 6 }}>
          {/* Explicit height, not the ResponsiveContainer default of "100%":
              stacked on xs this Grid item's own height comes from its content,
              so a percentage height resolves against zero and the chart
              disappears on phones. */}
          <ResponsiveContainer width="99%" height={props.isMobile ? 280 : 340}>
            <BarChart
              data={data}
              layout="horizontal"
              margin={{ top: 8, right: 8, left: 0, bottom: 8 }}
            >
              <CartesianGrid strokeDasharray="5 5" vertical={false} />
              <Bar dataKey="wins" fill={CHART_WIN} name="Wins" />
              <Bar dataKey="losses" fill={CHART_LOSS} name="Losses" />
              {/* angle/textAnchor pair matches every other chart in the app —
                  a positive angle with the default middle anchor drifts each
                  label off the bar it belongs to. */}
              <XAxis
                dataKey="general"
                height="auto"
                angle={-35}
                textAnchor="end"
                minTickGap={0}
                interval={0}
                tick={{ fontSize: props.isMobile ? 9 : 12 }}
              />
              <YAxis
                domain={[0, props.max]}
                tick={{ fontSize: props.isMobile ? 9 : 12 }}
              />
              <RechartsTooltip cursor={false} />
            </BarChart>
          </ResponsiveContainer>
        </Grid>
        <Grid size={{ xs: 12, md: 4 }}>
          <WinRateRadar data={radarData} />
        </Grid>
      </Grid>
    </Box>
  )
}

const MIN_GAMES_FOR_BEST = 8

type PlayerConsistency = {
  playerName: string
  spread: number
  bestWinRate: number
  bestGeneral: General
  worstWinRate: number
  worstGeneral: General
  qualifyingCount: number
}

function ConsistencyCard(props: {
  player: PlayerConsistency
  label: string
  emoji: string
  accentColor: string
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2, flex: 1, textAlign: "center" }}>
      <Typography
        variant="subtitle2"
        color={props.accentColor}
        sx={{ mb: 0.5 }}
      >
        {props.emoji} {props.label}
      </Typography>
      <Typography
        variant="h6"
        sx={{
          fontWeight: "bold",
          mb: 0.5,
        }}
      >
        {props.player.playerName}
      </Typography>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
          display: "block",
          mb: 1.5,
        }}
      >
        {props.player.spread * 100 < 1
          ? "<1"
          : (props.player.spread * 100).toFixed(0)}
        % spread across {props.player.qualifyingCount} generals
      </Typography>
      <Stack
        direction="row"
        spacing={3}
        sx={{
          justifyContent: "center",
        }}
      >
        <Stack
          spacing={0.5}
          sx={{
            alignItems: "center",
          }}
        >
          <DisplayGeneral general={props.player.bestGeneral} />
          <Typography
            variant="caption"
            sx={{
              color: "success.main",
            }}
          >
            ▲ {toGeneralName(props.player.bestGeneral)}
          </Typography>
        </Stack>
        <Stack
          spacing={0.5}
          sx={{
            alignItems: "center",
          }}
        >
          <DisplayGeneral general={props.player.worstGeneral} />
          <Typography
            variant="caption"
            sx={{
              color: "error.main",
            }}
          >
            ▼ {toGeneralName(props.player.worstGeneral)}
          </Typography>
        </Stack>
      </Stack>
    </Paper>
  )
}

function RankedPlayerCard(props: {
  general: General
  children: React.ReactNode
}) {
  return (
    <Grid size={{ xs: 6, sm: 4, md: 3, lg: 2 }}>
      <Paper
        sx={{ p: 1, textAlign: "center", height: "100%" }}
        variant="outlined"
      >
        <DisplayGeneral general={props.general} />
        <Typography
          variant="subtitle2"
          sx={{
            display: "block",
            mt: 0.5,
            mb: 0.5,
          }}
        >
          {toGeneralName(props.general)}
        </Typography>
        <Divider sx={{ mb: 0.5 }} />
        {props.children}
      </Paper>
    </Grid>
  )
}

const RANK_MEDALS = ["🥇", "🥈", "🥉"]

function BestPlayerPerGeneral(props: { playerStats: PlayerStats }) {
  type BestEntry = {
    playerName: string
    winRate: number
    wins: number
    losses: number
  }

  const entries = React.useMemo(() => {
    const generalMap = new Map<number, BestEntry[]>()
    for (const stat of props.playerStats.playerStats) {
      for (const [generalStr, winLoss] of Object.entries(stat.stats)) {
        const generalNum = parseInt(generalStr)
        if (generalNum < 0) continue
        const wins = winLoss?.wins ?? 0
        const losses = winLoss?.losses ?? 0
        const total = wins + losses
        if (total < MIN_GAMES_FOR_BEST) continue
        const list = generalMap.get(generalNum) ?? []
        list.push({
          playerName: stat.playerName,
          winRate: winRate(wins, losses),
          wins,
          losses,
        })
        generalMap.set(generalNum, list)
      }
    }
    return Array.from(generalMap.entries())
      .sort((a, b) => a[0] - b[0])
      .map(
        ([generalNum, list]) =>
          [
            generalNum,
            list
              .sort(
                (a, b) =>
                  wilsonLowerBound(b.wins, b.losses) -
                  wilsonLowerBound(a.wins, a.losses),
              )
              .slice(0, 3),
          ] as const,
      )
  }, [props.playerStats])

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
        <Typography variant="h5">Best Player Per General</Typography>
        <Tooltip
          title={`Only players with at least ${MIN_GAMES_FOR_BEST} games on a general are shown, ranked by the lower bound of the 95% Wilson confidence interval (so a well-sampled win rate beats a lucky small one)`}
        >
          <InfoOutlinedIcon
            fontSize="small"
            sx={{ color: "text.secondary", cursor: "default" }}
          />
        </Tooltip>
      </Stack>
      <Grid container spacing={1}>
        {entries.map(([generalNum, topPlayers]) => {
          const general = toGeneral(generalNum)
          return (
            <RankedPlayerCard key={generalNum} general={general}>
              {topPlayers.map((player, rank) => (
                <Box key={player.playerName} sx={{ mt: 0.5 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: rank === 0 ? "bold" : "normal",
                    }}
                  >
                    {RANK_MEDALS[rank]} {player.playerName}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.secondary",
                    }}
                  >
                    {(player.winRate * 100).toFixed(0)}% ({player.wins}W-
                    {player.losses}L)
                  </Typography>
                </Box>
              ))}
            </RankedPlayerCard>
          )
        })}
      </Grid>
    </Box>
  )
}

function BestRelativePlayerPerGeneral(props: { playerStats: PlayerStats }) {
  type RelativeEntry = {
    playerName: string
    winRate: number
    overallWinRate: number
    relativeDiff: number
    wins: number
    losses: number
  }

  const entries = React.useMemo(() => {
    const playerOverallRate = new Map<string, number>()
    for (const stat of props.playerStats.playerStats) {
      let totalWins = 0
      let totalGames = 0
      for (const winLoss of Object.values(stat.stats)) {
        totalWins += winLoss?.wins ?? 0
        totalGames += (winLoss?.wins ?? 0) + (winLoss?.losses ?? 0)
      }
      if (totalGames > 0) {
        playerOverallRate.set(stat.playerName, totalWins / totalGames)
      }
    }

    const generalMap = new Map<number, RelativeEntry[]>()
    for (const stat of props.playerStats.playerStats) {
      const overallWinRate = playerOverallRate.get(stat.playerName) ?? 0
      for (const [generalStr, winLoss] of Object.entries(stat.stats)) {
        const generalNum = parseInt(generalStr)
        if (generalNum < 0) continue
        const wins = winLoss?.wins ?? 0
        const losses = winLoss?.losses ?? 0
        const total = wins + losses
        if (total < MIN_GAMES_FOR_BEST) continue
        const wr = winRate(wins, losses)
        const relativeDiff = wr - overallWinRate
        const list = generalMap.get(generalNum) ?? []
        list.push({
          playerName: stat.playerName,
          winRate: wr,
          overallWinRate,
          relativeDiff,
          wins,
          losses,
        })
        generalMap.set(generalNum, list)
      }
    }

    return Array.from(generalMap.entries())
      .sort((a, b) => a[0] - b[0])
      .map(
        ([generalNum, list]) =>
          [
            generalNum,
            list.sort((a, b) => b.relativeDiff - a.relativeDiff).slice(0, 3),
          ] as const,
      )
  }, [props.playerStats])

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
        <Typography variant="h5">
          Best Relative Performance Per General
        </Typography>
        <Tooltip
          title={`Shows which player performs best on each general relative to their own overall win rate. Requires at least ${MIN_GAMES_FOR_BEST} games on that general.`}
        >
          <InfoOutlinedIcon
            fontSize="small"
            sx={{ color: "text.secondary", cursor: "default" }}
          />
        </Tooltip>
      </Stack>
      <Grid container spacing={1}>
        {entries.map(([generalNum, topPlayers]) => {
          const general = toGeneral(generalNum)
          return (
            <RankedPlayerCard key={generalNum} general={general}>
              {topPlayers.map((player, rank) => {
                const diffSign = player.relativeDiff >= 0 ? "+" : ""
                return (
                  <Box key={player.playerName} sx={{ mt: 0.5 }}>
                    <Tooltip
                      title={`Overall win rate: ${(player.overallWinRate * 100).toFixed(0)}%`}
                    >
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: rank === 0 ? "bold" : "normal",
                        }}
                      >
                        {RANK_MEDALS[rank]} {player.playerName}
                      </Typography>
                    </Tooltip>
                    <Typography
                      variant="caption"
                      sx={{
                        color: "text.secondary",
                      }}
                    >
                      {(player.winRate * 100).toFixed(0)}% ({player.wins}W-
                      {player.losses}L)
                    </Typography>
                    <Typography
                      variant="caption"
                      color={
                        player.relativeDiff >= 0 ? "success.main" : "error.main"
                      }
                      sx={{
                        display: "block",
                      }}
                    >
                      {diffSign}
                      {(player.relativeDiff * 100).toFixed(0)}% vs their avg
                    </Typography>
                  </Box>
                )
              })}
            </RankedPlayerCard>
          )
        })}
      </Grid>
    </Box>
  )
}

function GeneralConsistency(props: { playerStats: PlayerStats }) {
  const ranked = React.useMemo(() => {
    const rows: PlayerConsistency[] = []
    for (const stat of props.playerStats.playerStats) {
      const qualifying: { general: General; winRate: number }[] = []
      for (const [generalStr, winLoss] of Object.entries(stat.stats)) {
        const generalNum = parseInt(generalStr)
        if (generalNum < 0) continue
        const wins = winLoss?.wins ?? 0
        const losses = winLoss?.losses ?? 0
        const total = wins + losses
        if (total < MIN_GAMES_FOR_BEST) continue
        qualifying.push({
          general: toGeneral(generalNum),
          winRate: winRate(wins, losses),
        })
      }
      if (qualifying.length < 2) continue
      const sorted = qualifying.sort((a, b) => b.winRate - a.winRate)
      const best = sorted[0]
      const worst = sorted[sorted.length - 1]
      rows.push({
        playerName: stat.playerName,
        spread: best.winRate - worst.winRate,
        bestWinRate: best.winRate,
        bestGeneral: best.general,
        worstWinRate: worst.winRate,
        worstGeneral: worst.general,
        qualifyingCount: qualifying.length,
      })
    }
    return rows.sort((a, b) => a.spread - b.spread)
  }, [props.playerStats])

  if (ranked.length < 2) return null

  const mostConsistent = ranked[0]
  const mostVariable = ranked[ranked.length - 1]

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
        <Typography variant="h5">General Consistency</Typography>
        <Tooltip
          title={`Spread between a player's best and worst general win rate. Only generals with at least ${MIN_GAMES_FOR_BEST} games qualify. Players need at least 2 qualifying generals.`}
        >
          <InfoOutlinedIcon
            fontSize="small"
            sx={{ color: "text.secondary", cursor: "default" }}
          />
        </Tooltip>
      </Stack>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
        <ConsistencyCard
          player={mostConsistent}
          label="Most Consistent"
          emoji="🎯"
          accentColor="success.main"
        />
        <ConsistencyCard
          player={mostVariable}
          label="Most Variable"
          emoji="🎲"
          accentColor="error.main"
        />
      </Stack>
    </Box>
  )
}

export default function DisplayPlayerStats() {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"))
  const [format, setFormat] = React.useState<GameFormat>("All")
  const debug = useIsAdmin()
  const { showError, errorSnackbar } = useErrorSnackbar()
  const playerStats = useFetch(
    () => fetchPlayerStats(format),
    [format],
    showError,
  )
  const maxWinLoss = React.useMemo(() => {
    const maxwl = (playerStats?.playerStats ?? []).reduce(
      (acc, s) =>
        Math.max(
          acc,
          s.factionStats.reduce(
            (ac, x) =>
              Math.max(ac, x.winLoss?.wins ?? 0, x.winLoss?.losses ?? 0),
            0,
          ),
        ),
      0,
    )
    return roundUpNearestN(maxwl + 1, 2)
  }, [playerStats])

  if (!playerStats) {
    return <Loading />
  }
  return (
    <Page
      title="Player Stats"
      description="How everyone does with each general, across competitive team games."
      actions={
        <>
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            Game format
          </Typography>
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
        </>
      }
    >
      <GameCountsTable playerStats={playerStats} />
      <Divider sx={{ mb: 2 }} />
      <BestPlayerPerGeneral playerStats={playerStats} />
      <Divider sx={{ mb: 2 }} />
      <BestRelativePlayerPerGeneral playerStats={playerStats} />
      <Divider sx={{ mb: 2 }} />
      <GeneralConsistency playerStats={playerStats} />
      <Divider sx={{ mb: 2 }} />
      {playerStats.playerStats.map((m) => (
        <React.Fragment key={m.playerName}>
          <DisplayPlayerStat
            stat={m}
            max={maxWinLoss}
            debug={debug}
            isMobile={isMobile}
          />
          <Divider />
        </React.Fragment>
      ))}
      {errorSnackbar}
    </Page>
  )
}
