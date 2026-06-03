import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Loading from "./Loading"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import Grid from "@mui/material/Grid"
import Stack from "@mui/material/Stack"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
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
import WinRateRadar from "./WinRateRadar"
import DisplayGeneral from "./Generals"
import { GeneralStat, GeneralStats } from "./api"
import { Client } from "./Client"
import { toGeneralName } from "./general_utils"
import { Typography, useTheme } from "@mui/material"
import useMediaQuery from "@mui/material/useMediaQuery"
import { winRate } from "./utils"
import { CHART_WIN, CHART_LOSS } from "./theme"
import { useErrorSnackbar } from "./useErrorSnackbar"

const FORMAT_OPTIONS = ["All", "1v1", "2v2", "3v3", "4v4"] as const
type GameFormat = (typeof FORMAT_OPTIONS)[number]

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
  const rate = winRate(overallWins, overallLosses)

  return (
    <Box sx={{ flexGrow: 1 }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 0.5 }}>
        <DisplayGeneral general={props.stat.general} />
        <Typography variant="subtitle1" fontWeight="bold">
          {toGeneralName(props.stat.general)}
        </Typography>
        <Chip
          label={`${(rate * 100).toFixed(0)}% (${overallWins}W-${overallLosses}L)`}
          size="small"
          color={rate >= 0.5 ? "success" : "error"}
          variant="outlined"
        />
      </Stack>
    </Box>
  )
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
          winRate(b.total?.wins ?? 0, b.total?.losses ?? 0) -
          winRate(a.total?.wins ?? 0, a.total?.losses ?? 0),
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
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 2 }}>
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
      <Grid container spacing={2} alignItems="flex-start">
        <Grid size={{ xs: 12, md: 4 }}>
          <Typography variant="h6" sx={{ mb: 1 }}>
            Ordered by winrate
          </Typography>
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
      {errorSnackbar}
    </Paper>
  )
}
