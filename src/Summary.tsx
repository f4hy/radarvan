import Divider from "@mui/material/Divider"
import Stack from "@mui/material/Stack"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Typography from "@mui/material/Typography"
import * as React from "react"
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { ObjectSummary, PlayerSummary } from "./api"

function removeUnitPrefix(s: string): string {
  return s
    .replace(/.*_/g, "")
    .replace("America", "")
    .replace("China", "")
    .replace("GLA", "")
}

function BuiltChart(props: {
  built: { [key: string]: ObjectSummary }
  title: string
}) {
  if (Object.keys(props.built).length < 1) {
    return <div>No data</div>
  }
  const data = Object.entries(props.built).map(([unit, values]) => ({
    ...values,
    unit: unit,
  }))
  return (
    <>
      <Typography>{props.title}</Typography>
      <Stack direction="row">
        <ResponsiveContainer width="90%" height={300}>
          <BarChart
            title={props.title}
            height={300}
            layout="vertical"
            data={data}
            margin={{ top: 5, right: 5, left: 200, bottom: 5 }}
          >
            <YAxis
              dataKey="unit"
              type="category"
              tickFormatter={removeUnitPrefix}
            />
            <XAxis
              dataKey="count"
              type="number"
              orientation="top"
              allowDecimals={false}
            />
            <Tooltip />
            <Bar
              dataKey="count"
              fill="#8884d8"
              label={{ fill: "black", fontSize: 20 }}
            />
          </BarChart>
        </ResponsiveContainer>
        <ResponsiveContainer width="80%" height={300}>
          <BarChart
            title={props.title}
            height={300}
            layout="vertical"
            data={data}
            margin={{ top: 5, right: 5, left: 20, bottom: 5 }}
          >
            <YAxis
              dataKey="unit"
              type="category"
              tickFormatter={removeUnitPrefix}
              hide={true}
            />
            <XAxis
              dataKey="totalSpent"
              type="number"
              name="$"
              orientation="top"
            />
            <Tooltip />
            <Bar dataKey="totalSpent" fill="green" />
          </BarChart>
        </ResponsiveContainer>
      </Stack>
    </>
  )
}

function ShowPlayerSummary(props: { playerSummary: PlayerSummary }) {
  const sum = props.playerSummary
  if (sum?.name === undefined) {
    return <Typography>No player summaries</Typography>
  }
  return (
    <Stack>
      <Typography>
        {sum?.name} | {sum?.side} | Team={sum?.team} | Color={sum.color}
      </Typography>
      <Typography>Money Spent: ${props.playerSummary.moneySpent}</Typography>
      <Divider />
      <BuiltChart
        title="Units Created"
        built={props.playerSummary.unitsCreated}
      />
      <Divider />
      <BuiltChart
        title="Buildings Created"
        built={props.playerSummary.buildingsBuilt}
      />
      <Divider />
      <BuiltChart title="Upgrades" built={props.playerSummary.upgradesBuilt} />
      <Divider />
      {Object.entries(props.playerSummary.powersUsed).map(([name, count]) => {
        return <Typography key={name}>{"Powers Used: " + name + " " + count}</Typography>
      })}
    </Stack>
  )
}

export default function ShowPlayerSummaries(props: {
  playerSummaries: PlayerSummary[]
}) {
  const [selectedPlayer, setSelectedPlayer] = React.useState<number>(0)
  const handleClick = (
    event: React.MouseEvent<HTMLElement>,
    newSelection: number | undefined,
  ) => {
    setSelectedPlayer(newSelection ?? selectedPlayer)
  }
  const buttonGroup = (
    <ToggleButtonGroup
      exclusive
      value={selectedPlayer}
      onChange={handleClick}
      color="warning"
    >
      {props.playerSummaries.map((sum, i) => {
        return (
          <ToggleButton key={sum?.name ?? i} size="large" value={i}>
            {sum?.name}
          </ToggleButton>
        )
      })}
    </ToggleButtonGroup>
  )
  const playerSummary =
    selectedPlayer !== undefined ? (
      <ShowPlayerSummary
        playerSummary={props.playerSummaries[selectedPlayer]}
      />
    ) : (
      <></>
    )
  return (
    <>
      <Typography>Select player for details</Typography>
      {buttonGroup}
      {playerSummary}
    </>
  )
}
