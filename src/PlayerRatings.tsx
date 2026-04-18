import Stack from "@mui/material/Stack"
import Paper from "@mui/material/Paper"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import { Box, Typography, useTheme } from "@mui/material"
import useMediaQuery from "@mui/material/useMediaQuery"

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
  Line,
} from "recharts"
import { PlayerRatingData } from "./api"
import { Client } from "./Client"
import Loading from "./Loading"
import { useErrorSnackbar } from "./useErrorSnackbar"

const FORMAT_OPTIONS = ["All", "2v2", "3v3", "4v4"] as const
type GameFormat = (typeof FORMAT_OPTIONS)[number]

function getPlayerRatings(
  gameFormat: GameFormat,
  callback: (m: PlayerRatingData) => void,
  onError = console.error,
) {
  const params = gameFormat === "All" ? {} : { gameFormat }
  Client.getPlayerRatingsApiPlayerRatingsGet(params)
    .then(callback)
    .catch(onError)
}

function formatLabel(val: unknown): string {
  if (typeof val == "number") {
    return `${Number(val).toFixed(1)}`
  }
  return String(val ?? "")
}

const formatDate = (tickItem: number, short = false): string => {
  return new Date(tickItem).toLocaleDateString("en-US", {
    month: "short",
    ...(short ? { year: "2-digit" } : { day: "numeric", year: "numeric" }),
  })
}

function formatSkill(v: [number, number]): string {
  const ave = (v[0] + v[1]) / 2
  const val = ave.toFixed(1)
  const ebar = (ave - v[0]).toFixed(1)
  return `${val}±${ebar}`
}

function RatingsOverTime(props: { data: PlayerRatingData }) {
  const [startYear, setStartYear] = React.useState(2024)
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"))

  const allEntries = Object.entries(props.data.playerRatingOvertime ?? {})
  const earliestYear =
    allEntries.length > 0
      ? Math.min(
          ...allEntries.flatMap(([, d]) =>
            d.map((x) => new Date(x.atdate ?? 0).getFullYear()),
          ),
        )
      : 2022
  const currentYear = new Date().getFullYear()
  const years = Array.from(
    { length: currentYear - earliestYear + 1 },
    (_, i) => earliestYear + i,
  )

  const startMs = new Date(`${startYear}-01-01`).getTime()

  const data = allEntries
    .map(([name, d]) => {
      // Keep only the last entry per date
      const byDate = new Map<string, (typeof d)[0]>()
      for (const entry of d) {
        byDate.set(String(entry.atdate ?? ""), entry)
      }
      const deduped = Array.from(byDate.values())
      const sorted = [...deduped].sort(
        (a, b) =>
          new Date(a.atdate ?? 0).getTime() - new Date(b.atdate ?? 0).getTime(),
      )
      // Compute delta (mu change from previous entry)
      const withDelta = sorted.map((entry, i) => ({
        ...entry,
        delta: i > 0 ? (entry.mu ?? 0) - (sorted[i - 1].mu ?? 0) : null,
      }))
      const finalMu = sorted[sorted.length - 1]?.mu ?? 0
      return [name, withDelta, finalMu] as const
    })
    .sort((a, b) => b[2] - a[2])

  return (
    <Stack>
      <ToggleButtonGroup
        exclusive
        value={startYear}
        onChange={(_, v) => {
          if (v !== null) setStartYear(v)
        }}
        size="small"
        sx={{ mb: 1 }}
      >
        {years.map((y) => (
          <ToggleButton key={y} value={y}>
            {y}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
      {data.map(([name, d]) => {
        const last5 = d.slice(-20)
        const chartData = d
          .map((x) => ({
            mu: x.mu,
            sigma: x.sigma,
            delta: x.delta,
            skill: [(x.mu ?? 0) - (x.sigma ?? 0), (x.mu ?? 0) + (x.sigma ?? 0)],
            atdate: new Date(x.atdate ?? 0).getTime(),
          }))
          .filter((x) => x.atdate >= startMs)
        return (
          <Stack key={name}>
            <Typography>{name}</Typography>
            <Stack direction="row" spacing={2} sx={{ mb: 1 }}>
              {last5.map((entry, i) => {
                const isPositive = (entry.delta ?? 0) >= 0
                return (
                  <Box key={i} sx={{ textAlign: "center" }}>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      display="block"
                    >
                      {"" + entry.atdate}
                    </Typography>
                    <Typography variant="body2" fontWeight="bold">
                      {entry.mu?.toFixed(1)}±{entry.sigma?.toFixed(1)}
                    </Typography>
                    {entry.delta != null && (
                      <Typography
                        variant="caption"
                        color={isPositive ? "success.main" : "error.main"}
                        display="block"
                      >
                        {isPositive ? "+" : ""}
                        {entry.delta.toFixed(1)}
                      </Typography>
                    )}
                  </Box>
                )
              })}
            </Stack>
            <ResponsiveContainer width="100%" height={isMobile ? 180 : 250}>
              <AreaChart
                data={chartData}
                layout="horizontal"
                margin={{
                  top: 20,
                  right: 5,
                  left: isMobile ? 30 : 50,
                  bottom: isMobile ? 35 : 5,
                }}
              >
                <CartesianGrid strokeDasharray="5 5" vertical={false} />
                <Area
                  dataKey="skill"
                  fill="#42A5F5"
                  connectNulls
                  type="linear"
                />
                <Line
                  dataKey="mu"
                  stroke="none"
                  dot={(props: {
                    cx?: number
                    cy?: number
                    payload?: { delta?: number | null }
                  }) => {
                    const { cx = 0, cy = 0, payload } = props
                    const delta = payload?.delta
                    if (delta == null || Math.abs(delta) < 0.05) {
                      return <g key={`dot-${cx}-${cy}`} />
                    }
                    const pos = delta >= 0
                    const color = pos ? "#4caf50" : "#f44336"
                    const label = `${pos ? "+" : ""}${delta.toFixed(1)}`
                    return (
                      <text
                        key={`delta-${cx}-${cy}`}
                        x={cx}
                        y={cy - 6}
                        fill={color}
                        fontSize={10}
                        textAnchor="middle"
                      >
                        {label}
                      </text>
                    )
                  }}
                />
                <XAxis
                  dataKey="atdate"
                  type="number"
                  domain={[startMs, Date.now()]}
                  tickFormatter={(v) => formatDate(v, isMobile)}
                  angle={isMobile ? -35 : 0}
                  textAnchor={isMobile ? "end" : "middle"}
                  height={isMobile ? 50 : 30}
                />
                <YAxis
                  label={
                    isMobile
                      ? undefined
                      : {
                          value: "skill",
                          position: "insideLeft",
                          fontSize: 14,
                          offset: -10,
                          angle: -90,
                        }
                  }
                  domain={[0, 50]}
                  width={isMobile ? 30 : 50}
                />
                <Tooltip
                  cursor={false}
                  labelFormatter={(v) => formatDate(v)}
                  formatter={(v, name) => {
                    if (name === "skill")
                      return v != null ? formatSkill(v as [number, number]) : ""
                    if (name === "delta" && v != null) {
                      const n = v as number
                      return [`${n >= 0 ? "+" : ""}${n.toFixed(1)}`, "change"]
                    }
                    return ""
                  }}
                />
              </AreaChart>
            </ResponsiveContainer>
          </Stack>
        )
      })}
    </Stack>
  )
}

type RatingEntry = {
  mu: number
  sigma: number
  variance: number
  name: string
  ordinal: number
  gameCount: number
}

function FormatSelector(props: {
  format: GameFormat
  onChange: (f: GameFormat) => void
}) {
  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2, p: 1 }}>
      <Typography variant="h6">Game Format:</Typography>
      <ToggleButtonGroup
        value={props.format}
        exclusive
        onChange={(_, v) => v && props.onChange(v)}
        size="small"
      >
        {FORMAT_OPTIONS.map((f) => (
          <ToggleButton key={f} value={f}>
            {f}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </Stack>
  )
}

function SkillScatterChart(props: { data: RatingEntry[]; isMobile: boolean }) {
  const { data, isMobile } = props
  const labelFontSize = isMobile ? 11 : 20
  const leftMargin = isMobile ? 30 : 50
  return (
    <ResponsiveContainer width="100%" height={isMobile ? 300 : 500}>
      <ScatterChart
        margin={{
          top: 5,
          right: isMobile ? 30 : 10,
          left: leftMargin,
          bottom: isMobile ? 30 : 5,
        }}
      >
        <Scatter name="skill" data={data} shape="triangle" fill="blue">
          <LabelList
            dataKey="ordinal"
            position="bottom"
            offset={isMobile ? 15 : 40}
            formatter={(s) => Number(s).toFixed(1)}
            fontSize={labelFontSize}
          />
          <LabelList
            dataKey="mu"
            position="right"
            offset={1}
            formatter={(s) => Number(s).toFixed(isMobile ? 1 : 2)}
            fontSize={labelFontSize}
          />
          <ErrorBar
            dataKey="sigma"
            width={isMobile ? 4 : 10}
            strokeWidth={isMobile ? 2 : 5}
            stroke="skyblue"
            direction="y"
          />
        </Scatter>
        <XAxis dataKey="name" tick={{ fontSize: isMobile ? 11 : 14 }} />
        <YAxis
          label={
            isMobile
              ? undefined
              : {
                  value: "Estimated Skill",
                  position: "insideLeft",
                  fontSize: 16,
                  offset: -10,
                  angle: -90,
                }
          }
          type="number"
          dataKey="mu"
          domain={[0, 50]}
          width={leftMargin}
        />
        <ZAxis type="number" range={[100, 100]} />
        <Tooltip cursor={{ strokeDasharray: "3 3" }} formatter={formatLabel} />
        <CartesianGrid />
      </ScatterChart>
    </ResponsiveContainer>
  )
}

function GameCountBarChart(props: { data: RatingEntry[]; isMobile: boolean }) {
  const { data, isMobile } = props
  const leftMargin = isMobile ? 30 : 50
  return (
    <ResponsiveContainer width="100%" height={isMobile ? 180 : 250}>
      <BarChart
        data={data}
        layout="horizontal"
        margin={{ top: 5, right: 5, left: leftMargin, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="5 5" vertical={false} />
        <Bar dataKey="gameCount" fill="#42A5F5" />
        <XAxis dataKey="name" tick={{ fontSize: isMobile ? 11 : 14 }} />
        <YAxis
          label={
            isMobile
              ? undefined
              : {
                  value: "# games",
                  position: "insideLeft",
                  fontSize: 16,
                  offset: -10,
                  angle: -90,
                }
          }
          width={leftMargin}
        />
        <Tooltip cursor={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

const emptyPlayerRatingData = { playerRating: [], playerRatingOverTime: {} }
export default function DisplayPlayerRatings() {
  const [playerRatings, setPlayerRatings] = React.useState<PlayerRatingData>(
    emptyPlayerRatingData,
  )
  const [format, setFormat] = React.useState<GameFormat>("All")
  const { showError, errorSnackbar } = useErrorSnackbar()
  React.useEffect(() => {
    setPlayerRatings(emptyPlayerRatingData)
    getPlayerRatings(format, setPlayerRatings, showError)
  }, [format, showError])

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"))

  if (playerRatings.playerRating.length === 0) {
    return <Loading />
  }
  const data = playerRatings.playerRating
    .map((r) => ({ ...r, variance: r.sigma * r.sigma }))
    .sort((a, b) => b.mu - a.mu)
  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000 }}>
      <FormatSelector format={format} onChange={setFormat} />
      <Typography variant="h4">Player Ratings (debug only)</Typography>
      <SkillScatterChart data={data} isMobile={isMobile} />
      <GameCountBarChart data={data} isMobile={isMobile} />
      <RatingsOverTime data={playerRatings} />
      {errorSnackbar}
    </Paper>
  )
}
