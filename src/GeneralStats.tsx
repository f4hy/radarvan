import { Typography, useTheme } from "@mui/material"
import Box from "@mui/material/Box"
import Divider from "@mui/material/Divider"
import Grid from "@mui/material/Grid"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import { alpha } from "@mui/material/styles"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import MuiTooltip from "@mui/material/Tooltip"
import useMediaQuery from "@mui/material/useMediaQuery"
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
import { FactionMatrix, GeneralStat, GeneralStats } from "./api"
import { Client } from "./Client"
import DisplayGeneral from "./Generals"
import { toGeneralName } from "./general_utils"
import Loading from "./Loading"
import { CHART_LOSS, CHART_WIN, LOSS_COLOR, WIN_COLOR } from "./theme"
import { useErrorSnackbar } from "./useErrorSnackbar"
import { wilsonLowerBound, winRate } from "./utils"
import WinRateChip from "./WinRateChip"
import WinRateRadar from "./WinRateRadar"

const FORMAT_OPTIONS = ["All", "1v1", "2v2", "3v3", "4v4"] as const
type GameFormat = (typeof FORMAT_OPTIONS)[number]

const compactCash = new Intl.NumberFormat("en-US", {
  notation: "compact",
  maximumFractionDigits: 1,
})
const formatValue = (n: number) => `$${compactCash.format(n)}`

function getGeneralStats(
  gameFormat: GameFormat,
  callback: (m: GeneralStats) => void,
  onError = console.error,
) {
  const params = gameFormat === "All" ? {} : { gameFormat }
  Client.getGeneralsStatsApiGeneralstatsGet(params)
    .then(callback)
    .catch(onError)
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
          {formatValue(valueDestroyed)} destroyed · {formatValue(valueLost)}{" "}
          lost
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
      <Typography variant="h6" sx={{ mb: 1 }}>
        Faction matchup matrix
      </Typography>
      <Typography variant="body2" sx={{ color: "text.secondary", mb: 2 }}>
        Model-predicted advantage for the row general over the column general,
        with both players and the map unknown - the faction matchup in
        isolation. Each cell is percentage points above/below the grid's median
        draw ({(medianProbAWins * 100).toFixed(0)}%), not an absolute win rate.
        Faded cells ({cells.length - nSignificant} of {cells.length}) aren't
        distinguishable from a coin flip across an {ensembleSize}-model ensemble
        trained on this much data - only the {nSignificant} solid cells hold up.
      </Typography>
      <TableContainer sx={{ overflowX: "auto" }}>
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell />
              {generals.map((g) => (
                <TableCell key={g} align="center" sx={{ fontWeight: 600 }}>
                  {toGeneralName(g)}
                </TableCell>
              ))}
            </TableRow>
          </TableHead>
          <TableBody>
            {generals.map((rowGeneral) => (
              <TableRow key={rowGeneral}>
                <TableCell sx={{ fontWeight: 600, whiteSpace: "nowrap" }}>
                  {toGeneralName(rowGeneral)}
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
                      title={`${(prob * 100).toFixed(1)}% ± ${(std * 100).toFixed(1)}pp across ${ensembleSize} models${significant ? "" : " - not significant"}`}
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
  const [matrix, setMatrix] = React.useState<FactionMatrix | null>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    let cancelled = false
    Client.predictFactionMatrixApiPredictFactionMatrixGet()
      .then((res) => {
        if (!cancelled) setMatrix(res)
      })
      .catch(() => {
        // Model unavailable (503) or any other failure - best-effort, just
        // skip the section rather than erroring the whole page.
        if (!cancelled) setMatrix(null)
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [])

  if (loading) return <Loading />
  if (!matrix) return null
  return <FactionMatrixTable matrix={matrix} />
}

const empty = { generalStats: [] }

export default function DisplayGeneralStats() {
  const [generalStats, setGeneralStats] = React.useState<GeneralStats>(empty)
  const [format, setFormat] = React.useState<GameFormat>("All")
  const { showError, errorSnackbar } = useErrorSnackbar()
  React.useEffect(() => {
    setGeneralStats(empty)
    getGeneralStats(format, setGeneralStats, showError)
  }, [format, showError])

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

  if (generalStats.generalStats.length === 0) {
    return <Loading />
  }

  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000, p: 2 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          mb: 2,
        }}
      >
        <Typography variant="h6">Game Format:</Typography>
        <ToggleButtonGroup
          value={format}
          exclusive
          onChange={(_, v) => v && setFormat(v)}
          size="small"
        >
          {FORMAT_OPTIONS.map((f) => (
            <ToggleButton key={f} value={f}>
              {f}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Stack>
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
      {errorSnackbar}
    </Paper>
  )
}
