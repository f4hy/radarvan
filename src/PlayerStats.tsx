import Box from "@mui/material/Box"
import Divider from "@mui/material/Divider"
import Grid from "@mui/material/Grid"
import List from "@mui/material/List"
import ListItem from "@mui/material/ListItem"
import ListItemAvatar from "@mui/material/ListItemAvatar"
import ListItemText from "@mui/material/ListItemText"
import Paper from "@mui/material/Paper"
import Typography from "@mui/material/Typography"
import _ from "lodash"
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Line,
  LineChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import DisplayGeneral from "./Generals"
import {
  Faction,
  General,
  GeneralWL,
  PlayerRateOverTime,
  PlayerStat,
  PlayerStats,
  WinLoss,
  DateMessage,
} from "./proto/match"

function getPlayerStats(callback: (m: PlayerStats) => void) {
  fetch("/api/playerstats").then((r) =>
    r
      .blob()
      .then((b) => b.arrayBuffer())
      .then((j) => {
        const a = new Uint8Array(j)
        const playerStats = PlayerStats.decode(a)
        callback(playerStats)
      }),
  )
}

function roundUpNearestN(num: number, N: number) {
  return Math.ceil(num / N) * N
}

function PlayerListItem(props: { playerStatWL: GeneralWL }) {
  const p = props.playerStatWL
  return (
    <ListItem>
      <ListItemAvatar>
        <DisplayGeneral general={p.general} />
      </ListItemAvatar>
      <ListItemText
        primary={`${General[p.general]}:(${p.winLoss?.wins ?? 0}:${
          p.winLoss?.losses ?? 0
        })`}
      />
    </ListItem>
  )
}
function pad(n: number): string {
  return n.toString().padStart(2, "0")
}

function datemsgtoString(datemsg: DateMessage | undefined) {
  if (datemsg) {
    return `${datemsg.Year}-${pad(datemsg.Month)}-${pad(datemsg.Day)}`
  }
  return "unknown"
}

function rate(wl: WinLoss | undefined): number {
  if (wl) {
    return (100 * wl.wins) / (wl.losses + wl.wins)
  }
  return 0
}

function GeneralStatOverTime(props: { ot: PlayerRateOverTime[] }) {
  const grouped = Object.entries(_.groupBy(props.ot, (x) => x.wl?.general))
  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container rowSpacing={3}>
        {grouped.map(([g, data]) => (
          <Grid item xs={12} lg={3}>
            <DisplayGeneral general={+g} />
            <ResponsiveContainer width="99%" height={150}>
              <LineChart
                data={data.map((d) => ({
                  date: datemsgtoString(d.date),
                  rate: rate(d.wl?.winLoss),
                }))}
                margin={{
                  top: 5,
                  right: 30,
                  left: 20,
                  bottom: 5,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="date" type="category" />
                <YAxis domain={[0, 100]} type="number" />
                <Tooltip formatter={(v) => (v as number).toFixed(2) + "%"} />
                <Line dataKey="rate" strokeWidth={3} />
              </LineChart>
            </ResponsiveContainer>
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

function DisplayPlayerStat(props: { stat: PlayerStat; max: number }) {
  const sorted = props.stat.stats.sort((s1, s2) => s1.general - s2.general)
  const data = sorted.map((p) => {
    const wins = p.winLoss?.wins ?? 0
    const losses = p.winLoss?.losses ?? 0
    const tot = wins + losses
    const rate = (wins / (tot > 0 ? tot : 1)) * 100
    return {
      general: General[p.general] + ":" + rate.toFixed() + "%",
      wins: wins,
      losses: losses,
    }
  })
  const faction_sorted = props.stat.factionStats.sort(
    (s1, s2) => s1.faction - s2.faction,
  )
  const faction_data = faction_sorted.map((p) => {
    const wins = p.winLoss?.wins ?? 0
    const losses = p.winLoss?.losses ?? 0
    const tot = wins + losses
    const rate = (wins / (tot > 0 ? tot : 1)) * 100
    return {
      faction: Faction[p.faction] + ":" + rate.toFixed() + "%",
      wins: p.winLoss?.wins ?? 0,
      losses: p.winLoss?.losses ?? 0,
    }
  })
  return (
    <Box sx={{ flexGrow: 1 }}>
      <Grid container spacing={2}>
        <Grid item xs={12} md={2}>
          <Typography variant="h3">{props.stat.playerName}</Typography>
          <List sx={{ display: { xs: "none", md: "block" } }}>
            {sorted.map((p) => (
              <PlayerListItem playerStatWL={p} />
            ))}
          </List>
        </Grid>
        <Grid item xs={12} md={10}>
          <ResponsiveContainer width="99%" height={350}>
            <BarChart data={faction_data} layout="horizontal">
              <CartesianGrid strokeDasharray="5 5" vertical={false} />
              <Bar dataKey="wins" fill="#42A5F5" />
              <Bar dataKey="losses" fill="#FF7043" />
              <XAxis dataKey="faction" />
              <YAxis domain={[0, props.max]} />
              <Tooltip cursor={false} />
            </BarChart>
          </ResponsiveContainer>
          <ResponsiveContainer width="99%" height={350}>
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
              <Tooltip cursor={false} />
            </BarChart>
          </ResponsiveContainer>
        </Grid>
      </Grid>
      <GeneralStatOverTime ot={props.stat.overTime} />
    </Box>
  )
}

const empty = { playerStats: [] }

export default function DisplayPlayerStats() {
  const [playerStats, setPlayerStats] = React.useState<PlayerStats>(empty)
  React.useEffect(() => {
    getPlayerStats(setPlayerStats)
  }, [])
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
      {playerStats.playerStats.map((m) => (
        <>
          <DisplayPlayerStat stat={m} max={maxWinLoss} />
          <Divider />
        </>
      ))}
    </Paper>
  )
}
