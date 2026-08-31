import Tab from "@mui/material/Tab"
import Tabs from "@mui/material/Tabs"
import { alpha } from "@mui/material/styles"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import Typography from "@mui/material/Typography"
import orderBy from "lodash/orderBy"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  Cell,
  Legend,
  Line,
  LineChart,
  LabelList,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import CostBreakdown from "./CostBreakdown"
import ShowPlayerSummaries from "./Summary"
import { MatchesClient } from "./clients/matches"
import type {
  KillEventOutput,
  MatchDetails,
  APM,
  PlayerSummary,
  FirstBlood,
  BuildOrder,
  BuildOrderEntry,
  TimelineEvent,
} from "./api"
import GameMap, { useMapSupplyTotal } from "./Map"
import ReplayPlayback from "./ReplayPlayback"
import AIPredictions from "./AIPredictions"
import { Alert, Stack, Tooltip as MuiTooltip } from "@mui/material"
import UpgradeIcon from "@mui/icons-material/Upgrade"
import StarIcon from "@mui/icons-material/Star"
import BoltIcon from "@mui/icons-material/Bolt"
import ConstructionIcon from "@mui/icons-material/Construction"
import WhatshotIcon from "@mui/icons-material/Whatshot"
import BatteryAlertIcon from "@mui/icons-material/BatteryAlert"
import GpsFixedIcon from "@mui/icons-material/GpsFixed"
import CancelIcon from "@mui/icons-material/Cancel"
import FlagIcon from "@mui/icons-material/Flag"
import RadarIcon from "@mui/icons-material/Radar"
import MovieIcon from "@mui/icons-material/Movie"
import CrisisAlertIcon from "@mui/icons-material/CrisisAlert"
import ShieldIcon from "@mui/icons-material/Shield"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import { queryFallback } from "./QueryState"
import MatchNarrative from "./MatchNarrative"
import Box from "@mui/material/Box"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TableSortLabel from "@mui/material/TableSortLabel"
import { buildPlayerColorMap, formatCash, getColorHex } from "./utils"
import { BRAND_COLOR } from "./theme"

function MoneyChart(props: {
  money: { [key: string]: { [key: string]: number } }
  title: string
  playerSummaries: PlayerSummary[]
  horizontalLines?: number[]
}) {
  const lines = props.horizontalLines ?? []
  if (props.money && Object.keys(props.money).length > 0) {
    const players = Object.keys(Object.values(props.money)[0])
    const colors = buildPlayerColorMap(props.playerSummaries, getColorHex)
    // atMinute must be numeric (the XAxis is type="number") and the rows must
    // be sorted by time — object key order isn't guaranteed (e.g. after a
    // Postgres jsonb round-trip), and unsorted points draw zig-zag lines.
    const data = Object.entries(props.money)
      .map(([atMinute, values]) => ({
        ...values,
        atMinute: Number(atMinute),
      }))
      .sort((a, b) => a.atMinute - b.atMinute)
    const max = Object.values(props.money).reduce((acc, cur) => {
      return Math.max(acc, ...Object.values(cur))
    }, 0)
    const max_time = Math.max(...Object.keys(props.money).map((k) => Number(k)))
    return (
      <>
        <Typography variant="h5">{props.title}</Typography>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            title={props.title}
            height={300}
            data={data}
            margin={{ top: 5, right: 10, left: 50, bottom: 5 }}
          >
            <XAxis
              type="number"
              dataKey="atMinute"
              domain={[0, max_time]}
              tickFormatter={(atMinute) => `${atMinute.toFixed(1)}m`}
              name="minutes"
            />
            <YAxis
              label={{
                value: props.title,
                position: "insideLeft",
                fontSize: 25,
                offset: -30,
                angle: -90,
              }}
              domain={[0, max]}
            />
            <Tooltip labelFormatter={(t) => `${Number(t).toFixed(1)}m`} />
            <Legend />
            {players.map((n, _i) => (
              <Line
                key={n}
                dataKey={n}
                strokeWidth={2.5}
                stroke={colors[n]}
                dot={false}
              />
            ))}
            {lines.map((value, i) => (
              <ReferenceLine
                key={value}
                y={value}
                label={{ value: `${i + 2}⭐`, position: "insideLeft" }}
                stroke={BRAND_COLOR}
                strokeDasharray="3 3"
              />
            ))}
          </LineChart>
        </ResponsiveContainer>
      </>
    )
  } else {
    return <div>{props.title} data unavailable for this replay</div>
  }
}

// Single source of truth for timeline event types: label, row (shared
// Y-axis lane), and the icon to render. Row order in this list also
// defines the per-player lane ordering.
const EVENT_TYPES = [
  { type: "upgrade", label: "Upgrade", row: "upgrades", icon: UpgradeIcon },
  { type: "rank_up", label: "Rank Up", row: "rank ups", icon: StarIcon },
  {
    type: "generals_power",
    label: "Generals Power",
    row: "powers",
    icon: BoltIcon,
  },
  {
    type: "superweapon_built",
    label: "Superweapon Built",
    row: "superweapon",
    icon: ConstructionIcon,
  },
  {
    type: "superweapon_activated",
    label: "Superweapon Activated",
    row: "superweapon",
    icon: WhatshotIcon,
  },
  {
    type: "search_and_destroy",
    label: "Search & Destroy",
    row: "battle plans",
    icon: GpsFixedIcon,
  },
  {
    type: "low_power",
    label: "Low Power",
    row: "energy",
    icon: BatteryAlertIcon,
  },
  {
    type: "first_radar",
    label: "First Radar",
    row: "scouting",
    icon: RadarIcon,
  },
  {
    type: "tech_capture",
    label: "Tech Capture",
    row: "captures",
    icon: FlagIcon,
  },
  {
    type: "hunted",
    label: "Hunted",
    row: "hunted",
    icon: CrisisAlertIcon,
  },
  {
    type: "unhunted",
    label: "No Longer Hunted",
    row: "hunted",
    icon: ShieldIcon,
  },
  {
    type: "player_eliminated",
    label: "Eliminated",
    row: "eliminations",
    icon: CancelIcon,
  },
] as const satisfies readonly {
  type: string
  label: string
  row: string
  icon: React.ElementType
}[]

const EVENT_TYPE_BY_KEY = Object.fromEntries(
  EVENT_TYPES.map((m) => [m.type, m]),
) as Record<string, (typeof EVENT_TYPES)[number]>

const ROW_ORDER = [...new Set(EVENT_TYPES.map((m) => m.row))]

function EventChart(props: {
  timelineEvents: TimelineEvent[]
  playerSummaries: PlayerSummary[]
}) {
  // The backend (timeline_events.py) owns the event_type vocabulary; drop any
  // type this bundle doesn't know yet so a newer backend (or stale bundle)
  // can't crash the chart on EVENT_TYPE_BY_KEY[unknown].
  const events = React.useMemo(
    () => props.timelineEvents.filter((e) => e.eventType in EVENT_TYPE_BY_KEY),
    [props.timelineEvents],
  )
  const colors = buildPlayerColorMap(props.playerSummaries, getColorHex)
  const max = Math.max(0, ...events.map((e) => e.atMinute))
  const grouped = React.useMemo(() => {
    const players = Array.from(new Set(events.map((e) => e.playerName))).sort(
      (a, b) => a.localeCompare(b),
    )
    const byPlayerThenRow = new Map<string, Map<string, TimelineEvent[]>>()
    for (const e of events) {
      const row = EVENT_TYPE_BY_KEY[e.eventType].row
      const rows =
        byPlayerThenRow.get(e.playerName) ?? new Map<string, TimelineEvent[]>()
      const bucket = rows.get(row) ?? []
      bucket.push(e)
      rows.set(row, bucket)
      byPlayerThenRow.set(e.playerName, rows)
    }
    return players.map((player) => {
      const rowMap = byPlayerThenRow.get(player) ?? new Map()
      const lanes = ROW_ORDER.filter(
        (r) => (rowMap.get(r) ?? []).length > 0,
      ).map((r) => ({
        row: r,
        events: (rowMap.get(r) as TimelineEvent[]) ?? [],
      }))
      return { player, lanes }
    })
  }, [events])
  if (events.length === 0) {
    return null
  }
  const tickInterval = max > 30 ? 10 : max > 15 ? 5 : max > 5 ? 2 : 1
  const ticks: number[] = []
  for (let t = 0; t <= max; t += tickInterval) ticks.push(t)
  const LABEL_WIDTH = 200
  const pct = (m: number) => (max > 0 ? (m / max) * 100 : 0)
  return (
    <Paper variant="outlined" sx={{ p: 2, mt: 2 }}>
      <Typography variant="h5" sx={{ mb: 1 }}>
        Event Timeline
      </Typography>
      <Box sx={{ display: "flex", alignItems: "flex-end", mb: 0.5 }}>
        <Box sx={{ width: LABEL_WIDTH, flexShrink: 0 }} />
        <Box
          sx={{
            flex: 1,
            position: "relative",
            height: 20,
            borderBottom: 1,
            borderColor: "divider",
          }}
        >
          {ticks.map((t) => (
            <Box
              key={t}
              sx={{
                position: "absolute",
                left: `${pct(t)}%`,
                transform: "translateX(-50%)",
                bottom: 0,
              }}
            >
              <Typography
                variant="caption"
                sx={{
                  color: "text.secondary",
                }}
              >
                {t}m
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>
      <Stack divider={<Divider sx={{ my: 0.5 }} />}>
        {grouped.map(({ player, lanes }) => {
          const playerColor = colors[player] ?? "#888"
          return (
            <Box key={player} sx={{ py: 0.5 }}>
              <Stack
                direction="row"
                spacing={0.75}
                sx={{
                  alignItems: "center",
                  mb: 0.5,
                }}
              >
                <Box
                  sx={{
                    width: 10,
                    height: 10,
                    borderRadius: "50%",
                    bgcolor: playerColor,
                  }}
                />
                <Typography variant="subtitle2">{player}</Typography>
              </Stack>
              <Stack spacing={0.5}>
                {lanes.map(({ row, events: laneEvents }) => (
                  <Box
                    key={row}
                    sx={{
                      display: "flex",
                      alignItems: "center",
                      minHeight: 24,
                    }}
                  >
                    <Box sx={{ width: LABEL_WIDTH, flexShrink: 0, pr: 1 }}>
                      <Typography
                        variant="caption"
                        sx={{
                          color: "text.secondary",
                        }}
                      >
                        {row}
                      </Typography>
                    </Box>
                    <Box
                      sx={{
                        flex: 1,
                        position: "relative",
                        height: 24,
                        borderRadius: 0.5,
                        bgcolor: "action.hover",
                      }}
                    >
                      {laneEvents.map((e, i) => {
                        const meta = EVENT_TYPE_BY_KEY[e.eventType]
                        const Icon = meta.icon
                        const title = `${e.eventName} · ${meta.label} · ${e.atMinute.toFixed(2)}m${e.cost ? ` · $${e.cost}` : ""}`
                        return (
                          // biome-ignore lint/suspicious/noArrayIndexKey: events are positioned along a fixed timeline and the list is rebuilt whole.
                          <MuiTooltip key={i} title={title} arrow>
                            <Box
                              sx={{
                                position: "absolute",
                                left: `${pct(e.atMinute)}%`,
                                top: "50%",
                                transform: "translate(-50%, -50%)",
                                cursor: "pointer",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                width: 22,
                                height: 22,
                                borderRadius: "50%",
                                bgcolor: playerColor,
                                color: "white",
                                boxShadow: 1,
                                "&:hover": {
                                  transform: "translate(-50%, -50%) scale(1.2)",
                                },
                                transition: "transform 0.1s",
                              }}
                            >
                              <Icon sx={{ fontSize: 14 }} />
                            </Box>
                          </MuiTooltip>
                        )
                      })}
                    </Box>
                  </Box>
                ))}
              </Stack>
            </Box>
          )
        })}
      </Stack>
      <Stack
        direction="row"
        spacing={2}
        sx={{
          alignItems: "center",
          mt: 1.5,
          flexWrap: "wrap",
        }}
      >
        {EVENT_TYPES.map(({ type, label, icon: Icon }) => {
          return (
            <Stack
              key={type}
              direction="row"
              spacing={0.5}
              sx={{
                alignItems: "center",
              }}
            >
              <Box
                sx={{
                  width: 18,
                  height: 18,
                  borderRadius: "50%",
                  bgcolor: "grey.600",
                  color: "white",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                <Icon sx={{ fontSize: 12 }} />
              </Box>
              <Typography variant="caption">{label}</Typography>
            </Stack>
          )
        })}
      </Stack>
    </Paper>
  )
}

function ApmChart(props: {
  apmOverTime: { [key: string]: { [key: string]: number } }
  apms: APM[]
  playerSummaries: PlayerSummary[]
}) {
  const minuteKeys = Object.keys(props.apmOverTime)
  if (minuteKeys.length === 0) {
    return <div>APM data not available for this replay</div>
  }
  const players = Object.keys(Object.values(props.apmOverTime)[0])
  const colors = buildPlayerColorMap(props.playerSummaries, getColorHex)
  const data: { atMinute: number; [player: string]: number }[] = Object.entries(
    props.apmOverTime,
  )
    .map(([atMinute, values]) => ({
      ...values,
      atMinute: Number(atMinute),
    }))
    .sort((a, b) => a.atMinute - b.atMinute)
  const averageByPlayer = new Map(props.apms.map((a) => [a.playerName, a.apm]))
  const seriesMax = data.reduce(
    (acc, row) => Math.max(acc, ...players.map((p) => row[p] ?? 0)),
    0,
  )
  // Include the average lines in the domain, but ignore pathological outliers
  // so a single bad average can't collapse the whole chart (a degenerate
  // active window used to yield averages in the hundreds of millions). Averages
  // can legitimately exceed the per-minute series max, so allow generous slack.
  const saneAverages = Array.from(averageByPlayer.values()).filter(
    (v) => Number.isFinite(v) && v <= seriesMax * 5,
  )
  const max = Math.max(seriesMax, ...saneAverages, 0)
  const maxTime = data[data.length - 1].atMinute
  return (
    <>
      <Typography variant="h5">
        APM Over Time (10s windows, dotted = match average)
      </Typography>
      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          data={data}
          margin={{ top: 5, right: 10, left: 50, bottom: 5 }}
        >
          <XAxis
            type="number"
            dataKey="atMinute"
            domain={[0, maxTime]}
            tickFormatter={(t) => `${t.toFixed(0)}m`}
            name="minutes"
          />
          <YAxis
            label={{
              value: "APM",
              position: "insideLeft",
              fontSize: 25,
              offset: -30,
              angle: -90,
            }}
            domain={[0, max]}
          />
          <Tooltip
            labelFormatter={(t) => `${Number(t).toFixed(0)}m`}
            formatter={(value) =>
              typeof value === "number" ? value.toFixed(0) : value
            }
          />
          <Legend />
          {players.map((n) => (
            <Line
              key={n}
              dataKey={n}
              strokeWidth={2}
              stroke={colors[n]}
              dot={false}
            />
          ))}
          {players.map((n) => {
            const avg = averageByPlayer.get(n)
            if (avg === undefined) return null
            return (
              <ReferenceLine
                key={`avg-${n}`}
                y={avg}
                stroke={colors[n]}
                strokeDasharray="4 4"
                strokeWidth={1.5}
                ifOverflow="hidden"
                label={{
                  value: `${n} avg ${avg.toFixed(1)}`,
                  position: "right",
                  fill: colors[n],
                  fontSize: 11,
                }}
              />
            )
          })}
        </LineChart>
      </ResponsiveContainer>
    </>
  )
}

function DisplayFirstBlood(props: {
  first_blood?: FirstBlood
  building_first_blood?: FirstBlood
}) {
  if (props.first_blood === undefined) {
    return <></>
  }
  const msgs = [
    `${props.first_blood.attacker} drew first blood on ${props.first_blood.victim} at ${props.first_blood.atMinute.toFixed(2)} minutes`,
  ]
  if (props.building_first_blood) {
    msgs.push(
      `${props.building_first_blood.attacker} drew first building blood on ${props.building_first_blood.victim} at ${props.building_first_blood.atMinute.toFixed(2)} minutes`,
    )
  }
  return (
    <Stack
      direction="row"
      spacing={0}
      sx={{
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      {msgs.map((m) => (
        <Alert key={m} severity="warning" sx={{ width: "100%" }}>
          {m}
        </Alert>
      ))}
    </Stack>
  )
}

interface StyledTableRow {
  player: string
  team: number
  won: boolean
  color: string
  general: string
  xp: number | null
  unitsBuilt: number | null
  buildingsBuilt: number | null
  unitsLost: number | null
  buildingsLost: number | null
  unitsKilled: number | null
  buildingsKilled: number | null
  tech_buildings_captured: number | null
  faction_buildings_captured: number | null
  moneySpent: number | null
  moneyCollected: number | null
  valueDestroyed: number
  valueLost: number
  efficiency: number | null
}

function renderCash(value: number | null | undefined): string {
  if (value == null) {
    return "?"
  }
  return `$${value.toLocaleString("en-US")}`
}

function renderRatio(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) {
    return "?"
  }
  return value.toFixed(2)
}

const columns: Array<{
  key: keyof StyledTableRow
  label: string
  group: string
  align?: "left" | "right" | "center"
  render?: (value: StyledTableRow[keyof StyledTableRow]) => React.ReactNode
}> = [
  { key: "player", label: "Player", group: "Player" },
  { key: "team", label: "Team", group: "Player" },
  {
    key: "won",
    label: "Won",
    group: "Player",
    render: (value) => (value ? "✅" : "❌"),
  },
  {
    key: "general",
    label: "Side",
    group: "Player",
    render: (v) => {
      const s = String(v ?? "")
      return s.split(" ").length > 1 ? s.split(" ")[1] : s
    },
  },
  { key: "xp", label: "XP", group: "XP" },
  { key: "unitsBuilt", label: "🛻 Built", group: "Built" },
  { key: "buildingsBuilt", label: "🏢 Built", group: "Built" },
  { key: "unitsLost", label: "🛻 Lost", group: "Lost" },
  { key: "buildingsLost", label: "🏢 Lost", group: "Lost" },
  { key: "unitsKilled", label: "🛻 Killed", group: "Killed" },
  { key: "buildingsKilled", label: "🏢 Killed", group: "Killed" },
  { key: "tech_buildings_captured", label: "⭐ 🚩", group: "Captured" },
  { key: "faction_buildings_captured", label: "🏢 🚩", group: "Captured" },
  {
    key: "moneySpent",
    label: "$ Spent",
    group: "Economy",
    align: "right",
    render: (v) => renderCash(v as number | null),
  },
  {
    key: "moneyCollected",
    label: "$ Collected",
    group: "Economy",
    align: "right",
    render: (v) => renderCash(v as number | null),
  },
  {
    key: "valueDestroyed",
    label: "$ Destroyed",
    group: "Economy",
    align: "right",
    render: (v) => renderCash(v as number),
  },
  {
    key: "valueLost",
    label: "$ Lost",
    group: "Economy",
    align: "right",
    render: (v) => renderCash(v as number),
  },
  {
    key: "efficiency",
    label: "Efficiency",
    group: "Economy",
    align: "right",
    render: (v) => renderRatio(v as number | null),
  },
]

// Contiguous column groups, in order, for the grouped header row.
const columnGroups: { group: string; span: number }[] = columns.reduce(
  (acc, col) => {
    const last = acc[acc.length - 1]
    if (last && last.group === col.group) last.span += 1
    else acc.push({ group: col.group, span: 1 })
    return acc
  },
  [] as { group: string; span: number }[],
)

function GameDetailsTable(props: { matchDetails: MatchDetails }) {
  const [sortBy, setSortBy] =
    React.useState<keyof StyledTableRow>("moneyCollected")
  const [sortDir, setSortDir] = React.useState<"asc" | "desc">("desc")
  const handleSort = (key: keyof StyledTableRow) => {
    if (key === sortBy) {
      setSortDir((d) => (d === "desc" ? "asc" : "desc"))
    } else {
      setSortBy(key)
      setSortDir("desc")
    }
  }

  const data: StyledTableRow[] = React.useMemo(() => {
    const { playerSummary: summaries, statsData } = props.matchDetails
    function extractFromStatsData(key: string, name: string) {
      const d = statsData[key]
      if (d === undefined) {
        return null
      }
      // Pick the value at the latest minute. Object key order isn't guaranteed
      // (e.g. after a Postgres jsonb round-trip), so select by max numeric key
      // rather than trusting the last entry.
      const entries = Object.entries(d)
      if (entries.length === 0) {
        return null
      }
      const last = entries.reduce((a, b) =>
        Number(b[0]) > Number(a[0]) ? b : a,
      )[1]
      if (last === undefined) {
        return null
      }
      return last[name]
    }
    const sumValue = (d: Record<string, { totalSpent: number }>) =>
      Object.values(d).reduce((acc, o) => acc + o.totalSpent, 0)
    return summaries.map((s) => {
      const valueDestroyed =
        sumValue(s.unitsDestroyed ?? {}) + sumValue(s.buildingsDestroyed ?? {})
      const valueLost =
        sumValue(s.unitsLost ?? {}) + sumValue(s.buildingsLost ?? {})
      const moneyCollected = extractFromStatsData("money_earned", s.name)
      const efficiency =
        moneyCollected && moneyCollected > 0
          ? valueDestroyed / moneyCollected
          : null
      return {
        player: s.name,
        team: s.team,
        color: s.color,
        won: s.win,
        general: s.side,
        moneySpent: extractFromStatsData("money_spent", s.name),
        moneyCollected,
        xp: extractFromStatsData("xp", s.name),
        unitsBuilt: extractFromStatsData("units_built", s.name),
        buildingsBuilt: extractFromStatsData("buildings_built", s.name),
        unitsLost: extractFromStatsData("units_lost", s.name),
        buildingsLost: extractFromStatsData("buildings_lost", s.name),
        unitsKilled: extractFromStatsData("units_killed", s.name),
        buildingsKilled: extractFromStatsData("buildings_killed", s.name),
        tech_buildings_captured: extractFromStatsData(
          "tech_buildings_captured",
          s.name,
        ),
        faction_buildings_captured: extractFromStatsData(
          "faction_buildings_captured",
          s.name,
        ),
        valueDestroyed,
        valueLost,
        efficiency,
      }
    })
  }, [props.matchDetails])

  const sortedData = React.useMemo(
    () => orderBy(data, [sortBy], [sortDir]),
    [data, sortBy, sortDir],
  )

  return (
    <TableContainer component={Paper}>
      <Table
        stickyHeader
        size="small"
        sx={{
          "& .MuiTableCell-root": {
            px: 1,
            whiteSpace: "nowrap",
            fontSize: "0.75rem",
          },
        }}
      >
        <TableHead>
          <TableRow>
            {columnGroups.map((g, i) => (
              <TableCell
                key={g.group}
                colSpan={g.span}
                align="center"
                sx={{
                  fontWeight: 700,
                  color: "text.secondary",
                  textTransform: "uppercase",
                  fontSize: "0.62rem !important",
                  letterSpacing: "0.04em",
                  borderLeft: i === 0 ? undefined : "2px solid",
                  borderLeftColor: "divider",
                  bgcolor: "action.hover",
                }}
              >
                {g.group}
              </TableCell>
            ))}
          </TableRow>
          <TableRow>
            {columns.map((column, i) => {
              const groupStart =
                i === 0 || columns[i - 1].group !== column.group
              return (
                <TableCell
                  key={column.key}
                  align={column.align}
                  sx={{
                    borderLeft: groupStart && i !== 0 ? "2px solid" : undefined,
                    borderLeftColor: "divider",
                  }}
                >
                  <TableSortLabel
                    active={column.key === sortBy}
                    direction={column.key === sortBy ? sortDir : "desc"}
                    onClick={() => handleSort(column.key)}
                  >
                    {column.label}
                  </TableSortLabel>
                </TableCell>
              )
            })}
          </TableRow>
        </TableHead>
        <TableBody>
          {sortedData.map((row) => (
            <TableRow
              key={row.player}
              sx={{ backgroundColor: alpha(getColorHex(row.color), 0.3) }}
            >
              {columns.map((column, i) => {
                const groupStart =
                  i === 0 || columns[i - 1].group !== column.group
                return (
                  <TableCell
                    key={column.key}
                    align={column.align}
                    sx={{
                      borderLeft:
                        groupStart && i !== 0 ? "2px solid" : undefined,
                      borderLeftColor: "rgba(26, 34, 48, 0.12)",
                    }}
                  >
                    {column.render
                      ? column.render(row[column.key])
                      : row[column.key]}
                  </TableCell>
                )
              })}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function MoneyCharts(props: { details: MatchDetails }) {
  return (
    <>
      <MoneyChart
        title="Money"
        money={props.details.statsData.money}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="$ Earned"
        money={props.details.statsData.money_earned}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="$ spent"
        money={props.details.statsData.money_spent}
        playerSummaries={props.details.playerSummary}
      />
    </>
  )
}

function XpCharts(props: { details: MatchDetails }) {
  return (
    <MoneyChart
      title="XP"
      money={props.details.statsData.xp}
      playerSummaries={props.details.playerSummary}
      horizontalLines={[800, 1500, 2500, 5000]}
    />
  )
}

function UnitCharts(props: { details: MatchDetails }) {
  return (
    <>
      <MoneyChart
        title="Units Killed"
        money={props.details.statsData.units_killed}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="Units Built"
        money={props.details.statsData.units_built}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="Units Lost"
        money={props.details.statsData.units_lost}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="Buildings Killed"
        money={props.details.statsData.buildings_killed}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="Buildings Built"
        money={props.details.statsData.buildings_built}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="Buildings Lost"
        money={props.details.statsData.buildings_lost}
        playerSummaries={props.details.playerSummary}
      />
    </>
  )
}

function DetailedGraphs(props: { details: MatchDetails }) {
  const details = props.details
  return (
    <Paper>
      <ApmChart
        apmOverTime={details.apmOverTime ?? {}}
        apms={details.apms}
        playerSummaries={details.playerSummary}
      />
      <Divider />
      <CostBreakdown costs={details.costs} />
      <Divider />
      <MoneyCharts details={details} />
      <XpCharts details={details} />
      <UnitCharts details={details} />
    </Paper>
  )
}

function KillMap(props: {
  killEvents: KillEventOutput[]
  playerSummaries: PlayerSummary[]
  mapName: string
}) {
  const colors = React.useMemo(
    () => buildPlayerColorMap(props.playerSummaries, getColorHex),
    [props.playerSummaries],
  )
  const eventDots = React.useMemo(
    () =>
      props.killEvents.map((e) => ({
        x: e.x,
        y: e.y,
        color: colors[e.killerPlayer] ?? "#888",
        tooltip: `${e.killerPlayer} killed ${e.victimPlayer} (${e.killer} → ${e.victim}) @ ${e.atMinute.toFixed(2)}m`,
      })),
    [props.killEvents, colors],
  )
  if (props.killEvents.length === 0) {
    return <Typography>No kill event data for this replay</Typography>
  }
  return (
    <Box sx={{ maxWidth: "60%" }}>
      <GameMap mapname={props.mapName} eventDots={eventDots} />
      <Stack direction="row" spacing={2} sx={{ mt: 1, flexWrap: "wrap" }}>
        {props.playerSummaries.map((ps) => (
          <Stack
            // Color is unique per player in a match; names aren't (twin CPUs).
            key={`${ps.name}-${ps.color}`}
            direction="row"
            spacing={0.5}
            sx={{
              alignItems: "center",
            }}
          >
            <Box
              sx={{
                width: 12,
                height: 12,
                borderRadius: "50%",
                bgcolor: getColorHex(ps.color),
                flexShrink: 0,
              }}
            />
            <Typography variant="caption">{ps.name}</Typography>
          </Stack>
        ))}
      </Stack>
    </Box>
  )
}

const ACADEMY_ROWS: {
  key: keyof NonNullable<PlayerSummary["academy"]>
  label: string
}[] = [
  { key: "supplyCentersBuilt", label: "Supply Centers Built" },
  { key: "secondaryIncomeUnitsBuilt", label: "Secondary Income Units" },
  { key: "gatherersBuilt", label: "Gatherers Built" },
  { key: "peonsBuilt", label: "Peons Built" },
  { key: "salvageCollected", label: "Salvage Collected" },
  { key: "structuresCaptured", label: "Structures Captured" },
  { key: "structuresGarrisoned", label: "Structures Garrisoned" },
  { key: "clearedGarrisonedBuildings", label: "Buildings Cleared" },
  { key: "minesCleared", label: "Mines Cleared" },
  { key: "vehiclesDisguised", label: "Vehicles Disguised" },
  { key: "upgradesPurchased", label: "Upgrades Purchased" },
  { key: "heroesBuilt", label: "Heroes Built" },
  { key: "firestormsCreated", label: "Firestorms Created" },
  { key: "specialPowersUsed", label: "Special Powers Used" },
  { key: "generalsPointsSpent", label: "Generals Points Spent" },
  { key: "controlGroupsUsed", label: "Control Groups Used" },
  {
    key: "doubleClickAttackMoveOrdersGiven",
    label: "Double-Click Attack-Moves",
  },
  { key: "guardAbilityUsedCount", label: "Guard Ability Uses" },
]

function AcademyTable(props: { playerSummaries: PlayerSummary[] }) {
  const players = props.playerSummaries
  const anyData = players.some((p) => p.academy != null)
  if (!anyData) {
    return <Typography>No academy stats available for this replay.</Typography>
  }
  return (
    <TableContainer component={Paper}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Stat</TableCell>
            {players.map((p) => (
              // Color is unique per player in a match; names aren't (twin CPUs).
              <TableCell key={`${p.name}-${p.color}`} align="right">
                <Stack
                  direction="row"
                  spacing={0.5}
                  sx={{
                    alignItems: "center",
                    justifyContent: "flex-end",
                  }}
                >
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: "50%",
                      bgcolor: getColorHex(p.color),
                      flexShrink: 0,
                    }}
                  />
                  <span>{p.name}</span>
                </Stack>
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {ACADEMY_ROWS.map((row) => (
            <TableRow key={row.key}>
              <TableCell>{row.label}</TableCell>
              {players.map((p) => (
                <TableCell key={`${p.name}-${p.color}`} align="right">
                  {p.academy ? p.academy[row.key].toLocaleString() : "—"}
                </TableCell>
              ))}
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function fmtMinSec(min: number): string {
  const totalSec = Math.max(0, Math.round(min * 60))
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${s.toString().padStart(2, "0")}`
}

function BuildOrderColumn(props: {
  title: string
  entries: BuildOrderEntry[]
}) {
  return (
    <Box sx={{ minWidth: 180 }}>
      <Typography variant="subtitle2">{props.title}</Typography>
      {props.entries.length === 0 ? (
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          —
        </Typography>
      ) : (
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "auto 1fr",
            columnGap: 1.5,
            rowGap: 0.25,
            fontFamily: "monospace",
            fontSize: "0.875rem",
            alignItems: "baseline",
          }}
        >
          {props.entries.map((e, i) => {
            const count = e.count ?? 1
            const isRun = count > 1 && e.endMinute != null
            // Collapsed run → show the span (start–end); single build → one time.
            const when = isRun
              ? `${fmtMinSec(e.atMinute)}–${fmtMinSec(e.endMinute as number)}`
              : fmtMinSec(e.atMinute)
            // Economy/non-combat builds (workers, dozers, supply) are dimmed.
            const dim = e.isEconomy ? 0.5 : 1
            return (
              // biome-ignore lint/suspicious/noArrayIndexKey: same ordered event list as above, rendered as rows.
              <React.Fragment key={i}>
                <Box
                  sx={{
                    color: "text.secondary",
                    textAlign: "right",
                    opacity: dim,
                  }}
                >
                  {when}
                </Box>
                <Box sx={{ opacity: dim }}>
                  {e.name}
                  {count > 1 && (
                    <Box
                      component="span"
                      sx={{ color: "text.secondary", ml: 0.5 }}
                    >
                      &times;{count}
                    </Box>
                  )}
                </Box>
              </React.Fragment>
            )
          })}
        </Box>
      )}
    </Box>
  )
}

function BuildOrderTab(props: {
  buildOrders: { [name: string]: BuildOrder }
  playerSummaries: PlayerSummary[]
}) {
  const players = props.playerSummaries.filter(
    (p) => props.buildOrders[p.name] !== undefined,
  )
  if (players.length === 0) {
    return (
      <Typography>No build order data available for this replay.</Typography>
    )
  }
  return (
    <Stack
      direction="row"
      spacing={3}
      sx={{ flexWrap: "wrap", alignItems: "flex-start" }}
    >
      {players.map((p) => {
        const order = props.buildOrders[p.name]
        return (
          // Color is unique per player in a match; names aren't (twin CPUs).
          <Paper key={`${p.name}-${p.color}`} sx={{ p: 2, mb: 2 }}>
            <Stack
              direction="row"
              spacing={1}
              sx={{
                alignItems: "center",
                mb: 1,
              }}
            >
              <Box
                sx={{
                  width: 12,
                  height: 12,
                  borderRadius: "50%",
                  bgcolor: getColorHex(p.color),
                  flexShrink: 0,
                }}
              />
              <Typography variant="h6">{p.name}</Typography>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                ({p.side})
              </Typography>
            </Stack>
            <Stack direction="row" spacing={3}>
              <BuildOrderColumn title="Buildings" entries={order.buildings} />
              <BuildOrderColumn title="Units" entries={order.units} />
              <BuildOrderColumn title="Upgrades" entries={order.upgrades} />
            </Stack>
          </Paper>
        )
      })}
    </Stack>
  )
}

// details.incomeBySource is only populated when cncstats supplied the
// breakdown for this replay (newer replay versions only), and it is sparse:
// an all-zero source, a player who never earned from a source, and unchanged
// timesteps are all omitted - absent means "zero"/"unchanged", never
// "unknown" (see MatchDetails.income_by_source in radarvan/api_types.py).
type IncomeBySource = NonNullable<MatchDetails["incomeBySource"]>

// Fixed label/color per known source so a source keeps its identity across
// every player's chart regardless of which sources are active. Sources the
// backend sends that aren't listed here (theft, other, anything cncstats
// adds later) fold into a single gray "Other" band.
const KNOWN_INCOME_SOURCES: { key: string; label: string; color: string }[] = [
  { key: "supply", label: "Supply", color: "#2a78d6" },
  { key: "oil_derrick", label: "Oil Derrick", color: "#1baf7a" },
  { key: "black_market", label: "Black Market", color: "#eda100" },
  { key: "hacker", label: "Hacker", color: "#008300" },
  { key: "crate", label: "Crate", color: "#4a3aa7" },
  { key: "salvage", label: "Salvage", color: "#e34948" },
  { key: "bounty", label: "Bounty", color: "#e87ba4" },
  { key: "supply_drop", label: "Supply Drop", color: "#eb6834" },
]
const KNOWN_INCOME_KEYS = new Set(KNOWN_INCOME_SOURCES.map((s) => s.key))
const INCOME_OTHER_COLOR = "#898781"
const INCOME_OTHER_LABEL = "Other"

function incomeSourceColor(key: string): string {
  return (
    KNOWN_INCOME_SOURCES.find((s) => s.key === key)?.color ?? INCOME_OTHER_COLOR
  )
}

// Shared time grid: union of every source's minute keys. Every non-empty
// series shares this same sparse grid (see radarvan.stats_extraction).
function incomeMinutes(income: IncomeBySource): number[] {
  const all = new Set<number>()
  for (const series of Object.values(income)) {
    for (const m of Object.keys(series)) {
      all.add(Number(m))
    }
  }
  return [...all].sort((a, b) => a - b)
}

function playerHasIncomeFrom(
  series: IncomeBySource[string] | undefined,
  playerName: string,
): boolean {
  return Object.values(series ?? {}).some(
    (byPlayer) => (byPlayer[playerName] ?? 0) !== 0,
  )
}

// Gates both the "Income by Source" and "Econ" tabs (only present when
// cncstats supplied the breakdown for this replay).
function hasIncomeBySourceData(details: MatchDetails): boolean {
  return Object.keys(details.incomeBySource ?? {}).length > 0
}

function PlayerIncomeChart(props: {
  playerName: string
  income: IncomeBySource
  minutes: number[]
  yMax: number
}) {
  const { playerName, income, minutes, yMax } = props
  const { sources, otherKeys, data } = React.useMemo(() => {
    // Sources this player never earned from are dropped from their chart (no
    // flat zero bands); the source->color mapping stays fixed match-wide.
    const sources = KNOWN_INCOME_SOURCES.filter((s) =>
      playerHasIncomeFrom(income[s.key], playerName),
    )
    const otherKeys = Object.keys(income).filter(
      (k) =>
        !KNOWN_INCOME_KEYS.has(k) && playerHasIncomeFrom(income[k], playerName),
    )
    // Decode the sparse series over the shared grid with last-value carry
    // forward - correct for cumulative data, and robust even if the backend
    // ever emits per-source grids.
    const last: Record<string, number> = {}
    const data = minutes.map((m) => {
      const row: Record<string, number> = { atMinute: m }
      for (const s of sources) {
        const v = income[s.key]?.[m]?.[playerName]
        if (v !== undefined) last[s.key] = v
        row[s.label] = last[s.key] ?? 0
      }
      let otherSum = 0
      for (const k of otherKeys) {
        const v = income[k]?.[m]?.[playerName]
        if (v !== undefined) last[k] = v
        otherSum += last[k] ?? 0
      }
      if (otherKeys.length > 0) {
        row[INCOME_OTHER_LABEL] = otherSum
      }
      return row
    })
    return { sources, otherKeys, data }
  }, [playerName, income, minutes])
  if (sources.length === 0 && otherKeys.length === 0) {
    return null
  }
  const maxTime = minutes.length > 0 ? minutes[minutes.length - 1] : 0
  return (
    <>
      <Typography variant="h6">{playerName}</Typography>
      <ResponsiveContainer width="100%" height={260}>
        <AreaChart
          data={data}
          margin={{ top: 5, right: 10, left: 50, bottom: 5 }}
        >
          <XAxis
            type="number"
            dataKey="atMinute"
            domain={[0, maxTime]}
            tickFormatter={(atMinute) => `${atMinute.toFixed(1)}m`}
            name="minutes"
          />
          <YAxis domain={[0, yMax]} />
          <Tooltip labelFormatter={(t) => `${Number(t).toFixed(1)}m`} />
          <Legend />
          {sources.map((s) => (
            <Area
              key={s.key}
              type="monotone"
              dataKey={s.label}
              stackId="income"
              stroke={s.color}
              fill={s.color}
            />
          ))}
          {otherKeys.length > 0 && (
            <Area
              type="monotone"
              dataKey={INCOME_OTHER_LABEL}
              stackId="income"
              stroke={INCOME_OTHER_COLOR}
              fill={INCOME_OTHER_COLOR}
            />
          )}
          <ReferenceLine
            y={yMax}
            label={{ value: "highest $ collected", position: "insideTopRight" }}
            stroke={BRAND_COLOR}
            strokeDasharray="3 3"
          />
        </AreaChart>
      </ResponsiveContainer>
    </>
  )
}

function IncomeBySourceTab(props: { details: MatchDetails }) {
  const income = props.details.incomeBySource ?? {}
  const minutes = React.useMemo(() => incomeMinutes(income), [income])
  const mapSupplyTotal = useMapSupplyTotal(props.details.mapName ?? "")
  if (!hasIncomeBySourceData(props.details)) {
    return <Typography>No income-by-source data for this replay</Typography>
  }
  // Common y-axis ceiling: the highest "$ Collected" of any player - the
  // final cumulative money_earned the API already ships per player (same
  // figure as the GameDetailsTable column) - so every chart is on the same
  // scale and directly comparable.
  const yMax = Math.max(
    0,
    ...Object.values(props.details.playerMoneyCollected ?? {}),
  )
  return (
    <>
      {!!mapSupplyTotal && (
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 1 }}>
          Total map supply: {formatCash(mapSupplyTotal)}
        </Typography>
      )}
      {props.details.playerSummary.map((ps) => (
        <PlayerIncomeChart
          // Color is unique per player in a match; names aren't (twin CPUs).
          key={`${ps.name}-${ps.color}`}
          playerName={ps.name}
          income={income}
          minutes={minutes}
          yMax={yMax}
        />
      ))}
    </>
  )
}

// Three broad economy categories from the same income_by_source breakdown,
// using only the final (last snapshot) cumulative value per player - a
// simple totals comparison rather than the time-series detail of the
// "Income by Source" tab. Supplies/Oil colors are looked up from
// KNOWN_INCOME_SOURCES (not re-declared) so the two tabs can't drift apart.
const SUPPLY_INCOME_KEYS = ["supply", "crate"]
const OIL_INCOME_KEY = "oil_derrick"
const SECONDARY_ECONOMY_LABEL = "Secondary Economy"
const SECONDARY_ECONOMY_COLOR = "#eda100" // yellow - a composite bucket, not a single known source

function econCategories(
  secondaryKeys: string[],
): { label: string; keys: string[]; color: string }[] {
  return [
    {
      label: "Supplies",
      keys: SUPPLY_INCOME_KEYS,
      color: incomeSourceColor("supply"),
    },
    {
      label: "Oil Derricks",
      keys: [OIL_INCOME_KEY],
      color: incomeSourceColor("oil_derrick"),
    },
    {
      label: SECONDARY_ECONOMY_LABEL,
      keys: secondaryKeys,
      color: SECONDARY_ECONOMY_COLOR,
    },
  ]
}

// Final cumulative value for one player, summed across `keys`, carrying each
// key's last-known value forward over the shared minute grid - matching
// PlayerIncomeChart's decode, and correct even for a player whose series
// ends early (e.g. left/disconnected before the match's final snapshot).
function finalValueForPlayer(
  income: IncomeBySource,
  keys: string[],
  playerName: string,
  minutes: number[],
): number {
  const last: Record<string, number> = {}
  for (const m of minutes) {
    for (const k of keys) {
      const v = income[k]?.[m]?.[playerName]
      if (v !== undefined) last[k] = v
    }
  }
  return keys.reduce((sum, k) => sum + (last[k] ?? 0), 0)
}

const UNCOLLECTED_COLOR = "#9e9e9e"

// Bar height is the actual $ value collected; each bar is additionally
// labeled with that player's share either of the map's total available
// supply cash (`totalOverride`, when known - see mapparse's `supply` data)
// or, absent that, of what these players collected between them this match.
function PercentOfTotalChart(props: {
  title: string
  rows: { name: string; [key: string]: string | number }[]
  field: string
  colors: Record<string, string>
  totalOverride?: number
  // When set (and totalOverride leaves a positive remainder), adds a synthetic
  // bar for total - sum(collected) - e.g. supply cash still unclaimed on the map.
  remainderLabel?: string
}) {
  const rowSum = props.rows.reduce((sum, r) => sum + Number(r[props.field]), 0)
  const total = props.totalOverride ?? rowSum
  const data = props.rows
    .map((r) => {
      const value = Number(r[props.field])
      return {
        name: r.name,
        value,
        percentLabel:
          total > 0 ? `${((100 * value) / total).toFixed(1)}%` : "-",
      }
    })
    .sort((a, b) => b.value - a.value)
  const remainder = props.totalOverride !== undefined ? total - rowSum : 0
  if (props.remainderLabel && remainder > 0) {
    data.push({
      name: props.remainderLabel,
      value: remainder,
      percentLabel: `${((100 * remainder) / total).toFixed(1)}%`,
    })
  }
  return (
    <>
      <Typography variant="h6">{props.title}</Typography>
      <ResponsiveContainer width="100%" height={260}>
        <BarChart
          data={data}
          layout="horizontal"
          margin={{ top: 20, right: 10, left: 15, bottom: 5 }}
        >
          <Bar dataKey="value">
            <LabelList dataKey="percentLabel" position="top" />
            {data.map((d) => (
              <Cell
                key={d.name}
                fill={props.colors[d.name] ?? UNCOLLECTED_COLOR}
              />
            ))}
          </Bar>
          <XAxis dataKey="name" />
          <YAxis
            label={{
              value: "$ collected",
              position: "insideLeft",
              offset: -5,
              angle: -90,
            }}
          />
          <Tooltip
            formatter={(v, _name, item) => [
              `${v} (${item.payload.percentLabel} of ${
                props.totalOverride !== undefined
                  ? "map's total supply"
                  : "collected this match"
              })`,
              "$ collected",
            ]}
            cursor={false}
          />
        </BarChart>
      </ResponsiveContainer>
    </>
  )
}

function EconTab(props: { details: MatchDetails }) {
  const income = props.details.incomeBySource ?? {}
  const minutes = React.useMemo(() => incomeMinutes(income), [income])
  const mapSupplyTotal = useMapSupplyTotal(props.details.mapName ?? "")
  const secondaryKeys = React.useMemo(
    () =>
      Object.keys(income).filter(
        (k) => !SUPPLY_INCOME_KEYS.includes(k) && k !== OIL_INCOME_KEY,
      ),
    [income],
  )
  const categories = React.useMemo(
    () => econCategories(secondaryKeys),
    [secondaryKeys],
  )
  const colors = buildPlayerColorMap(props.details.playerSummary, getColorHex)
  const data = React.useMemo(
    () =>
      props.details.playerSummary.map((ps) => {
        const row: { name: string; [key: string]: string | number } = {
          name: ps.name,
        }
        for (const c of categories) {
          row[c.label] = finalValueForPlayer(income, c.keys, ps.name, minutes)
        }
        return row
      }),
    [props.details.playerSummary, income, minutes, categories],
  )
  if (!hasIncomeBySourceData(props.details)) {
    return <Typography>No econ data for this replay</Typography>
  }
  return (
    <>
      {!!mapSupplyTotal && (
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 1 }}>
          Total map supply: {formatCash(mapSupplyTotal)}
        </Typography>
      )}
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={data}
          layout="horizontal"
          margin={{ top: 5, right: 10, left: 15, bottom: 5 }}
        >
          {categories.map((c) => (
            <Bar
              key={c.label}
              dataKey={c.label}
              stackId="econ"
              fill={c.color}
            />
          ))}
          <XAxis dataKey="name" />
          <YAxis
            label={{
              value: "$ collected",
              position: "insideLeft",
              offset: -5,
              angle: -90,
            }}
          />
          <Tooltip />
          <Legend />
        </BarChart>
      </ResponsiveContainer>
      <Divider />
      {categories.map((c) => {
        const totalOverride =
          c.label === "Supplies" && mapSupplyTotal ? mapSupplyTotal : undefined
        return (
          <PercentOfTotalChart
            key={c.label}
            title={`${c.label} - % of ${totalOverride ? "map's total supply" : "collected this match"}`}
            rows={data}
            field={c.label}
            colors={colors}
            totalOverride={totalOverride}
            remainderLabel={totalOverride ? "Uncollected" : undefined}
          />
        )
      })}
    </>
  )
}

type Displays =
  | "Player Unit and spending breakdown"
  | "Event Chart"
  | "Detailed Graphs"
  | "Income by Source"
  | "Econ"
  | "Kill Map"
  | "Replay"
  | "AI"
  | "Academy"
  | "Build Order"

// The tab strip's labels. The `Displays` string stays the switch key below;
// only the rendered label is shortened, because a tab has to fit in a row of
// ten and "Player Unit and spending breakdown" is a sentence.
const DISPLAY_LABELS: Partial<Record<Displays, React.ReactNode>> = {
  "Player Unit and spending breakdown": "Units & Spending",
  AI: "🤖 AI",
  Replay: (
    <Stack
      direction="row"
      spacing={0.5}
      sx={{
        alignItems: "center",
      }}
    >
      <MovieIcon fontSize="small" />
      <span>Replay</span>
    </Stack>
  ),
}

/**
 * The detail views, as a tab strip with the first one already open.
 *
 * This was ten unselected toggle buttons over an empty panel: expanding a match
 * showed a wall of options and nothing to read, so the reader had to guess
 * which button held what they came for. A tab strip says the same thing but
 * arrives already showing something, and scrolls rather than wrapping to three
 * ragged rows on a narrow window.
 */
function DetailViewSelector(props: {
  selectedDisplay: Displays
  choices: Displays[]
  onChange: (display: Displays) => void
  details: MatchDetails
}) {
  const handleChange = React.useCallback(
    (_: React.SyntheticEvent, v: Displays) => props.onChange(v),
    [props.onChange],
  )
  return (
    <>
      <Tabs
        value={props.selectedDisplay}
        onChange={handleChange}
        variant="scrollable"
        scrollButtons="auto"
        allowScrollButtonsMobile
        sx={{ borderBottom: 1, borderColor: "divider", mb: 1.5 }}
      >
        {props.choices.map((v) => (
          <Tab key={v} value={v} label={DISPLAY_LABELS[v] ?? v} />
        ))}
      </Tabs>
      {props.selectedDisplay === "Player Unit and spending breakdown" && (
        <ShowPlayerSummaries
          playerSummaries={props.details.playerSummary}
          killEvents={props.details.killEvents ?? []}
        />
      )}
      {props.selectedDisplay === "Event Chart" && (
        <EventChart
          timelineEvents={props.details.timelineEvents ?? []}
          playerSummaries={props.details.playerSummary}
        />
      )}
      {props.selectedDisplay === "Detailed Graphs" && (
        <DetailedGraphs details={props.details} />
      )}
      {props.selectedDisplay === "Income by Source" && (
        <IncomeBySourceTab details={props.details} />
      )}
      {props.selectedDisplay === "Econ" && <EconTab details={props.details} />}
      {props.selectedDisplay === "Kill Map" && (
        <KillMap
          killEvents={props.details.killEvents ?? []}
          playerSummaries={props.details.playerSummary}
          mapName={props.details.mapName ?? ""}
        />
      )}
      {props.selectedDisplay === "Replay" && (
        <ReplayPlayback
          mapName={props.details.mapName ?? ""}
          mapEvents={props.details.mapEvents ?? []}
          killEvents={props.details.killEvents ?? []}
          playerSummaries={props.details.playerSummary}
        />
      )}
      {props.selectedDisplay === "AI" && (
        <AIPredictions matchId={props.details.matchId} />
      )}
      {props.selectedDisplay === "Academy" && (
        <AcademyTable playerSummaries={props.details.playerSummary} />
      )}
      {props.selectedDisplay === "Build Order" && (
        <BuildOrderTab
          buildOrders={props.details.buildOrders ?? {}}
          playerSummaries={props.details.playerSummary}
        />
      )}
    </>
  )
}

export default function ShowMatchDetails(props: { id: number }) {
  // Not `null`: a tab strip is always on something, and the panel that opens
  // with the match is the one most people are here for.
  const [selectedDisplay, setSelectedDisplay] = React.useState<Displays>(
    "Player Unit and spending breakdown",
  )
  // Keyed on the match id, so switching matches shows the new match's details
  // rather than leaving the previous one's charts on screen under the new id —
  // and a response that lands after the id moved on belongs to its own key.
  const query = useQuery({
    queryKey: ["matchDetails", props.id],
    queryFn: () =>
      MatchesClient.getMatchDetailsApiDetailsMatchIdGet({ matchId: props.id }),
  })
  const fallback = queryFallback(query, `match #${props.id}`)
  if (fallback) return fallback
  const details = query.data as MatchDetails
  const choices: Displays[] = [
    "Player Unit and spending breakdown",
    "Event Chart",
    "Detailed Graphs",
    ...(hasIncomeBySourceData(details)
      ? (["Income by Source", "Econ"] as const)
      : []),
    "Kill Map",
    "Replay",
    "AI",
    "Academy",
    "Build Order",
  ]

  return (
    <Paper>
      <Divider />
      {/* The deterministic retelling of the match (radarvan/match_narrative.py):
          every beat is a fact from the parsed replay, no model call involved.
          Collapsible because it repeats a few things the charts below also
          show, open by default because it is the fastest way to find out what
          actually happened in a game. */}
      <Accordion defaultExpanded disableGutters elevation={0}>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography sx={{ fontWeight: 600 }}>What happened</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <MatchNarrative matchId={props.id} showHeadline={false} />
        </AccordionDetails>
      </Accordion>
      <DisplayFirstBlood
        first_blood={details.firstBlood ?? undefined}
        building_first_blood={details.buildingFirstBlood ?? undefined}
      />
      <GameDetailsTable matchDetails={details} />
      <DetailViewSelector
        selectedDisplay={selectedDisplay}
        choices={choices}
        onChange={setSelectedDisplay}
        details={details}
      />
    </Paper>
  )
}
