import Box from "@mui/material/Box"
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
  Sankey,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { KillEventOutput, ObjectSummary, PlayerSummary } from "./api"

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
      </Stack>
    </>
  )
}

type SankeyCategory = { label: string; items: Record<string, ObjectSummary> }
type SankeyData = {
  nodes: { name: string }[]
  links: { source: number; target: number; value: number }[]
}

function buildCategorySankeyData(
  playerName: string,
  categories: SankeyCategory[],
): SankeyData {
  const nodeNames: string[] = []
  const nodeIdx = new Map<string, number>()
  const links: { source: number; target: number; value: number }[] = []

  function addNode(name: string): number {
    if (!nodeIdx.has(name)) {
      nodeIdx.set(name, nodeNames.length)
      nodeNames.push(name)
    }
    return nodeIdx.get(name)!
  }

  const playerIdx = addNode(playerName)
  for (const { label, items } of categories) {
    const catTotal = Object.values(items).reduce((s, x) => s + x.totalSpent, 0)
    if (catTotal === 0) continue
    const catIdx = addNode(label)
    links.push({ source: playerIdx, target: catIdx, value: catTotal })
    for (const [name, obj] of Object.entries(items)) {
      if (obj.totalSpent <= 0) continue
      links.push({
        source: catIdx,
        target: addNode(name),
        value: obj.totalSpent,
      })
    }
  }

  return { nodes: nodeNames.map((name) => ({ name })), links }
}

const CATEGORY_COLORS: Record<string, string> = {
  Units: "#4e79a7",
  Buildings: "#e15759",
  Upgrades: "#f28e2b",
  "Units Destroyed": "#9467bd",
  "Buildings Destroyed": "#bcbd22",
  "Units Lost": "#d62728",
  "Buildings Lost": "#8c564b",
  "Destroyed From": "#59a14f",
  "Lost To": "#e15759",
}

type SankeyLinkProps = {
  sourceX?: number
  sourceY?: number
  targetX?: number
  targetY?: number
  sourceControlX?: number
  targetControlX?: number
  linkWidth?: number
  payload?: { source?: { name?: string }; target?: { name?: string } }
}

function SankeyLink({
  sourceX = 0,
  sourceY = 0,
  targetX = 0,
  targetY = 0,
  sourceControlX = 0,
  targetControlX = 0,
  linkWidth = 0,
  payload,
}: SankeyLinkProps) {
  const color =
    CATEGORY_COLORS[payload?.target?.name ?? ""] ??
    CATEGORY_COLORS[payload?.source?.name ?? ""] ??
    "#aaa"
  const d = [
    `M${sourceX},${sourceY - linkWidth / 2}`,
    `C${sourceControlX},${sourceY - linkWidth / 2}`,
    ` ${targetControlX},${targetY - linkWidth / 2}`,
    ` ${targetX},${targetY - linkWidth / 2}`,
    `L${targetX},${targetY + linkWidth / 2}`,
    `C${targetControlX},${targetY + linkWidth / 2}`,
    ` ${sourceControlX},${sourceY + linkWidth / 2}`,
    ` ${sourceX},${sourceY + linkWidth / 2}Z`,
  ].join(" ")
  return (
    <path
      d={d}
      fill={color}
      fillOpacity={0.3}
      stroke={color}
      strokeOpacity={0.5}
    />
  )
}

const NODE_COLORS = [
  "#4e79a7",
  "#f28e2b",
  "#e15759",
  "#76b7b2",
  "#59a14f",
  "#edc948",
  "#b07aa1",
  "#ff9da7",
  "#9c755f",
  "#bab0ac",
]

type SankeyNodeProps = {
  x?: number
  y?: number
  width?: number
  height?: number
  index?: number
  payload?: { name: string; value?: number; sourceLinks?: unknown[] }
}

function SankeyNode({
  x = 0,
  y = 0,
  width = 0,
  height = 0,
  index = 0,
  payload,
}: SankeyNodeProps) {
  if (!payload) return null
  const color = NODE_COLORS[index % NODE_COLORS.length]
  const isLeaf = (payload.sourceLinks?.length ?? 0) === 0
  const textX = isLeaf ? x - 6 : x + width + 6
  const anchor = isLeaf ? "end" : "start"
  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={4}
        ry={4}
        fill={color}
        fillOpacity={0.85}
      />
      <text
        x={textX}
        y={y + height / 2}
        textAnchor={anchor}
        dominantBaseline="middle"
        fontSize={11}
        fill="currentColor"
      >
        ${(payload.value ?? 0).toLocaleString("en-US")}{" "}
        {payload.name.split("_").at(-1)}
      </text>
    </g>
  )
}

const cashFormatter = (value: unknown) =>
  `$${((value as number) ?? 0).toLocaleString("en-US")}`

function PlayerSankeyChart(props: {
  data: SankeyData
  emptyMessage: string
  formatter?: (value: unknown) => string
  minHeight?: number
}) {
  const { nodes, links } = props.data
  if (links.length === 0) return <div>{props.emptyMessage}</div>
  const height = Math.max(props.minHeight ?? 400, nodes.length * 18)
  return (
    <ResponsiveContainer width="100%" height={height}>
      <Sankey
        data={{ nodes, links }}
        nodePadding={10}
        margin={{ left: 100, right: 200 }}
        nodeWidth={15}
        iterations={32}
        node={<SankeyNode />}
        link={<SankeyLink />}
        linkCurvature={0.7}
      >
        <Tooltip formatter={props.formatter} />
      </Sankey>
    </ResponsiveContainer>
  )
}

function PlayerSpendingSankey(props: { playerSummary: PlayerSummary }) {
  const data = React.useMemo(
    () =>
      buildCategorySankeyData(props.playerSummary.name, [
        { label: "Units", items: props.playerSummary.unitsCreated },
        { label: "Buildings", items: props.playerSummary.buildingsBuilt },
        { label: "Upgrades", items: props.playerSummary.upgradesBuilt },
      ]),
    [props.playerSummary],
  )
  return (
    <PlayerSankeyChart
      data={data}
      emptyMessage="Spending data unavailable for this replay"
      formatter={cashFormatter}
    />
  )
}

function PlayerDestroyedSankey(props: { playerSummary: PlayerSummary }) {
  const data = React.useMemo(
    () =>
      buildCategorySankeyData(props.playerSummary.name, [
        {
          label: "Units Destroyed",
          items: props.playerSummary.unitsDestroyed ?? {},
        },
        {
          label: "Buildings Destroyed",
          items: props.playerSummary.buildingsDestroyed ?? {},
        },
      ]),
    [props.playerSummary],
  )
  return (
    <PlayerSankeyChart
      data={data}
      emptyMessage="Value destroyed data unavailable for this replay"
      formatter={cashFormatter}
    />
  )
}

function PlayerLossesSankey(props: { playerSummary: PlayerSummary }) {
  const data = React.useMemo(
    () =>
      buildCategorySankeyData(props.playerSummary.name, [
        { label: "Units Lost", items: props.playerSummary.unitsLost ?? {} },
        {
          label: "Buildings Lost",
          items: props.playerSummary.buildingsLost ?? {},
        },
      ]),
    [props.playerSummary],
  )
  return (
    <PlayerSankeyChart
      data={data}
      emptyMessage="Losses data unavailable for this replay"
      formatter={cashFormatter}
    />
  )
}

// killEvents carry killerPlayer/victimPlayer for every kill in the match, but
// nothing upstream groups them by *opponent* - match_details.py only buckets
// by unit type. Build that grouping here so FFA/team games can show who a
// player actually traded value with, reusing the existing Sankey plumbing.
function opponentValueMap(
  playerName: string,
  killEvents: KillEventOutput[],
  direction: "destroyed" | "lost",
): Record<string, ObjectSummary> {
  const result: Record<string, ObjectSummary> = {}
  for (const k of killEvents) {
    const self = direction === "destroyed" ? k.killerPlayer : k.victimPlayer
    const opponent = direction === "destroyed" ? k.victimPlayer : k.killerPlayer
    if (self !== playerName || opponent === "unk" || opponent === playerName) {
      continue
    }
    const entry = result[opponent] ?? { count: 0, totalSpent: 0 }
    entry.count += 1
    entry.totalSpent += k.value ?? 0
    result[opponent] = entry
  }
  return result
}

function PlayerOpponentSankey(props: {
  playerName: string
  killEvents: KillEventOutput[]
}) {
  const data = React.useMemo(
    () =>
      buildCategorySankeyData(props.playerName, [
        {
          label: "Destroyed From",
          items: opponentValueMap(
            props.playerName,
            props.killEvents,
            "destroyed",
          ),
        },
        {
          label: "Lost To",
          items: opponentValueMap(props.playerName, props.killEvents, "lost"),
        },
      ]),
    [props.playerName, props.killEvents],
  )
  return (
    <PlayerSankeyChart
      data={data}
      emptyMessage="No kill events recorded against a specific opponent"
      formatter={cashFormatter}
    />
  )
}

function PlayerPowersSankey(props: { playerSummary: PlayerSummary }) {
  const data = React.useMemo(() => {
    const nodeNames: string[] = []
    const nodeIdx = new Map<string, number>()
    const links: { source: number; target: number; value: number }[] = []
    function addNode(name: string): number {
      if (!nodeIdx.has(name)) {
        nodeIdx.set(name, nodeNames.length)
        nodeNames.push(name)
      }
      return nodeIdx.get(name)!
    }
    const playerIdx = addNode(props.playerSummary.name)
    for (const [power, count] of Object.entries(
      props.playerSummary.powersUsed,
    )) {
      if (count <= 0) continue
      links.push({ source: playerIdx, target: addNode(power), value: count })
    }
    return { nodes: nodeNames.map((name) => ({ name })), links }
  }, [props.playerSummary])
  return (
    <PlayerSankeyChart
      data={data}
      emptyMessage="No powers used data"
      minHeight={300}
    />
  )
}

function ShowPlayerSummary(props: {
  playerSummary: PlayerSummary
  killEvents: KillEventOutput[]
}) {
  const sum = props.playerSummary
  if (sum?.name === undefined) {
    return <Typography>No player summaries</Typography>
  }
  return (
    <Stack>
      <Stack spacing={2}>
        <Box>
          <Typography variant="h6">Spending Breakdown</Typography>
          <PlayerSpendingSankey playerSummary={sum} />
        </Box>
        <Box>
          <Typography variant="h6">Value Destroyed</Typography>
          <PlayerDestroyedSankey playerSummary={sum} />
        </Box>
        <Box>
          <Typography variant="h6">Losses</Typography>
          <PlayerLossesSankey playerSummary={sum} />
        </Box>
        <Box>
          <Typography variant="h6">Damage by Opponent</Typography>
          <PlayerOpponentSankey
            playerName={sum.name}
            killEvents={props.killEvents}
          />
        </Box>
        <Box>
          <Typography variant="h6">Powers Used</Typography>
          <PlayerPowersSankey playerSummary={sum} />
        </Box>
      </Stack>
      <Typography>
        {sum?.name} | {sum?.side} | Team={sum?.team} | Color={sum.color}
      </Typography>
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
    </Stack>
  )
}

export default function ShowPlayerSummaries(props: {
  playerSummaries: PlayerSummary[]
  killEvents: KillEventOutput[]
}) {
  const [selectedPlayer, setSelectedPlayer] = React.useState<number>(0)
  const handleClick = React.useCallback(
    (
      _event: React.MouseEvent<HTMLElement>,
      newSelection: number | undefined,
    ) => {
      setSelectedPlayer((prev) => newSelection ?? prev)
    },
    [],
  )
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
        killEvents={props.killEvents}
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
