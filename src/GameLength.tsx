import Box from "@mui/material/Box"
import Divider from "@mui/material/Divider"
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
import Typography from "@mui/material/Typography"
import useMediaQuery from "@mui/material/useMediaQuery"
import { useTheme } from "@mui/material/styles"
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { DurationDistribution, DurationStats } from "./api"
import { Client } from "./Client"
import Loading from "./Loading"
import Page from "./Page"
import { BRAND_COLOR, CHART_PALETTE, NEUTRAL_COLOR } from "./theme"
import { useErrorSnackbar } from "./useErrorSnackbar"

const FORMAT_OPTIONS = ["All", "1v1", "2v2", "3v3", "4v4"] as const
type GameFormat = (typeof FORMAT_OPTIONS)[number]

// Bar widths the histogram offers. Two minutes is the default the API picks;
// one shows the rush/macro split, five is for eyeballing the overall shape.
const BUCKET_OPTIONS = [1, 2, 5] as const
type BucketMinutes = (typeof BUCKET_OPTIONS)[number]

function formatMinutes(value: number | null | undefined): string {
  if (value === null || value === undefined) return "—"
  const total = Math.round(value * 60)
  const minutes = Math.floor(total / 60)
  const seconds = total % 60
  return `${minutes}:${String(seconds).padStart(2, "0")}`
}

function formatHours(minutes: number): string {
  const hours = minutes / 60
  return hours >= 24
    ? `${(hours / 24).toFixed(1)} days`
    : `${hours.toFixed(0)} hours`
}

type HistogramBar = {
  label: string
  start: number
  count: number
  isOverflow: boolean
}

// The API returns every bucket including empty ones so the axis is continuous.
// Trailing empties are still dropped for display: the corpus has a handful of
// hour-long games, and 30 empty bars past the last real one squash everything
// worth looking at into the left third of the chart.
function toBars(distribution: DurationDistribution): HistogramBar[] {
  const buckets = distribution.buckets ?? []
  let last = buckets.length - 1
  while (last > 0 && buckets[last].count === 0) last--
  return buckets.slice(0, last + 1).map((bucket) => ({
    label:
      bucket.endMinutes === null || bucket.endMinutes === undefined
        ? `${bucket.startMinutes}+`
        : `${bucket.startMinutes}`,
    start: bucket.startMinutes,
    count: bucket.count,
    isOverflow: bucket.endMinutes === null || bucket.endMinutes === undefined,
  }))
}

function StatTile(props: { label: string; value: string; hint?: string }) {
  return (
    <Paper variant="outlined" sx={{ p: 1.5, flex: "1 1 130px", minWidth: 120 }}>
      <Typography variant="caption" color="text.secondary">
        {props.label}
      </Typography>
      <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
        {props.value}
      </Typography>
      {props.hint && (
        <Typography variant="caption" color="text.secondary">
          {props.hint}
        </Typography>
      )}
    </Paper>
  )
}

function HistogramTooltip(props: {
  active?: boolean
  payload?: { payload: HistogramBar }[]
  bucketMinutes: number
  total: number
}) {
  if (!props.active || !props.payload?.length) return null
  const bar = props.payload[0].payload
  const share = props.total > 0 ? (bar.count / props.total) * 100 : 0
  const range = bar.isOverflow
    ? `${bar.start} min and up`
    : `${bar.start}–${bar.start + props.bucketMinutes} min`
  return (
    <Paper variant="outlined" sx={{ p: 1 }}>
      <Typography variant="body2" sx={{ fontWeight: "bold" }}>
        {range}
      </Typography>
      <Typography variant="body2">
        {bar.count} {bar.count === 1 ? "game" : "games"} ({share.toFixed(1)}%)
      </Typography>
    </Paper>
  )
}

function Histogram(props: {
  distribution: DurationDistribution
  bucketMinutes: number
  isMobile: boolean
}) {
  const bars = React.useMemo(
    () => toBars(props.distribution),
    [props.distribution],
  )
  const stats = props.distribution.stats
  const total = stats.count
  return (
    <ResponsiveContainer width="99%" height={props.isMobile ? 300 : 420}>
      <BarChart
        data={bars}
        margin={{ top: 10, right: 12, left: 0, bottom: 24 }}
        barCategoryGap={1}
      >
        <CartesianGrid strokeDasharray="5 5" vertical={false} />
        <XAxis
          dataKey="label"
          tick={{ fontSize: 11 }}
          interval="preserveStartEnd"
          minTickGap={12}
          label={{
            value: "Game length (minutes)",
            position: "insideBottom",
            offset: -14,
            fontSize: 12,
          }}
        />
        <YAxis
          tick={{ fontSize: 11 }}
          width={40}
          label={{
            value: "Games",
            angle: -90,
            position: "insideLeft",
            fontSize: 12,
          }}
        />
        <Tooltip
          content={
            <HistogramTooltip
              bucketMinutes={props.bucketMinutes}
              total={total}
            />
          }
          cursor={{ fill: "rgba(0,0,0,0.04)" }}
        />
        {stats.medianMinutes != null && (
          <ReferenceLine
            x={`${
              Math.floor(stats.medianMinutes / props.bucketMinutes) *
              props.bucketMinutes
            }`}
            stroke={CHART_PALETTE[1]}
            strokeDasharray="4 4"
            label={{ value: "median", position: "top", fontSize: 11 }}
          />
        )}
        <Bar dataKey="count" fill={BRAND_COLOR} radius={[2, 2, 0, 0]}>
          {bars.map((bar) => (
            <Cell
              key={bar.label}
              // The overflow bin is not the same width as the others, so it is
              // greyed rather than left looking like a comparable bar.
              fill={bar.isOverflow ? NEUTRAL_COLOR : BRAND_COLOR}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )
}

function FormatTable(props: { byFormat: { [key: string]: DurationStats } }) {
  const rows = Object.entries(props.byFormat)
  if (rows.length === 0) return null
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Format</TableCell>
            <TableCell align="right">Games</TableCell>
            <TableCell align="right">Median</TableCell>
            <TableCell align="right">Typical range</TableCell>
            <TableCell align="right">Longest</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {rows.map(([format, stats]) => (
            <TableRow key={format} hover>
              <TableCell sx={{ fontWeight: "bold" }}>{format}</TableCell>
              <TableCell align="right">{stats.count}</TableCell>
              <TableCell align="right">
                {formatMinutes(stats.medianMinutes)}
              </TableCell>
              <TableCell align="right">
                {formatMinutes(stats.p10Minutes)} –{" "}
                {formatMinutes(stats.p90Minutes)}
              </TableCell>
              <TableCell align="right">
                {formatMinutes(stats.longestMinutes)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

export default function GameLength() {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"))
  const [gameFormat, setGameFormat] = React.useState<GameFormat>("All")
  const [bucketMinutes, setBucketMinutes] = React.useState<BucketMinutes>(2)
  const [distribution, setDistribution] =
    React.useState<DurationDistribution | null>(null)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    setDistribution(null)
    Client.getDurationDistributionApiDurationDistributionGet({
      bucketMinutes,
      ...(gameFormat === "All" ? {} : { gameFormat }),
    })
      .then(setDistribution)
      .catch(showError)
  }, [gameFormat, bucketMinutes, showError])

  if (distribution === null) {
    return (
      <>
        {errorSnackbar}
        <Loading />
      </>
    )
  }

  const stats = distribution.stats
  return (
    <Page
      surface={false}
      title="Game Length"
      description="How long our games actually run. Comp-stomps and unfinished games are excluded, so a two-minute disconnect isn't counted as a two-minute game."
      actions={
        <>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={gameFormat}
            onChange={(_e, value) => value && setGameFormat(value)}
          >
            {FORMAT_OPTIONS.map((option) => (
              <ToggleButton key={option} value={option}>
                {option}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={bucketMinutes}
            onChange={(_e, value) => value && setBucketMinutes(value)}
          >
            {BUCKET_OPTIONS.map((option) => (
              <ToggleButton key={option} value={option}>
                {option} min bars
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </>
      }
    >
      <Stack spacing={2}>
        {errorSnackbar}
        <Stack
          direction="row"
          spacing={1.5}
          useFlexGap
          sx={{ flexWrap: "wrap" }}
        >
          <StatTile label="Games" value={stats.count.toLocaleString()} />
          <StatTile
            label="Median"
            value={formatMinutes(stats.medianMinutes)}
            hint="half are shorter"
          />
          <StatTile
            label="Typical range"
            value={`${formatMinutes(stats.p10Minutes)}–${formatMinutes(
              stats.p90Minutes,
            )}`}
            hint="10th to 90th percentile"
          />
          <StatTile
            label="Longest"
            value={formatMinutes(stats.longestMinutes)}
          />
          <StatTile
            label="Time played"
            value={formatHours(stats.totalMinutes)}
            hint="in-game, all together"
          />
        </Stack>

        <Paper variant="outlined" sx={{ p: 1.5 }}>
          <Histogram
            distribution={distribution}
            bucketMinutes={bucketMinutes}
            isMobile={isMobile}
          />
        </Paper>

        <Divider />
        <Typography variant="h6">By format</Typography>
        <FormatTable byFormat={distribution.byFormat ?? {}} />
      </Stack>
    </Page>
  )
}
