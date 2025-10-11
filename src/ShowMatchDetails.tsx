import Divider from "@mui/material/Divider"
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
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts"
import { PlayerColor } from "./Colors"
import CostBreakdown from "./CostBreakdown"
import { APM, MatchDetails, Spent, Upgrades } from "./proto/match"

function getDetails(id: number, callback: (m: MatchDetails) => void) {
  fetch("/api/details/" + id).then((r) =>
    r
      .blob()
      .then((b) => b.arrayBuffer())
      .then((j) => {
        const a = new Uint8Array(j)
        const costs = MatchDetails.decode(a)
        callback(costs)
      })
  )
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
}

const shapes: (
  | "circle"
  | "cross"
  | "diamond"
  | "square"
  | "star"
  | "triangle"
)[] = ["circle", "star", "square", "triangle"]

interface SpendChartData {
  atMinute: number
  Bill: number
  Brendan: number
  Sean: number
  Jared: number
}

type playername = "Bill" | "Brendan" | "Sean" | "Jared"

function spendDataReducer(acc: SpendChartData[], cur: Spent): SpendChartData[] {
  const next = { ...acc[acc.length - 1] }
  next[cur.playerName as playername] = cur.accCost
  next.atMinute = cur.atMinute
  return [...acc, next]
}

function SpendingChart(props: {
  spent: Spent[] | undefined
  title: string
  max: number
}) {
  if (props.spent) {
    const init = { Bill: 0, Brendan: 0, Sean: 0, Jared: 0, atMinute: 0 }
    const data = props.spent.reduce(spendDataReducer, [init])
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart
          height={300}
          data={data}
          margin={{ top: 5, right: 10, left: 15, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" dataKey="atMinute" domain={[0, props.max]} />
          <YAxis
            label={{
              value: "$",
              position: "insideLeft",
              offset: -5,
              angle: -90,
            }}
          />
          <Tooltip />
          <Legend />
          {["Bill", "Brendan", "Sean", "Jared"].map((n) => (
            <Line
              dataKey={n}
              strokeWidth={2}
              stroke={PlayerColor(n)}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  } else {
    return <div>WTF {JSON.stringify(props.spent)}</div>
  }
}

function EventChart(props: {
  upgrades: { [name: string]: Upgrades }
  max: number
}) {
  const names = Object.keys(props.upgrades).sort((x1, x2) =>
    x1.localeCompare(x2)
  )
  if (props.upgrades) {
    return (
      <ResponsiveContainer width="100%" height={300}>
        <ScatterChart margin={{ top: 5, right: 10, left: 15, bottom: 5 }}>
          {names.map((name, idx) => (
            <Scatter
              name={name}
              fill={PlayerColor(name)}
              data={props.upgrades[name].upgrades}
              shape={shapes[idx]}
              legendType={shapes[idx]}
            >
              {/* <LabelList dataKey="upgradeName" position="left" formatter={labelformater} offset={100} /> */}
            </Scatter>
          ))}
          <XAxis type="number" dataKey="atMinute" domain={[0, props.max]} />
          <YAxis
            type="number"
            dataKey="cost"
            label={{
              value: "Cost",
              position: "insideLeft",
              offset: -5,
              angle: -90,
            }}
          />
          <ZAxis dataKey="upgradeName" name="upgrade" />
          <Tooltip cursor={{ strokeDasharray: "3 3" }} />
          <CartesianGrid />
          <Legend />
        </ScatterChart>
      </ResponsiveContainer>
    )
  } else {
    return <div>{JSON.stringify(props.upgrades)}</div>
  }
}

function ApmChart(props: { apms: APM[] }) {
  const data = _.sortBy(props.apms, (a) => -a.apm)
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart
        data={data}
        layout="horizontal"
        margin={{ top: 5, right: 10, left: 15, bottom: 5 }}
      >
        <Bar dataKey="apm" fill="#42A5F5" />
        <XAxis dataKey="playerName" />
        <YAxis
          label={{
            value: "Actions Per Minute",
            position: "insideLeft",
            offset: -5,
            angle: -90,
          }}
        />
        <Tooltip cursor={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

export default function ShowMatchDetails(props: { id: number }) {
  const [details, setDetails] = React.useState<MatchDetails>(empty)
  React.useEffect(() => {
    getDetails(props.id, setDetails)
  }, [props.id])
  const maxAtMinute =
    details.spent !== undefined
      ? _.max(details.spent.total.map((t) => t.atMinute))
      : 1
  const maxMinute = Math.ceil(maxAtMinute ?? 1)
  return (
    <>
      <Typography>Spending Total</Typography>
      <SpendingChart
        spent={details.spent?.total}
        title="total"
        max={maxMinute}
      />
      <Typography>Spending Buildings</Typography>
      <SpendingChart
        spent={details.spent?.buildings}
        title="buildings"
        max={maxMinute}
      />
      <Typography>Spending Units</Typography>
      <SpendingChart
        spent={details.spent?.units}
        title="units"
        max={maxMinute}
      />
      <Typography>Spending Upgrades</Typography>
      <SpendingChart
        spent={details.spent?.upgrades}
        title="upgrades"
        max={maxMinute}
      />
      <EventChart upgrades={details.upgradeEvents} max={maxMinute} />
      <ApmChart apms={details.apms} />
      <Divider />
      <CostBreakdown costs={details.costs} />
    </>
  )
}
