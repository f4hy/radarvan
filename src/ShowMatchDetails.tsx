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
import { MatchDetails, Upgrades, APM, PlayerSummary, FirstBlood } from "./api"
import { Alert, Stack } from "@mui/material"
import Loading from "./Loading"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TableSortLabel from "@mui/material/TableSortLabel"

function getDetails(id: number, callback: (m: MatchDetails) => void) {
  Client.getMatchDetailsApiDetailsMatchIdGet({ matchId: id })
    .then(callback)
    .catch((e) => alert(e))
}

const empty: MatchDetails = {
  matchId: 0,
  costs: [],
  apms: [],
  upgradeEvents: {},
  spent: {
    buildings: [],
    units: [],
    upgrades: [],
    total: [],
  },
  moneyValues: {},
  moneyCollectedValues: {},
  statsData: {},
  playerSummary: [],
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
    const colors = props.playerSummaries.reduce(
      (acc, cur) => ({ ...acc, [cur.name]: cur.color }),
      {},
    )
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
            {players.map((n, i) => (
              <Line
                dataKey={n}
                strokeWidth={2.5}
                stroke={_.get(colors, n)}
                dot={false}
              />
            ))}
            {lines.map((value, i) => (
              <ReferenceLine
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
  max: number
  playerSummaries: PlayerSummary[]
}) {
  const names = Object.keys(props.upgrades).sort((x1, x2) =>
    x1.localeCompare(x2),
  )
  const colors = props.playerSummaries.reduce(
    (acc, cur) => ({ ...acc, [cur.name]: cur.color }),
    {},
  )

  if (props.upgrades && names.length > 0) {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 5, right: 10, left: 50, bottom: 5 }}>
          {names.map((name, idx) => (
            <Scatter
              name={name}
              fill={_.get(colors, name)}
              data={props.upgrades[name].upgrades}
              shape={shapes[idx]}
              legendType={shapes[idx]}
            >
              {/* <LabelList dataKey="upgradeName" position="left" formatter={labelformater} offset={100} /> */}
            </Scatter>
          ))}
          <XAxis
            type="number"
            dataKey="atMinute"
            domain={[0, props.max]}
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
  const colors = props.playerSummaries.reduce(
    (acc, cur) => ({ ...acc, [cur.name]: cur.color }),
    {},
  )
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
        <Alert severity="warning" sx={{ width: "100%" }}>
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
  moneySpent: number
  moneyCollected: number | null
}

function renderCash(value: number | null): string {
  if (value === null) {
    return "?"
  }
  return "$" + value.toLocaleString("en-US")
}

const columns: Array<{
  key: keyof StyledTableRow
  label: string
  align?: "left" | "right" | "center"
  render?: (value: any) => React.ReactNode
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
    render: (v) => (v.split(" ").length > 1 ? v.split(" ")[1] : v),
  },
  { key: "xp", label: "XP" },
  { key: "unitsBuilt", label: "🛻 Built" },
  { key: "buildingsBuilt", label: "🏢 Built" },
  { key: "unitsLost", label: "🛻 Lost" },
  { key: "buildingsLost", label: "🏢 Lost" },
  { key: "unitsKilled", label: "🛻 Killed" },
  { key: "buildingsKilled", label: "🏢 Killed" },
  { key: "tech_buildings_captured", label: "Tech Buildings Captured" },
  { key: "faction_buildings_captured", label: "Faction Buildings Captured" },
  {
    key: "moneySpent",
    label: "$ Spent",
    align: "right",
    render: renderCash,
  },
  {
    key: "moneyCollected",
    label: "$ Collected",
    align: "right",
    render: renderCash,
  },
]

const getColorHex = (colorName: string): string => {
  const colorMap: { [key: string]: string } = {
    pink: "#FFC0CB",
    red: "#FF0000",
    blue: "#0000FF",
    skyblue: "#87CEEB",
    green: "#00FF00",
    yellow: "#FFFF00",
    purple: "#800080",
    orange: "#FFA500",
    gold: "#FFD700",
    // add more as needed
  }
  if (colorName === "-1") {
    return "#000000"
  }

  return colorMap[colorName.toLowerCase()] || colorName
}

function GameDetailsTable(props: { matchDetails: MatchDetails }) {
  const [sortBy, setSortBy] = React.useState<null | keyof StyledTableRow>(
    "moneyCollected",
  )

  const summaries = props.matchDetails.playerSummary
  const statsData = props.matchDetails.statsData
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
  const data: StyledTableRow[] = []
  for (let s of summaries) {
    const row = {
      player: s.name,
      team: s.team,
      color: s.color,
      won: s.win,
      general: s.side,
      moneySpent: s.moneySpent,
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
    }
    data.push(row)
  }

  const sortedData = sortBy ? _.sortBy(data, sortBy) : data

  return (
    <TableContainer component={Paper}>
      <Table stickyHeader>
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

function DetailedGraphs(props: { details: MatchDetails }) {
  const details = props.details
  return (
    <Paper>
      <ApmChart apms={details.apms} playerSummaries={details.playerSummary} />
      <Divider />
      <CostBreakdown costs={details.costs} />
      <Divider />
      <MoneyChart
        title="Money"
        money={details.moneyValues}
        playerSummaries={details.playerSummary}
      />
      <MoneyChart
        title="$ Earned"
        money={details.statsData["money_earned"]}
        playerSummaries={details.playerSummary}
      />
      <MoneyChart
        title="XP"
        money={details.statsData["xp"]}
        playerSummaries={details.playerSummary}
        horizontalLines={[800, 1500, 2500, 5000]}
      />
      <MoneyChart
        title="Units Killed"
        money={details.statsData["units_killed"]}
        playerSummaries={details.playerSummary}
      />
      <MoneyChart
        title="Units Built"
        money={details.statsData["units_built"]}
        playerSummaries={details.playerSummary}
      />
      <MoneyChart
        title="Units Lost"
        money={details.statsData["units_lost"]}
        playerSummaries={details.playerSummary}
      />
      <MoneyChart
        title="Buildings Killed"
        money={details.statsData["buildings_killed"]}
        playerSummaries={details.playerSummary}
      />
      <MoneyChart
        title="Buildings Built"
        money={details.statsData["buildings_built"]}
        playerSummaries={details.playerSummary}
      />
      <MoneyChart
        title="Buildings Lost"
        money={details.statsData["buildings_lost"]}
        playerSummaries={details.playerSummary}
      />
    </Paper>
  )
}

type Displays =
  | "Player Unit and spending breakdown"
  | "Event Chart"
  | "Detailed Graphs"

export default function ShowMatchDetails(props: { id: number }) {
  const [details, setDetails] = React.useState<MatchDetails>(empty)
  const [selectedDisplay, setSelectedDisplay] = React.useState<Displays | null>(
    null,
  )
  React.useEffect(() => {
    getDetails(props.id, setDetails)
  }, [props.id])
  if (details.matchId === 0) {
    return <Loading />
  }
  const maxAtMinute =
    details.spent !== undefined
      ? _.max(details.spent.total.map((t) => t.atMinute))
      : 1
  const maxMinute = Math.ceil(maxAtMinute ?? 1)
  const choices: Displays[] = [
    "Player Unit and spending breakdown",
    "Event Chart",
    "Detailed Graphs",
  ]
  const handleClick = (
    event: React.MouseEvent<HTMLElement>,
    newSelection: Displays | null,
  ) => {
    setSelectedDisplay(newSelection ?? null)
  }
  const buttonGroup = (
    <>
      <Typography>Select which detailed charts to show</Typography>
      <ToggleButtonGroup
        exclusive
        value={selectedDisplay}
        onChange={handleClick}
        color="primary"
      >
        {choices.map((v, i) => {
          return (
            <ToggleButton size="large" value={v}>
              {v}
            </ToggleButton>
          )
        })}
      </ToggleButtonGroup>
    </>
  )

  return (
    <Paper>
      <Divider />
      <DisplayFirstBlood
        first_blood={details.firstBlood ?? undefined}
        building_first_blood={details.buildingFirstBlood ?? undefined}
      />
      <GameDetailsTable matchDetails={details} />
      {buttonGroup}
      <Divider />
      <Typography>{selectedDisplay}</Typography>
      {selectedDisplay === "Player Unit and spending breakdown" && (
        <ShowPlayerSummaries playerSummaries={details.playerSummary} />
      )}
      {selectedDisplay === "Event Chart" && (
        <EventChart
          upgrades={details.upgradeEvents}
          max={maxMinute}
          playerSummaries={details.playerSummary}
        />
      )}
      {selectedDisplay === "Detailed Graphs" && (
        <DetailedGraphs details={details} />
      )}
    </Paper>
  )
}
