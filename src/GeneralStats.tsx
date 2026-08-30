import { Typography, useTheme } from "@mui/material"
import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Divider from "@mui/material/Divider"
import Grid from "@mui/material/Grid"
import Stack from "@mui/material/Stack"
import { alpha } from "@mui/material/styles"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import MuiTooltip from "@mui/material/Tooltip"
import useMediaQuery from "@mui/material/useMediaQuery"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  LabelList,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import type { FactionMatrix, GeneralStat, GeneralStats } from "./api"
import { Client } from "./Client"
import DisplayGeneral, { GeneralAvatar } from "./Generals"
import { toGeneralName } from "./general_utils"
import Loading from "./Loading"
import FormatToggle, { ALL_FORMATS } from "./FormatToggle"
import Page from "./Page"
import QueryState from "./QueryState"
import { CHART_LOSS, CHART_WIN, LOSS_COLOR, WIN_COLOR } from "./theme"
import { formatCash, wilsonLowerBound, winRate } from "./utils"
import WinRateChip from "./WinRateChip"
import WinRateRadar from "./WinRateRadar"

const FORMAT_OPTIONS = ALL_FORMATS
type GameFormat = (typeof FORMAT_OPTIONS)[number]

function fetchGeneralStats(gameFormat: GameFormat): Promise<GeneralStats> {
  const params = gameFormat === "All" ? {} : { gameFormat }
  return Client.getGeneralsStatsApiGeneralstatsGet(params)
}

type GeneralChartData = {
  name: string
  wins: number
  losses: number
  rate: number
}

function GeneralWinLossChart(props: {
  data: GeneralChartData[]
  isMobile: boolean
}) {
  return (
    <ResponsiveContainer width="99%" height={props.isMobile ? 350 : 600}>
      <BarChart
        data={props.data}
        layout="horizontal"
        margin={{
          top: 20,
          right: 10,
          left: 5,
          bottom: props.isMobile ? 80 : 60,
        }}
      >
        <CartesianGrid strokeDasharray="5 5" vertical={false} />
        <Bar dataKey="wins" fill={CHART_WIN} name="Wins">
          {!props.isMobile && (
            <LabelList dataKey="wins" position="top" fontSize={11} />
          )}
          <LabelList
            dataKey="rate"
            position="insideTop"
            fontSize={props.isMobile ? 9 : 11}
            fill="white"
            formatter={(v) => `${(Number(v) * 100).toFixed(0)}%`}
          />
        </Bar>
        <Bar dataKey="losses" fill={CHART_LOSS} name="Losses">
          {!props.isMobile && (
            <LabelList dataKey="losses" position="top" fontSize={11} />
          )}
        </Bar>
        <XAxis
          dataKey="name"
          angle={-35}
          textAnchor="end"
          interval={0}
          height="auto"
          tick={{ fontSize: props.isMobile ? 9 : 12 }}
        />
        <YAxis tick={{ fontSize: props.isMobile ? 9 : 12 }} />
        <Tooltip cursor={false} />
      </BarChart>
    </ResponsiveContainer>
  )
}

function DisplayOverallGeneralStat(props: { stats: GeneralStats }) {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"))

  const data = React.useMemo(
    () =>
      props.stats.generalStats.map((x) => {
        const wins = x?.total?.wins ?? 0
        const losses = x?.total?.losses ?? 0
        return {
          wins,
          losses,
          name: toGeneralName(x.general),
          rate: winRate(wins, losses),
        }
      }),
    [props.stats.generalStats],
  )

  return <GeneralWinLossChart data={data} isMobile={isMobile} />
}

function DisplayGeneralStat(props: { stat: GeneralStat }) {
  const overall = props.stat.total
  const overallWins = overall?.wins ?? 0
  const overallLosses = overall?.losses ?? 0
  const valueDestroyed = props.stat.valueDestroyed ?? 0
  const valueLost = props.stat.valueLost ?? 0
  const tradeRatio = valueLost > 0 ? valueDestroyed / valueLost : undefined

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          mb: 0.5,
        }}
      >
        <DisplayGeneral general={props.stat.general} />
        <Typography
          variant="subtitle1"
          sx={{
            fontWeight: "bold",
          }}
        >
          {toGeneralName(props.stat.general)}
        </Typography>
        <WinRateChip wins={overallWins} losses={overallLosses} />
      </Stack>
      {(valueDestroyed > 0 || valueLost > 0) && (
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          {formatCash(valueDestroyed)} destroyed · {formatCash(valueLost)} lost
          {tradeRatio !== undefined && ` · ${tradeRatio.toFixed(2)}x trade`}
        </Typography>
      )}
    </Box>
  )
}

// Row general (general_a) vs column general (general_b): the model's
// predicted advantage for the row general in that draw, with both players
// and the map forced to the model's UNK slot - a pure faction-vs-faction
// signal, not tied to any specific players. Delta is expressed above/below
// the grid's own median (always ~50% by construction - see the backend's
// antisymmetric-head note) rather than as an absolute win probability, same
// convention as the bracket popup's "best draws" list.

// The grid is 12x12 of four-character numbers, so both edges have to stay put
// while it scrolls: without them a cell in the middle is a number with no idea
// which pair it belongs to.
const STICKY_ROW_LABEL = {
  position: "sticky",
  left: 0,
  zIndex: 2,
  bgcolor: "background.paper",
  borderRight: 1,
  borderColor: "divider",
} as const

function MatrixFact(props: { title: string; children: React.ReactNode }) {
  return (
    <MuiTooltip title={props.title}>
      <Chip
        size="small"
        variant="outlined"
        label={props.children}
        sx={{ cursor: "default" }}
      />
    </MuiTooltip>
  )
}

function FactionMatrixTable(props: { matrix: FactionMatrix }) {
  const { cells, medianProbAWins } = props.matrix

  const generals = React.useMemo(() => {
    const order: number[] = []
    for (const c of cells) {
      if (!order.includes(c.generalA)) order.push(c.generalA)
    }
    return order
  }, [cells])

  const statsByPair = React.useMemo(() => {
    const m = new Map<
      string,
      { prob: number; std: number; significant: boolean }
    >()
    for (const c of cells) {
      m.set(`${c.generalA}:${c.generalB}`, {
        prob: c.probAWins,
        std: c.probAWinsStd ?? 0,
        significant: c.significant ?? false,
      })
    }
    return m
  }, [cells])

  const maxAbsDelta = React.useMemo(
    () =>
      Math.max(...cells.map((c) => Math.abs(c.probAWins - medianProbAWins))),
    [cells, medianProbAWins],
  )

  const ensembleSize = props.matrix.ensembleSize ?? 1
  const nSignificant = cells.filter((c) => c.significant).length

  return (
    <Box>
      <Typography variant="h6" sx={{ mb: 0.5 }}>
        Faction matchup matrix
      </Typography>
      <Typography variant="body2" sx={{ color: "text.secondary", mb: 1.5 }}>
        How much the row general is favored over the column general, with both
        players and the map unknown. A positive number means the row general has
        the edge.
      </Typography>
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", mb: 1.5 }}>
        <MatrixFact title="Every cell is percentage points above or below this, not an absolute win rate. The grid's median draw is ~50% by construction.">
          Median draw {(medianProbAWins * 100).toFixed(0)}%
        </MatrixFact>
        <MatrixFact
          title={`Agreed on across an ${ensembleSize}-model ensemble trained on this much data.`}
        >
          {nSignificant} of {cells.length} matchups hold up
        </MatrixFact>
        <MatrixFact title="The remaining cells aren't distinguishable from a coin flip, so read them as no edge either way.">
          Faded = too close to call
        </MatrixFact>
      </Stack>
      <TableContainer sx={{ overflowX: "auto", maxHeight: 640 }}>
        <Table size="small" stickyHeader>
          <TableHead>
            <TableRow>
              <TableCell sx={{ ...STICKY_ROW_LABEL, zIndex: 3 }} />
              {generals.map((g) => (
                <TableCell key={g} align="center" sx={{ px: 0.5 }}>
                  <Stack spacing={0.25} sx={{ alignItems: "center" }}>
                    <GeneralAvatar general={g} size="1.4rem" />
                    <Box sx={{ fontWeight: 600, fontSize: "0.7rem" }}>
                      {toGeneralName(g)}
                    </Box>
                  </Stack>
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {generals.map((rowGeneral) => (
              <TableRow key={rowGeneral}>
                <TableCell sx={{ ...STICKY_ROW_LABEL, whiteSpace: "nowrap" }}>
                  <Stack
                    direction="row"
                    spacing={0.75}
                    sx={{ alignItems: "center" }}
                  >
                    <GeneralAvatar general={rowGeneral} size="1.4rem" />
                    <Box sx={{ fontWeight: 600 }}>
                      {toGeneralName(rowGeneral)}
                    </Box>
                  </Stack>
                </TableCell>
                {generals.map((colGeneral) => {
                  const stats = statsByPair.get(`${rowGeneral}:${colGeneral}`)
                  const prob = stats?.prob ?? medianProbAWins
                  const std = stats?.std ?? 0
                  const significant = stats?.significant ?? false
                  const delta = prob - medianProbAWins
                  const intensity =
                    maxAbsDelta > 0
                      ? Math.min(Math.abs(delta) / maxAbsDelta, 1)
                      : 0
                  const color = delta >= 0 ? WIN_COLOR : LOSS_COLOR
                  return (
                    <TableCell
                      key={colGeneral}
                      align="center"
                      title={`${toGeneralName(rowGeneral)} vs ${toGeneralName(colGeneral)}: ${(prob * 100).toFixed(1)}% ± ${(std * 100).toFixed(1)}pp across ${ensembleSize} models${significant ? "" : " - not significant"}`}
                      sx={{
                        bgcolor: alpha(
                          color,
                          intensity * (significant ? 0.7 : 0.12),
                        ),
                        color: significant ? "text.primary" : "text.disabled",
                        fontVariantNumeric: "tabular-nums",
                      }}
                    >
                      {delta >= 0 ? "+" : ""}
                      {(delta * 100).toFixed(1)}
                    </TableCell>
                  )
                })}
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

function FactionMatrixSection() {
  // Deliberately not wrapped in QueryState: the model is optional, so a 503
  // means "no prediction available", not "this page failed". No retry either —
  // an unavailable model stays unavailable for the length of a visit.
  const { data: matrix, isPending } = useQuery({
    queryKey: ["factionMatrix"],
    queryFn: () => Client.predictFactionMatrixApiPredictFactionMatrixGet(),
    retry: false,
  })

  if (isPending) return <Loading />
  if (!matrix) return null
  return <FactionMatrixTable matrix={matrix} />
}

function GeneralStatsBody({ generalStats }: { generalStats: GeneralStats }) {
  const sorted = React.useMemo(
    () =>
      [...generalStats.generalStats].sort(
        (a, b) =>
          wilsonLowerBound(b.total?.wins ?? 0, b.total?.losses ?? 0) -
          wilsonLowerBound(a.total?.wins ?? 0, a.total?.losses ?? 0),
      ),
    [generalStats.generalStats],
  )

  const radarData = React.useMemo(
    () =>
      generalStats.generalStats.map((x) => ({
        name: toGeneralName(x.general),
        winRate: Math.round(
          winRate(x?.total?.wins ?? 0, x?.total?.losses ?? 0) * 100,
        ),
      })),
    [generalStats.generalStats],
  )

  return (
    <>
      <DisplayOverallGeneralStat stats={generalStats} />
      <Divider sx={{ mt: 4, mb: 2 }} />
      <Grid
        container
        spacing={2}
        sx={{
          alignItems: "flex-start",
        }}
      >
        <Grid size={{ xs: 12, md: 4 }}>
          <MuiTooltip title="Ranked by the lower bound of the 95% Wilson confidence interval, so a well-sampled win rate outranks a lucky small sample. Chips turn green/red only when the interval is confidently above/below 50%; grey means the sample is inconclusive.">
            <Typography
              variant="h6"
              sx={{ mb: 1, cursor: "default", width: "fit-content" }}
            >
              Ranked by win rate ⓘ
            </Typography>
          </MuiTooltip>
          <Grid container spacing={2}>
            {sorted.map((m) => (
              <Grid key={m.general} size={12}>
                <DisplayGeneralStat stat={m} />
              </Grid>
            ))}
          </Grid>
        </Grid>
        <Grid size={{ xs: 12, md: 8 }}>
          <WinRateRadar data={radarData} aspect={1.4} />
        </Grid>
      </Grid>
      <Divider sx={{ mt: 4, mb: 2 }} />
      <FactionMatrixSection />
    </>
  )
}

export default function DisplayGeneralStats() {
  const [format, setFormat] = React.useState<GameFormat>("All")
  const query = useQuery({
    queryKey: ["generalStats", format],
    queryFn: () => fetchGeneralStats(format),
  })

  return (
    <Page
      title="General Stats"
      description="How each general performs across our games, and which faction matchups genuinely favor one side."
      actions={
        <FormatToggle
          label="Game format"
          options={FORMAT_OPTIONS}
          value={format}
          onChange={setFormat}
        />
      }
    >
      <QueryState query={query} what="general stats">
        {(generalStats) => <GeneralStatsBody generalStats={generalStats} />}
      </QueryState>
    </Page>
  )
}
