import { blue, lightGreen, purple, red } from "@mui/material/colors"
import Container from "@mui/material/Container"
import _ from "lodash"
import * as React from "react"
import {
  Bar,
  BarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Costs, CostsBuiltObject } from "./api"

const COLORS = [
  red["200"],
  purple["200"],
  lightGreen["200"],
  blue["200"],
  red["400"],
  purple["400"],
  lightGreen["400"],
  blue["400"],
  red["600"],
  purple["600"],
  lightGreen["600"],
  blue["600"],
  red["800"],
  purple["800"],
  lightGreen["800"],
  blue["800"],
]

function formatCosts(data: CostsBuiltObject[], name: string) {
  const sorted = _.sortBy(data, (d) => -d.totalSpent)
  function reducer(acc: Record<string, unknown>, d: CostsBuiltObject) {
    return { ...acc, [d.name]: d.totalSpent }
  }
  const bc = sorted.reduce(reducer, { name: name })
  return bc
}

function extractNames(data: object[]): string[] {
  return _.without(
    _.uniq(
      data.reduce<string[]>((names, n) => [...names, ...Object.keys(n)], []),
    ),
    "name",
  )
}

function CostChart(props: {
  data: object[]
  names: string[]
  label: string
  colors: string[]
}) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart
        data={props.data}
        layout="horizontal"
        margin={{ top: 5, right: 10, left: 15, bottom: 5 }}
      >
        {props.names.map((n, i) => (
          <Bar
            key={n}
            dataKey={n}
            fill={props.colors[i % props.colors.length]}
            stackId="a"
          />
        ))}
        <XAxis dataKey="name" />
        <YAxis
          label={{
            value: props.label,
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

export default function CostBreakdown(props: { costs: Costs[] }) {
  const building_data = React.useMemo(
    () =>
      props.costs.map((x) =>
        formatCosts(x.buildings, x?.player?.name ?? "unk"),
      ),
    [props.costs],
  )
  const building_names = React.useMemo(
    () => extractNames(building_data),
    [building_data],
  )

  const unit_data = React.useMemo(
    () =>
      props.costs.map((x) => formatCosts(x.units, x?.player?.name ?? "unk")),
    [props.costs],
  )
  const unit_names = React.useMemo(
    () => extractNames(unit_data),
    [unit_data],
  )

  const upgrade_data = React.useMemo(
    () =>
      props.costs.map((x) =>
        formatCosts(x.upgrades, x?.player?.name ?? "unk"),
      ),
    [props.costs],
  )
  const upgrade_names = React.useMemo(
    () => extractNames(upgrade_data),
    [upgrade_data],
  )

  if (props.costs.length === 0) {
    return <></>
  }

  return (
    <Container>
      <CostChart
        data={building_data}
        names={building_names}
        label="Building Spending"
        colors={COLORS}
      />
      <CostChart
        data={unit_data}
        names={unit_names}
        label="Unit Spending"
        colors={COLORS}
      />
      <CostChart
        data={upgrade_data}
        names={upgrade_names}
        label="Upgrade Spending"
        colors={COLORS}
      />
    </Container>
  )
}
