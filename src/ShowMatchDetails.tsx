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
  ReferenceLine,
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
import ShowPlayerSummaries from "./Summary"
import { Client } from "./Client"
import { MatchDetails, Spent, Upgrades, APM, PlayerSummary, FirstBlood } from "./api"
import { Alert, Stack } from "@mui/material"

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
            <XAxis type="number" dataKey="atMinute" domain={[0, max_time]}
              tickFormatter={(atMinute) => atMinute.toFixed(1) + "m"}
              name="minutes"
            />
            <YAxis
              label={{
                value: props.title,
                position: "insideLeft",
                fontSize: 25,
                strokeFill: "black",
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
          <XAxis type="number" dataKey="atMinute" domain={[0, props.max]}
            tickFormatter={(atMinute) => atMinute.toFixed(1) + "m"}
          />
          <YAxis
            type="number"
            dataKey="cost"
            label={{
              value: "Cost",
              position: "insideLeft",
              fontSize: 25,
              strokeFill: "black",
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

function ApmChart(props: { apms: APM[] }) {
  if (props.apms.length === 0) {
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
            stroke: 5
          }}
        />
        <Tooltip cursor={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function DisplayFirstBlood(props: { first_blood?: FirstBlood, building_first_blood?: FirstBlood }) {
  if (props.first_blood === undefined) {
    return <></>
  }
  const msgs = [`${props.first_blood.attacker} drew first blood on ${props.first_blood.victim} at ${props.first_blood.atMinute.toFixed(2)}minutes`]
  if (props.building_first_blood) {
    msgs.push(`${props.building_first_blood.attacker} drew first building blood on ${props.building_first_blood.victim} at ${props.building_first_blood.atMinute.toFixed(2)}minutes`)
  }
  return (
    <Stack direction="row" spacing={0} sx={{
      justifyContent: "space-between",
      alignItems: "center",
    }}>
      {msgs.map(m =>
        (<Alert severity="warning" sx={{ width: "100%" }}>{m}</Alert>)
      )}
    </Stack>
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
      <Divider />
      <DisplayFirstBlood first_blood={details.firstBlood ?? undefined} building_first_blood={details.buildingFirstBlood ?? undefined} />
      <ShowPlayerSummaries playerSummaries={details.playerSummary} />
      <Divider />
      <EventChart upgrades={details.upgradeEvents} max={maxMinute} playerSummaries={details.playerSummary} />
      <ApmChart apms={details.apms} />
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
    </>
  )
}
