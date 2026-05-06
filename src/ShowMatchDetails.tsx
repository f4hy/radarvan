import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import { alpha } from "@mui/material/styles"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import Typography from "@mui/material/Typography"
import _ from "lodash"
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  Legend,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  Cell,
} from "recharts"
import CostBreakdown from "./CostBreakdown"
import ShowPlayerSummaries from "./Summary"
import { Client } from "./Client"
import {
  KillEventOutput,
  MatchDetails,
  Upgrades,
  APM,
  PlayerSummary,
  FirstBlood,
} from "./api"
import GameMap from "./Map"
import { Alert, Stack } from "@mui/material"
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

function getDetails(
  id: number,
  callback: (m: MatchDetails) => void,
  onError = console.error,
) {
  Client.getMatchDetailsApiDetailsMatchIdGet({ matchId: id })
    .then(callback)
    .catch(onError)
}

const shapes: (
  | "circle"
  | "cross"
  | "diamond"
  | "square"
  | "star"
  | "triangle"
)[] = ["circle", "star", "square", "triangle"]

function MoneyChart(props: {
  money: { [key: string]: { [key: string]: number } }
  title: string
  playerSummaries: PlayerSummary[]
  horizontalLines?: number[]
}) {
  const lines = props.horizontalLines ?? []
  if (props.money && Object.keys(props.money).length > 0) {
    const players = Object.keys(Object.values(props.money)[0])
    const colors = buildPlayerColorMap(props.playerSummaries)
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
                stroke="blue"
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

function EventChart(props: {
  upgrades: { [name: string]: Upgrades }
  playerSummaries: PlayerSummary[]
}) {
  const names = React.useMemo(
    () => Object.keys(props.upgrades).sort((x1, x2) => x1.localeCompare(x2)),
    [props.upgrades],
  )
  const colors = buildPlayerColorMap(props.playerSummaries)
  const max = React.useMemo(
    () =>
      Math.max(
        ...Object.values(props.upgrades).map((u) =>
          Math.max(...u.upgrades.map((g) => g.atMinute)),
        ),
      ),
    [props.upgrades],
  )
  if (props.upgrades && names.length > 0) {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 5, right: 10, left: 50, bottom: 5 }}>
          {names.map((name, idx) => (
            <Scatter
              key={name}
              name={name}
              fill={_.get(colors, name)}
              data={props.upgrades[name].upgrades}
              shape={shapes[idx]}
              legendType={shapes[idx]}
            ></Scatter>
          ))}
          <XAxis
            type="number"
            dataKey="atMinute"
            domain={[0, max]}
            tickFormatter={(atMinute) => atMinute.toFixed(1) + "m"}
          />
          <YAxis
            type="number"
            dataKey="cost"
            label={{
              value: "Cost",
              position: "insideLeft",
              fontSize: 25,
              offset: -30,
              angle: -90,
            }}
          />
          <ZAxis dataKey="upgradeName" name="upgrade" />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            labelFormatter={(t) => t + "m"}
          />
          <CartesianGrid />
          <Legend />
        </ScatterChart>
      </ResponsiveContainer>
    )
  } else {
    return <div></div>
  }
}

function ApmChart(props: { apms: APM[]; playerSummaries: PlayerSummary[] }) {
  if (props.apms.length === 0) {
    return <div>APM data not yet availible</div>
  }
  const colors = buildPlayerColorMap(props.playerSummaries)
  const data = _.sortBy(props.apms, (a) => -a.apm)
  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart
        data={data}
        layout="vertical"
        margin={{ top: 5, right: 10, left: 15, bottom: 20 }}
      >
        <XAxis
          type="number"
          dataKey="apm"
          label={{ value: "Actions Per Minute", offset: 1, position: "bottom" }}
        />
        <YAxis type="category" dataKey="playerName" />
        <Bar dataKey="apm">
          {data.map((entry, index) => (
            <Cell
              key={`cell-${index}`}
              fill={_.get(colors, entry.playerName)}
            />
          ))}
        </Bar>
        <Tooltip
          cursor={false}
          formatter={(value) =>
            typeof value === "number" ? value.toFixed(1) : value
          }
        />
      </BarChart>
    </ResponsiveContainer>
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
}

function renderCash(value: number | null | undefined): string {
  if (value === null || value == undefined) {
    return "?"
  }
  return "$" + value.toLocaleString("en-US")
}

const columns: Array<{
  key: keyof StyledTableRow
  label: string
  align?: "left" | "right" | "center"
  render?: (value: StyledTableRow[keyof StyledTableRow]) => React.ReactNode
}> = [
  { key: "player", label: "Player" },
  { key: "team", label: "Team" },
  {
    key: "won",
    label: "Won",
    render: (value) => (value ? "✅" : "❌"),
  },
  {
    key: "general",
    label: "Side",
    render: (v) => {
      const s = String(v ?? "")
      return s.split(" ").length > 1 ? s.split(" ")[1] : s
    },
  },
  { key: "xp", label: "XP" },
  { key: "unitsBuilt", label: "🛻 Built" },
  { key: "buildingsBuilt", label: "🏢 Built" },
  { key: "unitsLost", label: "🛻 Lost" },
  { key: "buildingsLost", label: "🏢 Lost" },
  { key: "unitsKilled", label: "🛻 Killed" },
  { key: "buildingsKilled", label: "🏢 Killed" },
  { key: "tech_buildings_captured", label: "⭐ 🚩" },
  { key: "faction_buildings_captured", label: "🏢 🚩" },
  {
    key: "moneySpent",
    label: "$ Spent",
    align: "right",
    render: (v) => renderCash(v as number | null),
  },
  {
    key: "moneyCollected",
    label: "$ Collected",
    align: "right",
    render: (v) => renderCash(v as number | null),
  },
  {
    key: "valueDestroyed",
    label: "$ Destroyed",
    align: "right",
    render: (v) => renderCash(v as number),
  },
  {
    key: "valueLost",
    label: "$ Lost",
    align: "right",
    render: (v) => renderCash(v as number),
  },
]

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
      return {
        player: s.name,
        team: s.team,
        color: s.color,
        won: s.win,
        general: s.side,
        moneySpent: extractFromStatsData("money_spent", s.name),
        moneyCollected: extractFromStatsData("money_earned", s.name),
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
            {columns.map((column) => (
              <TableCell key={column.key} align={column.align}>
                <TableSortLabel
                  active={column.key === sortBy}
                  direction={"desc"}
                  onClick={() => setSortBy(column.key)}
                >
                  {column.label}
                </TableSortLabel>
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {sortedData.map((row, index) => (
            <TableRow
              key={index}
              sx={{ backgroundColor: alpha(getColorHex(row.color), 0.3) }}
            >
              {columns.map((column) => (
                <TableCell key={column.key} align={column.align}>
                  {column.render
                    ? column.render(row[column.key])
                    : row[column.key]}
                </TableCell>
              ))}
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
      <ApmChart apms={details.apms} playerSummaries={details.playerSummary} />
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

type Displays =
  | "Player Unit and spending breakdown"
  | "Event Chart"
  | "Detailed Graphs"
  | "Kill Map"

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
      <Typography>Select which detailed charts to show</Typography>
      <ToggleButtonGroup
        exclusive
        value={props.selectedDisplay}
        onChange={handleChange}
        color="primary"
      >
        {props.choices.map((v) => (
          <ToggleButton key={v} size="large" value={v}>
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
          upgrades={props.details.upgradeEvents}
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
