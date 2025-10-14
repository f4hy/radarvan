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
import { PlayerColor, ColorByIdx } from "./Colors"
import CostBreakdown from "./CostBreakdown"
import { Client } from "./Client"
import { MatchDetails, Spent, Upgrades, APM } from "./api"

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
    return <div>{props.title + " data unavailible for this replay"}</div>
  }
}

function MoneyChart(props: {
  money: { [key: string]: { [key: string]: number } }
  title: string
}) {
  if (props.money && Object.keys(props.money).length > 0) {
    const players = Object.keys(Object.values(props.money)[0])
    const data = Object.entries(props.money).map(([timecode, values]) => ({
      ...values,
      timecode: timecode,
    }))
    const max = Object.values(props.money).reduce((acc, cur) => { return Math.max(acc, ...Object.values(cur)) }, 0)
    const max_time = Math.max(...Object.keys(props.money).map(k => Number(k)))
    return (
      <ResponsiveContainer width="100%" height={300}>
        <LineChart
					title="Money $$"
          height={300}
          data={data}
          margin={{ top: 5, right: 10, left: 15, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis  type="number" dataKey="timecode" domain={[0, max_time]} />
          <YAxis
            label={{
              value: "Money",
              position: "insideLeft",
              offset: -5,
              angle: -90,
            }}
            domain={[0, max]}
          />
          <Tooltip />
          <Legend />
          {players.map((n, i) => (
            <Line
              dataKey={n}
              strokeWidth={2}
              stroke={ColorByIdx(i)}
              dot={false}
            />
          ))}
        </LineChart>
      </ResponsiveContainer>
    )
  } else {
    return <div>Money data unavailible for this replay</div>
  }
}

function EventChart(props: {
  upgrades: { [name: string]: Upgrades }
  max: number
}) {
  const names = Object.keys(props.upgrades).sort((x1, x2) =>
    x1.localeCompare(x2),
  )
  if (props.upgrades && names.length > 0) {
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
    return <div></div>
  }
}

function ApmChart(props: { apms: APM[] }) {
  if (props.apms.length == 0) {
    return <div>APM data not yet availible</div>
  }
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

function Spending(props: {
  title: string
  spend_data: Spent[] | undefined
  max: number
}) {
  if ((props.spend_data ?? []).length === 0) {
    return <div>{props.title} data not yet available</div>
  }
  return (
    <>
      <Typography>props.title</Typography>
      <SpendingChart spent={props.spend_data} title="total" max={props.max} />
    </>
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
      <MoneyChart title="Money" money={details.moneyValues} />
      <Divider />
      <Spending
        title="Spending Total"
        spend_data={details.spent.total}
        max={maxMinute}
      />
      <Spending
        title="Spending Units"
        spend_data={details.spent.units}
        max={maxMinute}
      />
      <Spending
        title="Spending Buildings"
        spend_data={details.spent.buildings}
        max={maxMinute}
      />
      <Spending
        title="Spending Upgrades"
        spend_data={details.spent.upgrades}
        max={maxMinute}
      />
      <EventChart upgrades={details.upgradeEvents} max={maxMinute} />
      <ApmChart apms={details.apms} />
      <Divider />
      <CostBreakdown costs={details.costs} />
    </>
  )
}
