import Stack from "@mui/material/Stack"
import Paper from "@mui/material/Paper"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import { Typography } from "@mui/material"

import * as React from "react"
import {
  Bar,
  BarChart,
  LabelList,
  CartesianGrid,
  ErrorBar,
  Scatter,
  ScatterChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  AreaChart,
  Area,
} from "recharts"
import { PlayerRatingData } from "./api"
import { Client } from "./Client"
import Loading from "./Loading"

function getPlayerRatings(callback: (m: PlayerRatingData) => void) {
  Client.getPlayerRatingsApiPlayerRatingsGet()
    .then(callback)
    .catch((e) => alert(e))
}

function formatLabel(val: any): string {
  if (typeof val == "number") {
    return `${Number(val).toFixed(1)}`
  }
  return String(val ?? "")
}

const formatDate = (tickItem: number): string => {
  return new Date(tickItem).toLocaleDateString("en-US", {
    month: "short",
    day: "numeric",
    year: "numeric",
  })
}

function formatSkill(v: any): string {
  const ave = (v[0] + v[1]) / 2
  const val = ave.toFixed(1)
  const ebar = (ave - v[0]).toFixed(1)
  return `${val}±${ebar}`
}

function RatingsOverTime(props: { data: PlayerRatingData }) {
  const [startYear, setStartYear] = React.useState(2024)

  const allEntries = Object.entries(props.data.playerRatingOvertime ?? {})
  const earliestYear = allEntries.length > 0
    ? Math.min(...allEntries.flatMap(([, d]) => d.map((x) => new Date(x.atdate ?? 0).getFullYear())))
    : 2022
  const currentYear = new Date().getFullYear()
  const years = Array.from({ length: currentYear - earliestYear + 1 }, (_, i) => earliestYear + i)

  const startMs = new Date(`${startYear}-01-01`).getTime()

  const data = allEntries
    .map(([name, d]) => {
      const sorted = [...d].sort((a, b) => new Date(a.atdate ?? 0).getTime() - new Date(b.atdate ?? 0).getTime())
      const finalMu = sorted[sorted.length - 1]?.mu ?? 0
      return [name, d, finalMu] as const
    })
    .sort((a, b) => b[2] - a[2])

  if (data.length < 1) {
    ;<Typography>{JSON.stringify(data)}</Typography>
  }
  return (
    <Stack>
      <ToggleButtonGroup
        exclusive
        value={startYear}
        onChange={(_, v) => { if (v !== null) setStartYear(v) }}
        size="small"
        sx={{ mb: 1 }}
      >
        {years.map((y) => (
          <ToggleButton key={y} value={y}>{y}</ToggleButton>
        ))}
      </ToggleButtonGroup>
      {data.map(([name, d]) => (
        <Stack key={name}>
          <Typography>{name}</Typography>
          <ResponsiveContainer width="100%" height={250}>
            <AreaChart
              data={d
                .map((x) => ({
                  mu: x.mu,
                  sigma: x.sigma,
                  skill: [x.mu - x.sigma, x.mu + x.sigma],
                  atdate: new Date(x.atdate ?? 0).getTime(),
                }))
                .filter((x) => x.atdate >= startMs)}
              layout="horizontal"
              margin={{ top: 5, right: 10, left: 50, bottom: 5 }}
            >
              <CartesianGrid strokeDasharray="5 5" vertical={false} />
              <Area
                dataKey="skill"
                fill="#42A5F5"
                connectNulls
                type="linear"
              ></Area>
              <XAxis
                dataKey="atdate"
                type="number"
                domain={[startMs, Date.now()]}
                tickFormatter={formatDate}
              />
              <YAxis
                label={{
                  value: "# games",
                  position: "insideLeft",
                  fontSize: 25,
                  offset: -10,
                  angle: -90,
                }}
                domain={[0, 50]}
              />
              <Tooltip
                cursor={false}
                labelFormatter={(v) => formatDate(v)}
                formatter={(v) => (v !== null ? formatSkill(v) : "")}
              />
            </AreaChart>
          </ResponsiveContainer>
        </Stack>
      ))}
    </Stack>
  )
}

const emptyPlayerRatingData = { playerRating: [], playerRatingOverTime: {} }
export default function DisplayPlayerRatings() {
  const [playerRatings, setPlayerRatings] = React.useState<PlayerRatingData>(
    emptyPlayerRatingData,
  )
  React.useEffect(() => {
    getPlayerRatings(setPlayerRatings)
  }, [])

  if (playerRatings.playerRating.length === 0) {
    return <Loading />
  }
  const data = playerRatings.playerRating.map((r) => ({
    ...r,
    variance: r.sigma * r.sigma,
  }))
  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000 }}>
      <Typography variant="h4">Player Ratings (debug only)</Typography>
      <ResponsiveContainer width="100%" height={500}>
        <ScatterChart margin={{ top: 5, right: 10, left: 50, bottom: 5 }}>
          <Scatter name="skill" data={data} shape="triangle" fill="blue">
            <LabelList
              dataKey="ordinal"
              position="bottom"
              offset={40}
              formatter={(s) => Number(s).toFixed(1)}
              fontSize={20}
            />
            <LabelList
              dataKey="mu"
              position="right"
              offset={1}
              formatter={(s) => Number(s).toFixed(2)}
              fontSize={20}
            />
            <ErrorBar
              dataKey="sigma"
              width={10}
              strokeWidth={5}
              stroke="skyblue"
              direction="y"
            />
          </Scatter>
          <XAxis dataKey="name" />
          <YAxis
            label={{
              value: "Estimated Skill",
              position: "insideLeft",
              fontSize: 25,
              offset: -10,
              angle: -90,
            }}
            type="number"
            dataKey="mu"
            domain={[0, 50]}
          />
          <ZAxis type="number" range={[100, 100]} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            formatter={formatLabel}
          />
          <CartesianGrid />
        </ScatterChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={250}>
        <BarChart
          data={data}
          layout="horizontal"
          margin={{ top: 5, right: 10, left: 50, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="5 5" vertical={false} />
          <Bar dataKey="gameCount" fill="#42A5F5" />
          <XAxis dataKey="name" />
          <YAxis
            label={{
              value: "# games",
              position: "insideLeft",
              fontSize: 25,
              offset: -10,
              angle: -90,
            }}
          />
          <Tooltip cursor={false} />
        </BarChart>
      </ResponsiveContainer>
      <RatingsOverTime data={playerRatings} />
    </Paper>
  )
}
