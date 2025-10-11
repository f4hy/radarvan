import Box from "@mui/material/Box"
import Divider from "@mui/material/Divider"
import FormControl from "@mui/material/FormControl"
import InputLabel from "@mui/material/InputLabel"
import MenuItem from "@mui/material/MenuItem"
import Paper from "@mui/material/Paper"
import Select, { SelectChangeEvent } from "@mui/material/Select"
import Typography from "@mui/material/Typography"
import _ from "lodash"
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { TeamColor } from "./Colors"
import { DateMessage, Faction, TeamStat, TeamStats } from "./proto/match"

function getTeamStats(querystr: string, callback: (m: TeamStats) => void) {
  fetch("/api/teamstatsfiltered?" + querystr).then((r) =>
    r
      .blob()
      .then((b) => b.arrayBuffer())
      .then((j) => {
        const a = new Uint8Array(j)
        const teamStats = TeamStats.decode(a)
        callback(teamStats)
      })
  )
}

function roundUpNearest5(num: number) {
  return Math.ceil(num / 5) * 5
}

interface OverTime {
  datestr: string
  date: Date
  time: number
  team1: 0
  team3: 0
}
function pad(n: number): string {
  return n.toString().padStart(2, "0")
}

function datemsgtoString(datemsg: DateMessage | undefined) {
  if (datemsg) {
    return `${datemsg.Year}.${pad(datemsg.Month)}.${pad(datemsg.Day)}`
  }
  return "unknown"
}
function datemsgtoDate(datemsg: DateMessage | undefined): Date {
  if (datemsg) {
    return new Date(datemsg.Year, datemsg.Month - 1, datemsg.Day - 1)
  }
  return new Date()
}

function addMonths(date: Date, months: number): Date {
  let newDate = new Date(date.setMonth(date.getMonth() + months))
  return newDate
}

function timeFmt(time: number): string {
  const date = new Date(time)
  return `${date.toLocaleDateString()}`
}
function tickFmt(time: number): string {
  const date = new Date(time)
  return `${date.toLocaleDateString("en", { year: "2-digit", month: "short" })}`
}

function RecordOverTime(props: { stats: TeamStats }) {
  const initial: OverTime[] = []
  function reducer(acc: OverTime[], next: TeamStat): OverTime[] {
    const datestr = datemsgtoString(next.date)
    const toAdd: OverTime = {
      datestr: datestr,
      date: datemsgtoDate(next.date),
      time: datemsgtoDate(next.date).getTime(),
      team1: 0,
      team3: 0,
    }
    if (acc.length) {
      const last = acc[acc.length - 1]
      if (last.datestr === datestr) {
        acc.pop()
      }
      toAdd.team1 += last.team1
      toAdd.team3 += last.team3
    }
    if (next.team === 1) {
      toAdd.team1 += next.wins
    }
    if (next.team === 3) {
      toAdd.team3 += next.wins
    }

    return [...acc, toAdd]
  }
  const data = _.orderBy(props.stats.teamStats, (ts) =>
    datemsgtoString(ts.date)
  ).reduce(reducer, initial)
  const rates = data.map((x) => ({
    date: x.date,
    time: x.date.getTime(),
    team1: (100 * x.team1) / (x.team1 + x.team3),
    team3: (100 * x.team3) / (x.team1 + x.team3),
  }))
  const minDate = _.min(rates.map((d) => d.date)) ?? new Date()
  const maxDate = _.max(rates.map((d) => d.date)) ?? new Date()
  const nextFirst = new Date(minDate.getTime())
  nextFirst.setMonth(minDate.getMonth() + 1)
  nextFirst.setDate(1)
  const ticks = Array(100)
    .fill(0)
    .map((v, i) => addMonths(new Date(nextFirst.getTime()), i))
    .filter((v) => v <= maxDate)
    .map((d) => d.getTime())
  const KC = new Date(2023, 1, 10).getTime()
  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography>Win Rate</Typography>
      <ResponsiveContainer width="95%" height={500}>
        <LineChart
          height={300}
          data={rates}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="time"
            scale="time"
            type="number"
            domain={[minDate.getTime(), maxDate.getTime()]}
            tickFormatter={tickFmt}
            minTickGap={0}
            ticks={ticks}
          />
          <YAxis domain={[0, 100]} />
          <Tooltip
            formatter={(v) => (v as number).toFixed(2) + "%"}
            labelFormatter={timeFmt}
          />
          <Legend />
          <Line dataKey="team1" stroke={TeamColor("1")} strokeWidth={3} />
          <Line dataKey="team3" stroke={TeamColor("3")} strokeWidth={3} />
          <ReferenceLine
            x={KC}
            label="KC"
            stroke="red"
            strokeWidth={2}
            strokeDasharray="3 6"
          />
        </LineChart>
      </ResponsiveContainer>
      <Typography>Wins</Typography>
      <ResponsiveContainer width="95%" height={500}>
        <LineChart
          height={300}
          data={data}
          margin={{
            top: 5,
            right: 30,
            left: 20,
            bottom: 5,
          }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="time"
            scale="time"
            type="number"
            domain={[minDate.getTime(), maxDate.getTime()]}
            tickFormatter={timeFmt}
            minTickGap={0}
            ticks={ticks}
          />
          <YAxis />
          <Tooltip labelFormatter={timeFmt} />
          <Legend />
          <Line dataKey="team1" stroke={TeamColor("1")} strokeWidth={3} />
          <Line dataKey="team3" stroke={TeamColor("3")} strokeWidth={3} />
          <ReferenceLine
            x={KC}
            label="KC"
            stroke="red"
            strokeWidth={2}
            strokeDasharray="3 6"
          />
        </LineChart>
      </ResponsiveContainer>
    </Box>
  )
}

function DisplayTeamStat(props: {
  stats: TeamStat[]
  title: string
  max: number
}) {
  /* const data = [props.stats.reduce((acc, s) => ({teamname: `${s.team}`, [s.team]: s.wins, ...acc}), {})] */
  const data = props.stats.sort((x1, x2) => x1.team - x2.team) //.reduce((o, x)=> ({...o, ["team"+ x.team]: x.wins}), {"a": 1})];
  const total = data.reduce((sum, c) => sum + c.wins, 0)
  return (
    <Box sx={{ flexGrow: 1 }}>
      <Typography variant="h4">
        {props.title + " Played " + total + " games"}
      </Typography>
      <ResponsiveContainer width="95%" height={300}>
        <BarChart data={data} layout="vertical">
          <Bar dataKey="wins" fill="#8884d8">
            <LabelList dataKey="wins" position="right" />
          </Bar>
          <YAxis dataKey="team" label="team" type="category" />
          <XAxis label="wins" type="number" domain={[0, props.max]} />
          <Tooltip cursor={false} />
        </BarChart>
      </ResponsiveContainer>
    </Box>
  )
}

function Selector(props: {
  name: string
  param: string
  setter: (v: string) => void
}) {
  const name = props.name
  return (
    <FormControl fullWidth>
      <InputLabel id={`${name}-general-select`}>{name}'s Faction</InputLabel>
      <Select
        labelId={`${name}-label`}
        id={`${name}-simple-select`}
        value={props.param}
        label={name}
        onChange={(event: SelectChangeEvent) =>
          props.setter(event.target.value.toString() as string)
        }
      >
        <MenuItem value={""}>Unset</MenuItem>
        <MenuItem value={Faction.ANYUSA}>USA</MenuItem>
        <MenuItem value={Faction.ANYCHINA}>China</MenuItem>
        <MenuItem value={Faction.ANYGLA}>GLA</MenuItem>
      </Select>
    </FormControl>
  )
}

const empty = { teamStats: [] }

export default function DisplayTeamStats() {
  const [teamStats, setTeamStats] = React.useState<TeamStats>(empty)
  const [brendan, setBrendan] = React.useState<string>("")
  const [jared, setJared] = React.useState<string>("")
  const [sean, setSean] = React.useState<string>("")
  const [bill, setBill] = React.useState<string>("")
  const [searchParams, setSearchParams] = React.useState<string>("")
  React.useEffect(() => {
    getTeamStats(searchParams, setTeamStats)
  }, [searchParams])

  React.useEffect(() => {
    const params = new URLSearchParams("")
    if (brendan.length) {
      params.append("Brendan", brendan)
    }
    if (bill.length) {
      params.append("Bill", bill)
    }
    if (sean.length) {
      params.append("Sean", sean)
    }
    if (jared.length) {
      params.append("Jared", jared)
    }
    setSearchParams(params.toString())
  }, [brendan, bill, sean, jared])

  const max = teamStats.teamStats.reduce((max, s) => Math.max(max, s.wins), 0)
  const grouped = Object.entries(
    _.groupBy(teamStats.teamStats, (ts: TeamStat) => datemsgtoString(ts.date))
  )
  const ordered = _.orderBy(grouped, (s) => s[0], ["desc"])
  const matches = teamStats.teamStats.reduce((acc, x) => acc + x.wins, 0)
  const teamSum: { [team: string]: number } = teamStats.teamStats.reduce(
    (acc: { [team: string]: number }, x) => ({
      ...acc,
      [x.team]: (acc[x.team] ?? 0) + x.wins,
    }),
    {}
  )

  return (
    <Paper>
      <Selector name="Brendan" param={brendan} setter={setBrendan} />
      <Selector name="Jared" param={jared} setter={setJared} />
      <Selector name="Bill" param={bill} setter={setBill} />
      <Selector name="Sean" param={sean} setter={setSean} />
      {searchParams.length > 0 ? (
        <Typography variant="h4">
          Limiting matches to just those where {searchParams}
        </Typography>
      ) : null}
      <Typography variant="h2">{matches} games played! </Typography>
      {Object.keys(teamSum).map((x: any) => (
        <Typography variant="h2">
          Team {x} has {teamSum[x]} wins.{" "}
          {((100 * teamSum[x]) / matches).toFixed(2)}%{" "}
        </Typography>
      ))}
      <RecordOverTime stats={teamStats} />
      {searchParams.length > 0
        ? null
        : ordered.map(([date, m]) => (
            <>
              <DisplayTeamStat
                stats={m}
                title={date}
                max={roundUpNearest5(max)}
              />
              <Divider />
            </>
          ))}
    </Paper>
  )
}
