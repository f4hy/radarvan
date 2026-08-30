import Stack from "@mui/material/Stack"
import Paper from "@mui/material/Paper"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Accordion from "@mui/material/Accordion"
import AccordionSummary from "@mui/material/AccordionSummary"
import AccordionDetails from "@mui/material/AccordionDetails"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import { Box, Tooltip as MuiTooltip, Typography, useTheme } from "@mui/material"
import useMediaQuery from "@mui/material/useMediaQuery"

import { useQuery } from "@tanstack/react-query"
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
import { HeadToHead, PlayerRatingData, PlayerSkill, RatingUpset } from "./api"
import { Client } from "./Client"
import Loading from "./Loading"
import Page from "./Page"
import { queryFallback } from "./QueryState"
import { SimplePlayerSynergy } from "./PlayerSynergy"
import { PlayerLabel } from "./PlayerChip"
import { BRAND_COLOR, WIN_COLOR, LOSS_COLOR } from "./theme"

const FORMAT_OPTIONS = ["All", "2v2", "3v3", "4v4"] as const
type GameFormat = (typeof FORMAT_OPTIONS)[number]

const MONTHS_BACK_OPTIONS = [1, 3, 6, 9, 12] as const
type MonthsBack = (typeof MONTHS_BACK_OPTIONS)[number] | null

function fetchPlayerRatings(
  gameFormat: GameFormat,
  monthsBack: MonthsBack,
): Promise<PlayerRatingData> {
  const params = {
    ...(gameFormat === "All" ? {} : { gameFormat }),
    ...(monthsBack == null ? {} : { monthsBack }),
  }
  return Client.getPlayerRatingsApiPlayerRatingsGet(params)
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
        const recentEntries = d.slice(-20)
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
            <Stack direction="row" spacing={2} sx={{ mb: 1, flexWrap: "wrap" }}>
              {recentEntries.map((entry, i) => {
                const isPositive = (entry.delta ?? 0) >= 0
                return (
                  <Box key={i} sx={{ textAlign: "center" }}>
                    <Typography
                      variant="caption"
                      sx={{
                        color: "text.secondary",
                        display: "block",
                      }}
                    >
                      {entry.atdate
                        ? formatDate(new Date(entry.atdate).getTime(), true)
                        : "—"}
                    </Typography>
                    <Typography
                      variant="body2"
                      sx={{
                        fontWeight: "bold",
                      }}
                    >
                      {entry.mu?.toFixed(1)}±{entry.sigma?.toFixed(1)}
                    </Typography>
                    {entry.delta != null && (
                      <Typography
                        variant="caption"
                        color={isPositive ? "success.main" : "error.main"}
                        sx={{
                          display: "block",
                        }}
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
                  fill={BRAND_COLOR}
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
                    const color = pos ? WIN_COLOR : LOSS_COLOR
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
                  height="auto"
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
                  labelFormatter={(v) => formatDate(v as number)}
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
  name: string
  ordinal: number
  gameCount: number
  recentDeltas?: { [key: string]: number }
  highOrdinal?: number | null
  lowOrdinal?: number | null
}

function DeltaCell(props: { delta: number | null | undefined }) {
  const delta = props.delta ?? 0
  const scaled = Math.round(delta * 10)
  const isHot = delta > 0
  return (
    <TableCell
      align="right"
      sx={{
        color:
          delta === 0
            ? "text.secondary"
            : isHot
              ? "success.main"
              : "error.main",
        fontWeight: "bold",
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {delta === 0 ? "—" : `${isHot ? "+" : ""}${scaled}`}
    </TableCell>
  )
}

function FormDots(props: { results: boolean[] }) {
  return (
    <Stack
      direction="row"
      spacing={0.5}
      sx={{
        alignItems: "center",
      }}
    >
      {props.results.map((won, i) => (
        <Box
          key={i}
          sx={{
            width: 10,
            height: 10,
            borderRadius: "50%",
            bgcolor: won ? "success.main" : "error.main",
          }}
        />
      ))}
    </Stack>
  )
}

function PlayerLeaderboard(props: {
  data: RatingEntry[]
  form: Record<string, boolean[]>
}) {
  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>#</TableCell>
            <TableCell>Player</TableCell>
            <TableCell align="right">
              <MuiTooltip title="ordinal × 10">
                <span>Rating</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="All-time high / low ordinal (× 10)">
                <span>Range</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">Games</TableCell>
            <TableCell>Last 10</TableCell>
            <TableCell align="right">
              <MuiTooltip title="Rating change over last 14 days (× 10)">
                <span>14d trend</span>
              </MuiTooltip>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {props.data.map((r, i) => (
            <TableRow key={r.name} hover>
              <TableCell>{i + 1}</TableCell>
              <TableCell>{r.name}</TableCell>
              <TableCell
                align="right"
                sx={{ fontVariantNumeric: "tabular-nums" }}
              >
                {Math.round(r.ordinal * 10)}
              </TableCell>
              <TableCell
                align="right"
                sx={{
                  fontVariantNumeric: "tabular-nums",
                  color: "text.secondary",
                  fontSize: "0.8em",
                }}
              >
                {r.highOrdinal != null && r.lowOrdinal != null
                  ? `${Math.round(r.highOrdinal * 10)} / ${Math.round(r.lowOrdinal * 10)}`
                  : "—"}
              </TableCell>
              <TableCell
                align="right"
                sx={{ fontVariantNumeric: "tabular-nums" }}
              >
                {r.gameCount}
              </TableCell>
              <TableCell>
                <FormDots results={props.form[r.name] ?? []} />
              </TableCell>
              <DeltaCell delta={r.recentDeltas?.[14]} />
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function pct(p: number): string {
  return `${Math.round(p * 100)}%`
}

function TeamPlayers(props: { names: string[] }) {
  return (
    <Stack
      direction="row"
      spacing={0.5}
      useFlexGap
      sx={{
        flexWrap: "wrap",
      }}
    >
      {props.names.map((n) => (
        <PlayerLabel key={n} name={n} />
      ))}
    </Stack>
  )
}

// "Recent upsets" = games in the last RECENT_UPSET_DAYS whose upset magnitude
// (favorite's win-probability edge over the actual winner) is at least
// RECENT_UPSET_MIN_PCT percent. Tweak these two constants to retune the section.
const RECENT_UPSET_DAYS = 120
const RECENT_UPSET_MIN_PCT = 60

function UpsetsTable(props: { upsets: RatingUpset[] }) {
  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>#</TableCell>
            <TableCell>Date</TableCell>
            <TableCell>Match</TableCell>
            <TableCell>Favored to win</TableCell>
            <TableCell align="right">Chance</TableCell>
            <TableCell>Beaten by</TableCell>
            <TableCell align="right">Chance</TableCell>
            <TableCell align="right">
              <MuiTooltip title="Favorite's win-probability edge over the actual winner">
                <span>Upset</span>
              </MuiTooltip>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {props.upsets.map((u, i) => (
            <TableRow key={u.matchId} hover>
              <TableCell>{i + 1}</TableCell>
              <TableCell sx={{ whiteSpace: "nowrap" }}>
                {u.atdate ? formatDate(new Date(u.atdate).getTime()) : "—"}
              </TableCell>
              <TableCell
                sx={{
                  fontFamily: "monospace",
                  fontSize: "0.8em",
                  color: "text.secondary",
                }}
              >
                {u.matchId}
              </TableCell>
              <TableCell>
                <TeamPlayers names={u.favoredPlayers} />
              </TableCell>
              <TableCell
                align="right"
                sx={{ fontVariantNumeric: "tabular-nums" }}
              >
                {pct(u.favoredWinProb)}
              </TableCell>
              <TableCell>
                <TeamPlayers names={u.winnerPlayers} />
              </TableCell>
              <TableCell
                align="right"
                sx={{ fontVariantNumeric: "tabular-nums" }}
              >
                {pct(u.winnerWinProb)}
              </TableCell>
              <TableCell
                align="right"
                sx={{
                  fontVariantNumeric: "tabular-nums",
                  fontWeight: "bold",
                  color: "error.main",
                }}
              >
                +{pct(u.surprise)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

// Recent big shocks: last RECENT_UPSET_DAYS days, surprise >= RECENT_UPSET_MIN_PCT%.
function RecentUpsets(props: { format: GameFormat }) {
  const query = useQuery({
    queryKey: ["ratingUpsets", "recent", props.format],
    queryFn: () =>
      Client.getRatingUpsetsApiPlayerRatingsUpsetsGet({
        limit: 200,
        withinDays: RECENT_UPSET_DAYS,
        minSurprise: RECENT_UPSET_MIN_PCT / 100,
        ...(props.format === "All" ? {} : { gameFormat: props.format }),
      }),
  })
  const fallback = queryFallback(query, "recent upsets")
  if (fallback) return fallback
  const upsets = query.data as RatingUpset[]
  if (upsets.length === 0) {
    return (
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
        }}
      >
        No upsets above {RECENT_UPSET_MIN_PCT}% in the last {RECENT_UPSET_DAYS}{" "}
        days.
      </Typography>
    )
  }

  return (
    <>
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
          mb: 1,
        }}
      >
        Games in the last {RECENT_UPSET_DAYS} days where the favored team had at
        least a {RECENT_UPSET_MIN_PCT}% pre-game edge and still lost.
      </Typography>
      <UpsetsTable upsets={upsets} />
    </>
  )
}

// Top games where the rating model's favored team lost. The "surprise" is the
// favorite's pre-game win-probability edge over the team that actually won.
function BiggestUpsets(props: { format: GameFormat }) {
  const query = useQuery({
    queryKey: ["ratingUpsets", "biggest", props.format],
    queryFn: () =>
      Client.getRatingUpsetsApiPlayerRatingsUpsetsGet({
        limit: 15,
        ...(props.format === "All" ? {} : { gameFormat: props.format }),
      }),
  })
  const fallback = queryFallback(query, "upsets")
  if (fallback) return fallback
  const upsets = query.data as RatingUpset[]
  if (upsets.length === 0) {
    return (
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
        }}
      >
        No upsets — the favored team won every rated game.
      </Typography>
    )
  }

  return (
    <>
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
          mb: 1,
        }}
      >
        Games where the favored team (by pre-game rating) lost, biggest shock
        first. The chance shown is the model&apos;s pre-game win probability.
      </Typography>
      <UpsetsTable upsets={upsets} />
    </>
  )
}

function HeadToHeadMatrix(props: { format: GameFormat }) {
  const query = useQuery({
    queryKey: ["ratingsHeadToHead", props.format],
    queryFn: () =>
      Client.getHeadToHeadApiPlayerRatingsHeadToHeadGet(
        props.format === "All" ? {} : { gameFormat: props.format },
      ),
  })
  const fallback = queryFallback(query, "the head-to-head matrix")
  if (fallback) return fallback
  const h2h = query.data as { [k: string]: { [k: string]: HeadToHead } }

  const players = Object.keys(h2h).sort()

  const cellColor = (wins: number, losses: number): string => {
    const total = wins + losses
    if (total === 0) return "transparent"
    const rate = wins / total
    if (rate > 0.5)
      return `rgba(76,175,80,${((rate - 0.5) * 2 * 0.6 + 0.15).toFixed(2)})`
    return `rgba(244,67,54,${((0.5 - rate) * 2 * 0.6 + 0.15).toFixed(2)})`
  }

  return (
    <>
      <Box sx={{ overflowX: "auto" }}>
        <table style={{ borderCollapse: "collapse", fontSize: 13 }}>
          <thead>
            <tr>
              <th style={{ padding: "4px 8px", textAlign: "left" }}>vs →</th>
              {players.map((p) => (
                <th
                  key={p}
                  style={{
                    padding: "4px 8px",
                    fontWeight: "bold",
                    textAlign: "center",
                    whiteSpace: "nowrap",
                  }}
                >
                  {p}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {players.map((p1) => (
              <tr key={p1}>
                <td
                  style={{
                    padding: "4px 8px",
                    fontWeight: "bold",
                    whiteSpace: "nowrap",
                  }}
                >
                  {p1}
                </td>
                {players.map((p2) => {
                  if (p1 === p2)
                    return (
                      <td
                        key={p2}
                        style={{
                          padding: "4px 8px",
                          textAlign: "center",
                          background: "#e0e0e0",
                        }}
                      >
                        —
                      </td>
                    )
                  const rec = h2h[p1]?.[p2]
                  if (!rec)
                    return (
                      <td
                        key={p2}
                        style={{
                          padding: "4px 8px",
                          textAlign: "center",
                          color: "#aaa",
                        }}
                      >
                        -
                      </td>
                    )
                  return (
                    <MuiTooltip
                      key={p2}
                      title={`${p1} vs ${p2}: ${rec.wins}W-${rec.losses}L`}
                    >
                      <td
                        style={{
                          padding: "4px 8px",
                          textAlign: "center",
                          background: cellColor(rec.wins, rec.losses),
                          cursor: "default",
                          whiteSpace: "nowrap",
                        }}
                      >
                        {rec.wins}-{rec.losses}
                      </td>
                    </MuiTooltip>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </Box>
    </>
  )
}

function FormatSelector(props: {
  format: GameFormat
  onChange: (f: GameFormat) => void
}) {
  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{
        alignItems: "center",
        mb: 2,
        p: 1,
      }}
    >
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

const MONTHS_BACK_ALL = "all"

function MonthsBackSelector(props: {
  monthsBack: MonthsBack
  onChange: (m: MonthsBack) => void
}) {
  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{
        alignItems: "center",
        mb: 2,
        p: 1,
      }}
    >
      <Typography variant="h6">Time Range:</Typography>
      <ToggleButtonGroup
        value={props.monthsBack ?? MONTHS_BACK_ALL}
        exclusive
        onChange={(_, v) => {
          if (v == null) return
          props.onChange(v === MONTHS_BACK_ALL ? null : v)
        }}
        size="small"
      >
        <ToggleButton value={MONTHS_BACK_ALL}>All</ToggleButton>
        {MONTHS_BACK_OPTIONS.map((m) => (
          <ToggleButton key={m} value={m}>
            {m}mo
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
        <Scatter name="skill" data={data} shape="triangle" fill={BRAND_COLOR}>
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
        <Bar dataKey="gameCount" fill={BRAND_COLOR} />
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

const WHR_FORMATS = ["All", "2v2", "3v3", "4v4"] as const

function WhrTable() {
  const query = useQuery({
    queryKey: ["playerSkills", WHR_FORMATS],
    queryFn: async () => {
      const results = await Promise.all(
        WHR_FORMATS.map((f) =>
          Client.getPlayerSkillsApiPlayerSkillsGet(
            f === "All" ? {} : { gameFormat: f },
          ),
        ),
      )
      const byPlayer: Record<
        string,
        Partial<Record<(typeof WHR_FORMATS)[number], number>>
      > = {}
      results.forEach((skills: PlayerSkill[], i) => {
        const fmt = WHR_FORMATS[i]
        for (const s of skills) {
          if (!byPlayer[s.name]) byPlayer[s.name] = {}
          byPlayer[s.name][fmt] = s.skill
        }
      })
      return byPlayer
    },
  })
  const fallback = queryFallback(query, "skill ratings")
  if (fallback) return fallback
  const data = query.data as Record<
    string,
    Partial<Record<(typeof WHR_FORMATS)[number], number>>
  >

  const sorted = Object.entries(data).sort(
    (a, b) => (b[1].All ?? -Infinity) - (a[1].All ?? -Infinity),
  )

  return (
    <Stack spacing={1} sx={{ mb: 2 }}>
      <Typography variant="h5">Whole-History Rating</Typography>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
        }}
      >
        Skill in log-odds units (Coulom 2008). Higher = stronger; difference of
        1.0 ≈ 73% win probability.
      </Typography>
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              <TableCell>Player</TableCell>
              {WHR_FORMATS.map((f) => (
                <TableCell key={f} align="right">
                  {f}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {sorted.map(([name, skills], i) => (
              <TableRow key={name} hover>
                <TableCell>{i + 1}</TableCell>
                <TableCell>{name}</TableCell>
                {WHR_FORMATS.map((f) => (
                  <TableCell
                    key={f}
                    align="right"
                    sx={{ fontVariantNumeric: "tabular-nums" }}
                  >
                    {skills[f] != null ? skills[f]!.toFixed(2) : "—"}
                  </TableCell>
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Stack>
  )
}

export function DisplayPlayerRatingTrend() {
  const [format, setFormat] = React.useState<GameFormat>("All")
  const query = useQuery({
    queryKey: ["playerRatings", format, null],
    queryFn: () => fetchPlayerRatings(format, null),
  })
  const fallback = queryFallback(query, "rating trends")
  if (fallback) return fallback
  const playerRatings = query.data as PlayerRatingData

  const data = [...playerRatings.playerRating].sort(
    (a, b) => (b.gameCount ?? 0) - (a.gameCount ?? 0),
  )
  const form = playerRatings.playerForm ?? {}
  const trendDays = Array.from(
    new Set(data.flatMap((r) => Object.keys(r.recentDeltas ?? {}).map(Number))),
  ).sort((a, b) => a - b)

  return (
    <Page
      title="Rating Trend"
      width="narrow"
      description="Who has been on a run lately: recent results, and how far each player has climbed or slid over the last 7, 14 and 30 days."
    >
      <FormatSelector format={format} onChange={setFormat} />
      <TableContainer>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>#</TableCell>
              <TableCell>Player</TableCell>
              <TableCell align="right">Games</TableCell>
              <TableCell>Last 10 team game results</TableCell>
              {trendDays.map((d) => (
                <TableCell key={d} align="right">
                  <MuiTooltip
                    title={`Rating change over last ${d} days (× 10)`}
                  >
                    <span>{d}d</span>
                  </MuiTooltip>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {data.map((r, i) => (
              <TableRow key={r.name} hover>
                <TableCell>{i + 1}</TableCell>
                <TableCell>
                  <PlayerLabel name={r.name} />
                </TableCell>
                <TableCell
                  align="right"
                  sx={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {r.gameCount}
                </TableCell>
                <TableCell>
                  <FormDots results={form[r.name] ?? []} />
                </TableCell>
                {trendDays.map((d) => (
                  <DeltaCell key={d} delta={r.recentDeltas?.[d]} />
                ))}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Typography variant="h6" sx={{ mt: 3, mb: 0.5 }}>
        Player Synergy
      </Typography>
      <SimplePlayerSynergy />
    </Page>
  )
}

export default function DisplayPlayerRatings() {
  const [format, setFormat] = React.useState<GameFormat>("All")
  const [monthsBack, setMonthsBack] = React.useState<MonthsBack>(null)
  const query = useQuery({
    queryKey: ["playerRatings", format, monthsBack],
    queryFn: () => fetchPlayerRatings(format, monthsBack),
  })

  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"))

  const fallback = queryFallback(query, "player ratings")
  if (fallback) return fallback
  const playerRatings = query.data as PlayerRatingData
  // Loaded but empty (e.g. a narrow months-back window where nobody clears
  // the rating minimum): keep the selectors rendered so the user can switch
  // back, instead of spinning forever.
  if (playerRatings.playerRating.length === 0) {
    return (
      <Paper sx={{ flexGrow: 1, maxWidth: 2000, p: 1 }}>
        <MonthsBackSelector monthsBack={monthsBack} onChange={setMonthsBack} />
        <FormatSelector format={format} onChange={setFormat} />
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            p: 2,
          }}
        >
          No rated players for this format / time range — ratings need a minimum
          number of games.
        </Typography>
      </Paper>
    )
  }
  const data = [...playerRatings.playerRating].sort((a, b) => b.mu - a.mu)
  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000, p: 1 }}>
      <MonthsBackSelector monthsBack={monthsBack} onChange={setMonthsBack} />
      <Accordion
        disableGutters
        defaultExpanded={false}
        slotProps={{ transition: { unmountOnExit: true } }}
      >
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Whole-History Rating</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <WhrTable />
        </AccordionDetails>
      </Accordion>
      <FormatSelector format={format} onChange={setFormat} />
      <Typography variant="h4">Player Ratings</Typography>
      <PlayerLeaderboard data={data} form={playerRatings.playerForm ?? {}} />
      <SkillScatterChart data={data} isMobile={isMobile} />
      <GameCountBarChart data={data} isMobile={isMobile} />
      <Typography variant="h6" sx={{ mt: 2 }}>
        Recent Upsets
      </Typography>
      <RecentUpsets format={format} />
      <Typography variant="h6" sx={{ mt: 2 }}>
        Biggest Upsets
      </Typography>
      <BiggestUpsets format={format} />
      <Typography variant="h6" sx={{ mt: 2 }}>
        Head-to-Head
      </Typography>
      <HeadToHeadMatrix format={format} />
      <Accordion disableGutters sx={{ mt: 2 }}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography variant="h6">Ratings Over Time</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <RatingsOverTime data={playerRatings} />
        </AccordionDetails>
      </Accordion>
    </Paper>
  )
}
