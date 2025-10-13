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
import { MatchDetails, Spent, Upgrades, APM , CostsOutput, CostsBuiltObject } from "./api"

function formatCosts(data: CostsBuiltObject[], name: string) {
  const sorted = _.sortBy(data, (d) => -d.totalSpent)
  function reducer(acc: any, d: CostsBuiltObject) {
    return { ...acc, [d.name]: d.totalSpent }
  }
  const bc = sorted.reduce(reducer, { name: name })
  return bc
}

export default function CostBreakdown(props: { costs: CostsOutput[] }) {
  const building_data = props.costs.map((x) =>
    formatCosts(x.buildings, x?.player?.name ?? "unk")
  )
  const building_names: string[] = _.without(
    _.uniq(
      building_data.reduce((names, n) => [...names, ...Object.keys(n)], [])
    ),
    "name"
  )
  const unit_data = props.costs.map((x) =>
    formatCosts(x.units, x?.player?.name ?? "unk")
  )
  const unit_names: string[] = _.without(
    _.uniq(unit_data.reduce((names, n) => [...names, ...Object.keys(n)], [])),
    "name"
  )

  const upgrade_data = props.costs.map((x) =>
    formatCosts(x.upgrades, x?.player?.name ?? "unk")
  )
  const upgrade_names: string[] = _.without(
    _.uniq(
      upgrade_data.reduce((names, n) => [...names, ...Object.keys(n)], [])
    ),
    "name"
  )

  const colors = [
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
  return (
    <Container>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={building_data}
          layout="horizontal"
          margin={{ top: 5, right: 10, left: 15, bottom: 5 }}
        >
          {building_names.map((n, i) => (
            <Bar dataKey={n} fill={colors[i % colors.length]} stackId="a" />
          ))}
          <XAxis dataKey="name" />
          <YAxis
            label={{
              value: "Building Spending",
              position: "insideLeft",
              offset: -5,
              angle: -90,
            }}
          />
          <Tooltip cursor={false} />
        </BarChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={unit_data}
          layout="horizontal"
          margin={{
            top: 5,
            right: 10,
            left: 15,
            bottom: 5,
          }}
        >
          {unit_names.map((n, i) => (
            <Bar dataKey={n} fill={colors[i % colors.length]} stackId="a" />
          ))}
          <XAxis dataKey="name" />
          <YAxis
            label={{
              value: "Unit Spending",
              position: "insideLeft",
              offset: -5,
              angle: -90,
            }}
          />
          <Tooltip cursor={false} />
        </BarChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={300}>
        <BarChart
          data={upgrade_data}
          layout="horizontal"
          margin={{
            top: 5,
            right: 10,
            left: 15,
            bottom: 5,
          }}
        >
          {upgrade_names.map((n, i) => (
            <Bar dataKey={n} fill={colors[i % colors.length]} stackId="a" />
          ))}
          <XAxis dataKey="name" />
          <YAxis
            label={{
              value: "Upgrade Spending",
              position: "insideLeft",
              offset: -5,
              angle: -90,
            }}
          />
          <Tooltip cursor={false} />
        </BarChart>
      </ResponsiveContainer>
    </Container>
  )
}
