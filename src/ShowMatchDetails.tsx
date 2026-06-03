import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import { alpha } from "@mui/material/styles"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import Typography from "@mui/material/Typography"
import _ from "lodash"
import * as React from "react"
import {
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import CostBreakdown from "./CostBreakdown"
import ShowPlayerSummaries from "./Summary"
import { Client } from "./Client"
import {
  KillEventOutput,
  MatchDetails,
  APM,
  PlayerSummary,
  FirstBlood,
  BuildOrder,
  BuildOrderEntry,
  TimelineEvent,
} from "./api"
import GameMap from "./Map"
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
import Loading from "./Loading"
import Box from "@mui/material/Box"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TableSortLabel from "@mui/material/TableSortLabel"
import { useErrorSnackbar } from "./useErrorSnackbar"
import { buildPlayerColorMap, getColorHex } from "./utils"
import { BRAND_COLOR } from "./theme"

function getDetails(
  id: number,
  callback: (m: MatchDetails) => void,
  onError = console.error,
) {
  Client.getMatchDetailsApiDetailsMatchIdGet({ matchId: id })
    .then(callback)
    .catch(onError)
}

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
    const data = Object.entries(props.money).map(([atMinute, values]) => ({
      ...values,
      atMinute: atMinute,
    }))
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
              tickFormatter={(atMinute) => atMinute.toFixed(1) + "m"}
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
            <Tooltip labelFormatter={(t) => t.slice(0, 4) + "m"} />
            <Legend />
            {players.map((n, _i) => (
              <Line
                key={n}
                dataKey={n}
                strokeWidth={2.5}
                stroke={_.get(colors, n)}
                dot={false}
              />
            ))}
            {lines.map((value, i) => (
              <ReferenceLine
                key={i}
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
    return <div>{props.title} data unavailible for this replay</div>
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
  const events = props.timelineEvents
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
              <Typography variant="caption" color="text.secondary">
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
                alignItems="center"
                mb={0.5}
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
                      <Typography variant="caption" color="text.secondary">
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
        sx={{ mt: 1.5, flexWrap: "wrap" }}
        alignItems="center"
      >
        {EVENT_TYPES.map(({ type, label, icon: Icon }) => {
          return (
            <Stack key={type} direction="row" spacing={0.5} alignItems="center">
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
  const max = Math.max(
    data.reduce(
      (acc, row) => Math.max(acc, ...players.map((p) => row[p] ?? 0)),
      0,
    ),
    ...Array.from(averageByPlayer.values()),
  )
  const maxTime = data[data.length - 1].atMinute
  return (
    <>
      <Typography variant="h5">
        APM Over Time (1-min windows, dotted = match average)
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
            tickFormatter={(t) => t.toFixed(0) + "m"}
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
              stroke={_.get(colors, n)}
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
                stroke={_.get(colors, n)}
                strokeDasharray="4 4"
                strokeWidth={1.5}
                ifOverflow="extendDomain"
                label={{
                  value: `${n} avg ${avg.toFixed(1)}`,
                  position: "right",
                  fill: _.get(colors, n),
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
      `${props.building_first_blood.attacker} drew first building blood on ${props.building_first_blood.victim} at ${props.building_first_blood.atMinute.toFixed(2)}minutes`,
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
  if (value === null || value == undefined) {
    return "?"
  }
  return "$" + value.toLocaleString("en-US")
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
  const [sortBy, setSortBy] = React.useState<null | keyof StyledTableRow>(
    "moneyCollected",
  )

  const data: StyledTableRow[] = React.useMemo(() => {
    const { playerSummary: summaries, statsData } = props.matchDetails
    function extractFromStatsData(key: string, name: string) {
      const d = statsData[key]
      if (d === undefined) {
        return null
      }
      const vals = Object.values(d)
      const last = vals[vals.length - 1]
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
    () => (sortBy ? _.sortBy(data, sortBy) : data),
    [data, sortBy],
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
                    direction={"desc"}
                    onClick={() => setSortBy(column.key)}
                  >
                    {column.label}
                  </TableSortLabel>
                </TableCell>
              )
            })}
          </TableRow>
        </TableHead>
        <TableBody>
          {sortedData.map((row, index) => (
            <TableRow
              key={index}
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
        money={props.details.statsData["money"]}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="$ Earned"
        money={props.details.statsData["money_earned"]}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="$ spent"
        money={props.details.statsData["money_spent"]}
        playerSummaries={props.details.playerSummary}
      />
    </>
  )
}

function XpCharts(props: { details: MatchDetails }) {
  return (
    <MoneyChart
      title="XP"
      money={props.details.statsData["xp"]}
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
        money={props.details.statsData["units_killed"]}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="Units Built"
        money={props.details.statsData["units_built"]}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="Units Lost"
        money={props.details.statsData["units_lost"]}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="Buildings Killed"
        money={props.details.statsData["buildings_killed"]}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="Buildings Built"
        money={props.details.statsData["buildings_built"]}
        playerSummaries={props.details.playerSummary}
      />
      <MoneyChart
        title="Buildings Lost"
        money={props.details.statsData["buildings_lost"]}
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
            key={ps.name}
            direction="row"
            spacing={0.5}
            alignItems="center"
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
              <TableCell key={p.name} align="right">
                <Stack
                  direction="row"
                  spacing={0.5}
                  alignItems="center"
                  justifyContent="flex-end"
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
                <TableCell key={p.name} align="right">
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
          {props.entries.map((e, i) => (
            <React.Fragment key={i}>
              <Box sx={{ color: "text.secondary", textAlign: "right" }}>
                {fmtMinSec(e.atMinute)}
              </Box>
              <Box>{e.name}</Box>
            </React.Fragment>
          ))}
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
          <Paper key={p.name} sx={{ p: 2, mb: 2 }}>
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              sx={{ mb: 1 }}
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

type Displays =
  | "Player Unit and spending breakdown"
  | "Event Chart"
  | "Detailed Graphs"
  | "Kill Map"
  | "Academy"
  | "Build Order"

function DetailViewSelector(props: {
  selectedDisplay: Displays | null
  choices: Displays[]
  onChange: (display: Displays | null) => void
  details: MatchDetails
}) {
  const handleChange = React.useCallback(
    (_: React.MouseEvent<HTMLElement>, v: Displays | null) => props.onChange(v),
    [props.onChange],
  )
  return (
    <>
      <Typography variant="subtitle2" color="text.secondary" sx={{ mb: 1 }}>
        Select which detailed charts to show
      </Typography>
      <ToggleButtonGroup
        exclusive
        value={props.selectedDisplay}
        onChange={handleChange}
        color="primary"
        sx={{ flexWrap: "wrap" }}
      >
        {props.choices.map((v) => (
          <ToggleButton key={v} value={v}>
            {v}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
      <Divider />
      <Typography>{props.selectedDisplay}</Typography>
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
      {props.selectedDisplay === "Kill Map" && (
        <KillMap
          killEvents={props.details.killEvents ?? []}
          playerSummaries={props.details.playerSummary}
          mapName={props.details.mapName ?? ""}
        />
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
  const [details, setDetails] = React.useState<MatchDetails | null>(null)
  const [selectedDisplay, setSelectedDisplay] = React.useState<Displays | null>(
    null,
  )
  const { showError, errorSnackbar } = useErrorSnackbar()
  React.useEffect(() => {
    getDetails(props.id, setDetails, showError)
  }, [props.id, showError])
  if (details === null) {
    return (
      <>
        <Loading />
        {errorSnackbar}
      </>
    )
  }
  const choices: Displays[] = [
    "Player Unit and spending breakdown",
    "Event Chart",
    "Detailed Graphs",
    "Kill Map",
    "Academy",
    "Build Order",
  ]

  return (
    <Paper>
      <Divider />
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
      {errorSnackbar}
    </Paper>
  )
}
