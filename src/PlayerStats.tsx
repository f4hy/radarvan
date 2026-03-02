import Box from "@mui/material/Box"
import Loading from "./Loading"
import Divider from "@mui/material/Divider"
import Grid from "@mui/material/Grid"
import List from "@mui/material/List"
import ListItem from "@mui/material/ListItem"
import ListItemAvatar from "@mui/material/ListItemAvatar"
import ListItemText from "@mui/material/ListItemText"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined"
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
import { isDebug, winRate } from "./utils"
import { useErrorSnackbar } from "./useErrorSnackbar"

function getPlayerStats(
  callback: (m: PlayerStats) => void,
  onError = console.error,
) {
  Client.getPlayerStatsApiPlayerstatsGet().then(callback).catch(onError)
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

function PlayerListItem(props: { general: General; winLoss: WinLoss }) {
  return (
    <ListItem>
      <ListItemAvatar>
        <DisplayGeneral general={props.general} />
      </ListItemAvatar>
      <ListItemText
        primary={`${toGeneralName(props.general)} [${props.winLoss?.wins ?? 0}:${
          props.winLoss?.losses ?? 0
        }]`}
      />
    </ListItem>
  )
}
function DisplayPlayerStat(props: {
  stat: PlayerStat
  max: number
  debug: boolean
}) {
  const sorted = props.stat.stats
  let total_wins = 0
  let total_games = 0
  const data = Object.entries(sorted).map(([general, winLoss]) => {
    const wins = winLoss?.wins ?? 0
    total_wins += wins
    const losses = winLoss?.losses ?? 0
    const tot = wins + losses
    total_games += tot
    const rate = (wins / (tot > 0 ? tot : 1)) * 100
    return {
      general: toGeneralName(toGeneral(general)) + ":" + rate.toFixed() + "%",
      wins: wins,
      losses: losses,
    }
  })
  const win_rate = (total_wins / total_games) * 100
  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={3}>
        <Grid item xs={12} md={2}>
          <Typography variant="h3">{props.stat.playerName}</Typography>
          {props.debug && (
            <Typography variant="h5">
              {total_wins}/{total_games} {win_rate.toFixed(1)}%
            </Typography>
          )}
          <List>
            {Object.entries(sorted).map(([general, winLoss]) => (
              <PlayerListItem
                key={general}
                general={toGeneral(general)}
                winLoss={winLoss}
              />
            ))}
          </List>
        </Grid>
        <Grid item xs={12} md={10}>
          <ResponsiveContainer width="99%">
            <BarChart data={data} layout="horizontal">
              <CartesianGrid strokeDasharray="5 5" vertical={false} />
              <Bar dataKey="wins" fill="#42A5F5" />
              <Bar dataKey="losses" fill="#FF7043" />
              <XAxis
                dataKey="general"
                height={130}
                angle={60}
                minTickGap={0}
                interval={0}
              />
              <YAxis domain={[0, props.max]} />
              <RechartsTooltip cursor={false} />
            </BarChart>
          </ResponsiveContainer>
        </Grid>
      </Grid>
    </Box>
  )
}

const MIN_GAMES_FOR_BEST = 8

const RANK_MEDALS = ["🥇", "🥈", "🥉"]

function BestPlayerPerGeneral(props: { playerStats: PlayerStats }) {
  type BestEntry = {
    playerName: string
    winRate: number
    wins: number
    losses: number
  }
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

  const entries = Array.from(generalMap.entries())
    .sort((a, b) => a[0] - b[0])
    .map(
      ([generalNum, list]) =>
        [
          generalNum,
          list.sort((a, b) => b.winRate - a.winRate).slice(0, 3),
        ] as const,
    )

  return (
    <Box sx={{ mb: 2 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
        <Typography variant="h5">Best Player Per General</Typography>
        <Tooltip
          title={`Only players with at least ${MIN_GAMES_FOR_BEST} games on a general are shown`}
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
            <Grid key={generalNum} item>
              <Paper
                sx={{ p: 1, textAlign: "center", minWidth: 110 }}
                variant="outlined"
              >
                <DisplayGeneral general={general} />
                <Typography variant="caption" display="block">
                  {toGeneralName(general)}
                </Typography>
                {topPlayers.map((player, rank) => (
                  <Box key={player.playerName} sx={{ mt: 0.5 }}>
                    <Typography
                      variant="body2"
                      fontWeight={rank === 0 ? "bold" : "normal"}
                    >
                      {RANK_MEDALS[rank]} {player.playerName}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {(player.winRate * 100).toFixed(0)}% ({player.wins}W-
                      {player.losses}L)
                    </Typography>
                  </Box>
                ))}
              </Paper>
            </Grid>
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

  const entries = Array.from(generalMap.entries())
    .sort((a, b) => a[0] - b[0])
    .map(
      ([generalNum, list]) =>
        [
          generalNum,
          list.sort((a, b) => b.relativeDiff - a.relativeDiff).slice(0, 3),
        ] as const,
    )

  return (
    <Box sx={{ mb: 2 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
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
            <Grid key={generalNum} item>
              <Paper
                sx={{ p: 1, textAlign: "center", minWidth: 110 }}
                variant="outlined"
              >
                <DisplayGeneral general={general} />
                <Typography variant="caption" display="block">
                  {toGeneralName(general)}
                </Typography>
                {topPlayers.map((player, rank) => {
                  const diffSign = player.relativeDiff >= 0 ? "+" : ""
                  return (
                    <Box key={player.playerName} sx={{ mt: 0.5 }}>
                      <Tooltip
                        title={`Overall win rate: ${(player.overallWinRate * 100).toFixed(0)}%`}
                      >
                        <Typography
                          variant="body2"
                          fontWeight={rank === 0 ? "bold" : "normal"}
                        >
                          {RANK_MEDALS[rank]} {player.playerName}
                        </Typography>
                      </Tooltip>
                      <Typography variant="caption" color="text.secondary">
                        {(player.winRate * 100).toFixed(0)}% ({player.wins}W-
                        {player.losses}L)
                      </Typography>
                      <Typography
                        variant="caption"
                        display="block"
                        color={
                          player.relativeDiff >= 0
                            ? "success.main"
                            : "error.main"
                        }
                      >
                        {diffSign}
                        {(player.relativeDiff * 100).toFixed(0)}% vs their avg
                      </Typography>
                    </Box>
                  )
                })}
              </Paper>
            </Grid>
          )
        })}
      </Grid>
    </Box>
  )
}

function GeneralConsistency(props: { playerStats: PlayerStats }) {
  type PlayerConsistency = {
    playerName: string
    spread: number
    bestWinRate: number
    bestGeneral: General
    worstWinRate: number
    worstGeneral: General
    qualifyingCount: number
  }

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

  const ranked = rows.sort((a, b) => a.spread - b.spread)
  if (ranked.length < 2) return null

  const mostConsistent = ranked[0]
  const mostVariable = ranked[ranked.length - 1]

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
        <Typography variant="h6" fontWeight="bold" sx={{ mb: 0.5 }}>
          {props.player.playerName}
        </Typography>
        <Typography
          variant="caption"
          color="text.secondary"
          display="block"
          sx={{ mb: 1.5 }}
        >
          {props.player.spread * 100 < 1
            ? "<1"
            : (props.player.spread * 100).toFixed(0)}
          % spread across {props.player.qualifyingCount} generals
        </Typography>
        <Stack direction="row" justifyContent="center" spacing={3}>
          <Stack alignItems="center" spacing={0.5}>
            <DisplayGeneral general={props.player.bestGeneral} />
            <Typography variant="caption" color="success.main">
              ▲ {toGeneralName(props.player.bestGeneral)}
            </Typography>
          </Stack>
          <Stack alignItems="center" spacing={0.5}>
            <DisplayGeneral general={props.player.worstGeneral} />
            <Typography variant="caption" color="error.main">
              ▼ {toGeneralName(props.player.worstGeneral)}
            </Typography>
          </Stack>
        </Stack>
      </Paper>
    )
  }

  return (
    <Box sx={{ mb: 2 }}>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
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

const empty = { playerStats: [] }

export default function DisplayPlayerStats() {
  const [playerStats, setPlayerStats] = React.useState<PlayerStats>(empty)
  const debug = isDebug()
  const { showError, errorSnackbar } = useErrorSnackbar()
  React.useEffect(() => {
    getPlayerStats(setPlayerStats, showError)
  }, [showError])
  if (playerStats.playerStats.length === 0) {
    return <Loading />
  }
  const maxwl = playerStats.playerStats.reduce(
    (acc, s) =>
      Math.max(
        acc,
        s.factionStats.reduce(
          (ac, x) => Math.max(ac, x.winLoss?.wins ?? 0, x.winLoss?.losses ?? 0),
          0,
        ),
      ),
    0,
  )
  const maxWinLoss = roundUpNearestN(maxwl + 1, 2)
  return (
    <Paper>
      <Typography variant="h4">
        Stats computed only from 1v1 2v2 3v3 and 4v4 games
      </Typography>
      <BestPlayerPerGeneral playerStats={playerStats} />
      <Divider sx={{ mb: 2 }} />
      <BestRelativePlayerPerGeneral playerStats={playerStats} />
      <Divider sx={{ mb: 2 }} />
      <GeneralConsistency playerStats={playerStats} />
      <Divider sx={{ mb: 2 }} />
      {playerStats.playerStats.map((m) => (
        <React.Fragment key={m.playerName}>
          <DisplayPlayerStat stat={m} max={maxWinLoss} debug={debug} />
          <Divider />
        </React.Fragment>
      ))}
      {errorSnackbar}
    </Paper>
  )
}
