import Box from "@mui/material/Box"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import DisplayGeneral from "./Generals"
import { General, GeneralStat, GeneralStats } from "./proto/match"

function getGeneralStats(callback: (m: GeneralStats) => void) {
  fetch("/api/generalstats").then((r) =>
    r
      .blob()
      .then((b) => b.arrayBuffer())
      .then((j) => {
        const a = new Uint8Array(j)
        const generalStats = GeneralStats.decode(a)
        generalStats.generalStats.sort((s1, s2) => s1.general - s2.general)
        callback(generalStats)
      })
  )
}

function DisplayOverallGeneralStat(props: { stats: GeneralStats }) {
  const data = props.stats.generalStats.map((x) => {
    const wins = x?.total?.wins ?? 0
    const losses = x?.total?.losses ?? 0
    const tot = losses + wins
    const rate = (wins / (tot > 0 ? tot : 1)) * 100
    return {
      wins: wins,
      losses: losses,
      name: General[x.general] + ":" + rate.toFixed() + "%",
    }
  })
  return (
    <ResponsiveContainer width="99%" height={350}>
      <BarChart data={data} layout="horizontal">
        <CartesianGrid strokeDasharray="5 5" vertical={false} />
        <Bar dataKey="wins" fill="#42A5F5" />
        <Bar dataKey="losses" fill="#FF7043" />
        <XAxis dataKey="name" />
        <YAxis />
        <Tooltip cursor={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function DisplayGeneralStat(props: { stat: GeneralStat; max: number }) {
  const sorted = props.stat.stats.sort((s1, s2) =>
    s1.playerName.localeCompare(s2.playerName, "en")
  )
  const overall = props.stat.total
  let pdata = sorted.map((s) => ({
    name: s.playerName,
    wins: s.winLoss?.wins ?? 0,
    losses: s.winLoss?.losses ?? 0,
  }))
  const data = [
    { name: "overall", wins: overall?.wins ?? 0, losses: overall?.losses ?? 0 },
    ...pdata,
  ].map((x) => {
    const tot = x.losses + x.wins
    const rate = (x.wins / (tot > 0 ? tot : 1)) * 100
    return {
      wins: x.wins,
      losses: x.losses,
      name: x.name + ":" + rate.toFixed() + "%",
    }
  })
  return (
    <Box sx={{ flexGrow: 1 }}>
      <DisplayGeneral general={props.stat.general} />
      <ResponsiveContainer width="99%" height={350}>
        <BarChart data={data} layout="horizontal">
          <CartesianGrid strokeDasharray="5 5" vertical={false} />
          <Bar dataKey="wins" fill="#42A5F5" />
          <Bar dataKey="losses" fill="#FF7043" />
          <XAxis dataKey="name" />
          <YAxis domain={["auto", props.max]} />
          <Tooltip cursor={false} />
        </BarChart>
      </ResponsiveContainer>
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
    0
  )
  const maxWinLoss = roundUpNearest5(maxwl + 1)
  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 1600 }}>
      {/* <Button variant="contained" onClick={() => getGeneralStats(setGeneralStats)} >Get Matches</Button> */}
      <DisplayOverallGeneralStat stats={generalStats} />
      {generalStats.generalStats.map((m) => (
        <>
          <DisplayGeneralStat stat={m} max={maxWinLoss} />
          <Divider />
        </>
      ))}
    </Paper>
  )
}
