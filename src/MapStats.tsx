import Box from "@mui/material/Box"
import Stack from "@mui/material/Stack"
import Paper from "@mui/material/Paper"
import Typography from "@mui/material/Typography"
import useMediaQuery from "@mui/material/useMediaQuery"
import _ from "lodash"
import * as React from "react"
import Grid from "@mui/material/Grid"
import Map from "./Map"

import {
  Bar,
  BarChart,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { TeamColor } from "./Colors"
import {
  DateMessage,
  MapResult,
  MapResults,
  MapStat,
  MapStats,
  Team,
} from "./proto/match"

function getMapStats(callback: (m: MapStats) => void) {
  fetch("/api/mapstats").then((r) =>
    r
      .blob()
      .then((b) => b.arrayBuffer())
      .then((j) => {
        const a = new Uint8Array(j)
        const mapstats = MapStats.decode(a)
        callback(mapstats)
      })
  )
}
const emptyOverTime: { [key: string]: MapResults } = {}
const empty: MapStats = { mapStats: [], overTime: emptyOverTime }

interface Red {
  map: string
  team1: number
  team3: number
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

function datemsgtoNum(datemsg: DateMessage | undefined) {
  if (!datemsg) {
    return 0
  }
  return (datemsg.Year * 12 + datemsg.Month) * 365 + datemsg.Day
}

interface MapWinOverTime {
  datestr: string
  team1: number
  team3: number
  games: number
}

function MapStatOverTime(props: { stat: MapResult[] }) {
  if (props.stat.length < 3) {
    return <></>
  }
  const sorted = _.sortBy(props.stat, (s) => datemsgtoNum(s.date))
  const first = props.stat[0]
  let data: MapWinOverTime[] = []
  let team1 = 0
  let team3 = 0
  let games = 0
  for (let index in sorted) {
    games += 1
    if (sorted[index].winner === Team.ONE) {
      team1 += 1
    }
    if (sorted[index].winner === Team.THREE) {
      team3 += 1
    }
    let datestr = datemsgtoString(sorted[index].date)
    data = [
      ...data,
      { datestr: datestr, team1: team1, team3: team3, games: games },
    ]
  }

  return (
    <Paper elevation={6}>
      <Grid container spacing={2}>
        <Grid item xs={1} md={2}>
          <Map mapname={first.map} />
        </Grid>
        <Grid item xs={11} md={10}>
          <Typography variant="h4">{first.map.split("/").pop()}</Typography>
          <ResponsiveContainer width="99%" height={300}>
            <LineChart
              data={data}
              layout="horizontal"
              stackOffset="sign"
              margin={{
                top: 20,
                right: 30,
                left: 20,
                bottom: 5,
              }}
            >
              <Line
                dataKey="team1"
                stroke={TeamColor("1")}
                strokeWidth={3}
                label={{ position: "top" }}
              />
              <Line
                dataKey="team3"
                stroke={TeamColor("3")}
                strokeWidth={3}
                label={{ position: "top" }}
              />
              <ReferenceLine y={0} stroke="#000" />
              <XAxis dataKey="datestr" />
              <YAxis label="wins" />
              <Tooltip cursor={false} />
            </LineChart>
          </ResponsiveContainer>
        </Grid>
      </Grid>
    </Paper>
  )
}

export default function DisplayMapstats() {
  const [mapstats, setMapstats] = React.useState<MapStats>(empty)
  React.useEffect(() => {
    getMapStats(setMapstats)
  }, [])
  const isBig = useMediaQuery("(min-width:1200px)")

  const max = mapstats.mapStats.reduce((max, s) => Math.max(max, s.wins), 0)
  const initial: Red[] = []
  function reducer(reds: Red[], next: MapStat) {
    const nmap = next.map.split("/").pop()
    if (!nmap) {
      return reds
    }
    const found = reds.find((r) => r.map === nmap)

    if (found) {
      if (next.team === 1) {
        found.team1 += next.wins
      }
      if (next.team === 3) {
        found.team3 += next.wins
      }
      return reds
    }
    const n: Red = {
      map: nmap,
      team1: next.team === 1 ? next.wins : 0,
      team3: next.team === 3 ? next.wins : 0,
    }
    return [...reds, n]
  }
  function redScore(r: Red): number {
    return r.team1 * 1.01 + r.team3 + r.map.length * 0.00001
  }
  const data = mapstats.mapStats
    .reduce(reducer, initial)
    .sort((m1, m2) => redScore(m2) - redScore(m1))
  const chunks = _.chunk(data, isBig ? 64 : 16)
  const sorted_over_time_keys = _.sortBy(
    Object.keys(mapstats.overTime),
    (r) => -mapstats.overTime[r].results.length
  )
  return (
    <Paper>
      <Typography variant="h2">Map stats.</Typography>
      <Box sx={{ flexGrow: 1, maxWidth: 1600, textAlign: "center" }}>
        {chunks.map((chunk) => (
          <ResponsiveContainer width="99%" height={800}>
            <BarChart
              data={chunk}
              layout="horizontal"
              margin={{
                top: 20,
                right: 30,
                left: 20,
                bottom: 5,
              }}
            >
              <Bar dataKey="team1" fill="#82ca9d" stackId="a" />
              <Bar dataKey="team3" fill="#8884d8" stackId="a" />
              <XAxis
                dataKey="map"
                label="map"
                angle={90}
                height={500}
                textAnchor="begin"
                minTickGap={0}
                interval={0}
              />
              <YAxis domain={[0, max]} label="wins" />
              <Tooltip cursor={false} />
            </BarChart>
          </ResponsiveContainer>
        ))}
      </Box>
      <Stack spacing={2}>
        {sorted_over_time_keys.map((m) => (
          <MapStatOverTime stat={mapstats.overTime[m].results} />
        ))}
      </Stack>
    </Paper>
  )
}
