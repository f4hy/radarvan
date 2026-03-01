import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Loading from "./Loading"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import Grid from "@mui/material/Grid"
import Stack from "@mui/material/Stack"
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import DisplayGeneral from "./Generals"
import { GeneralStat, GeneralStats } from "./api"
import { Client } from "./Client"
import { toGeneralName } from "./general_utils"
import { Typography } from "@mui/material"

function getGeneralStats(callback: (m: GeneralStats) => void) {
  Client.getGeneralsStatsApiGeneralstatsGet()
    .then(callback)
    .catch((e) => alert(e))
}

function winRate(wins: number, losses: number): number {
  const tot = wins + losses
  return tot > 0 ? wins / tot : 0
}

function DisplayOverallGeneralStat(props: { stats: GeneralStats }) {
  const data = props.stats.generalStats
    .map((x) => {
      const wins = x?.total?.wins ?? 0
      const losses = x?.total?.losses ?? 0
      return { wins, losses, name: toGeneralName(x.general), rate: winRate(wins, losses) }
    })

  return (
    <ResponsiveContainer width="99%" height={600}>
      <BarChart data={data} layout="horizontal" margin={{ top: 20, right: 20, left: 10, bottom: 60 }}>
        <CartesianGrid strokeDasharray="5 5" vertical={false} />
        <Bar dataKey="wins" fill="#42A5F5" name="Wins">
          <LabelList dataKey="wins" position="top" fontSize={11} />
          <LabelList dataKey="rate" position="insideTop" fontSize={11} fill="white" formatter={(v: any) => `${(v * 100).toFixed(0)}%`} />
        </Bar>
        <Bar dataKey="losses" fill="#FF7043" name="Losses">
          <LabelList dataKey="losses" position="top" fontSize={11} />
        </Bar>
        <XAxis dataKey="name" angle={-35} textAnchor="end" interval={0} />
        <YAxis />
        <Tooltip cursor={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function DisplayGeneralStat(props: { stat: GeneralStat; max: number }) {
  const overall = props.stat.total
  const overallWins = overall?.wins ?? 0
  const overallLosses = overall?.losses ?? 0
  const rate = winRate(overallWins, overallLosses)

  const data = props.stat.stats
    .map((s) => ({
      name: s.playerName,
      wins: s.winLoss?.wins ?? 0,
      losses: s.winLoss?.losses ?? 0,
      rate: winRate(s.winLoss?.wins ?? 0, s.winLoss?.losses ?? 0),
    }))
    .sort((a, b) => b.rate - a.rate)

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
        <DisplayGeneral general={props.stat.general} />
        <Typography variant="subtitle1" fontWeight="bold">
          {toGeneralName(props.stat.general)}
        </Typography>
        <Chip
          label={`${(rate * 100).toFixed(0)}% (${overallWins}W-${overallLosses}L)`}
          size="small"
          color={rate >= 0.5 ? "success" : "error"}
          variant="outlined"
        />
      </Stack>
    </Box>
  )
}

function roundUpNearest5(num: number) {
  return Math.ceil(num / 5) * 5
}

const empty = { generalStats: [] }

export default function DisplayGeneralStats() {
  const [generalStats, setGeneralStats] = React.useState<GeneralStats>(empty)
  React.useEffect(() => {
    getGeneralStats(setGeneralStats)
  }, [])
  const maxwl = generalStats.generalStats.reduce(
    (acc, s) => Math.max(acc, s.total?.wins ?? 0, s.total?.losses ?? 0),
    0,
  )
  const maxWinLoss = roundUpNearest5(maxwl + 1)
  if (generalStats.generalStats.length === 0) {
    return <Loading />
  }

  const sorted = [...generalStats.generalStats].sort((a, b) => {
    const rateA = winRate(a.total?.wins ?? 0, a.total?.losses ?? 0)
    const rateB = winRate(b.total?.wins ?? 0, b.total?.losses ?? 0)
    return rateB - rateA
  })

  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000 }}>
      <Typography variant="h4">
        Stats computed only from 1v1 2v2 3v3 and 4v4 games
      </Typography>
      <DisplayOverallGeneralStat stats={{ generalStats: generalStats.generalStats }} />
      <Divider sx={{ mt: 4, mb: 2 }} />
      <Typography variant="h4">Ordered by winrate </Typography>
      <Grid container spacing={2}>
        {sorted.map((m) => (
          <Grid key={m.general} item xs={12} sm={6} md={8}>
            <DisplayGeneralStat stat={m} max={maxWinLoss} />
          </Grid>
        ))}
      </Grid>
    </Paper>
  )
}
