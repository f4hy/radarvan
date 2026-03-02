import Tooltip from "@mui/material/Tooltip"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Divider from "@mui/material/Divider"
import LinearProgress from "@mui/material/LinearProgress"
import Loading from "./Loading"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Tab from "@mui/material/Tab"
import Tabs from "@mui/material/Tabs"
import Typography from "@mui/material/Typography"
import * as React from "react"
import DisplayGeneral from "./Generals"
import { MapData, MapStatsResponse } from "./api"
import { Client } from "./Client"
import { toGeneralName } from "./general_utils"
import Map from "./Map"
import { useErrorSnackbar } from "./useErrorSnackbar"
import { isDebug, winRate } from "./utils"

function getMapStats(
  callback: (m: MapStatsResponse) => void,
  onError = console.error,
) {
  Client.getMapStatsApiMapStatsGet().then(callback).catch(onError)
}

const getRateColor = (rate: number): "success" | "warning" | "error" => {
  if (rate >= 0.55) return "success"
  if (rate >= 0.45) return "warning"
  return "error"
}

function WinRateRow(props: {
  label: React.ReactNode
  wins: number
  losses: number
  delta?: number
}) {
  const rate = winRate(props.wins, props.losses)
  const { delta } = props
  const deltaColor =
    delta === undefined || Math.abs(delta) < 0.01
      ? "text.secondary"
      : delta > 0
        ? "success.main"
        : "error.main"
  const deltaStr =
    delta !== undefined && Math.abs(delta) >= 0.01
      ? ` delta from generals ave ${delta > 0 ? "+" : ""}${(delta * 100).toFixed(0)}%`
      : null
  return (
    <Box sx={{ mb: 1 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.25 }}>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          {props.label}
        </Box>
        <Box sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ whiteSpace: "nowrap" }}
          >
            {(rate * 100).toFixed(0)}% ({props.wins}W–{props.losses}L)
            {deltaStr && (
              <Tooltip title="Win rate of this general on this map above that general's average win rate">
                <Typography
                  variant="caption"
                  color={deltaColor}
                  fontWeight="bold"
                >
                  {deltaStr}
                </Typography>
              </Tooltip>
            )}
          </Typography>
        </Box>
      </Box>
      <LinearProgress
        variant="determinate"
        value={rate * 100}
        color={getRateColor(rate)}
        sx={{ height: 7, borderRadius: 4 }}
      />
    </Box>
  )
}

function PlayerWinRates(props: { players: MapData["playerStats"] }) {
  const sorted = [...props.players]
    .filter((p) => p.wins + p.losses >= 3)
    .sort((a, b) => winRate(b.wins, b.losses) - winRate(a.wins, a.losses))

  if (sorted.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        Not enough data
      </Typography>
    )
  }

  return (
    <Stack>
      {sorted.map((p) => (
        <WinRateRow
          key={p.player}
          label={<Typography variant="body2">{p.player}</Typography>}
          wins={p.wins}
          losses={p.losses}
        />
      ))}
    </Stack>
  )
}

function GeneralWinRates(props: { generals: MapData["generalStats"] }) {
  const sorted = [...props.generals].sort(
    (a, b) => winRate(b.wins, b.losses) - winRate(a.wins, a.losses),
  )

  return (
    <Stack>
      {sorted.map((g) => (
        <WinRateRow
          key={g.general}
          label={
            <>
              <DisplayGeneral general={g.general} />
              <Typography variant="body2">
                {toGeneralName(g.general)}
              </Typography>
            </>
          }
          wins={g.wins}
          losses={g.losses}
          delta={g.winRateDelta}
        />
      ))}
    </Stack>
  )
}

function MapCard(props: { map: MapData; defaultExpanded: boolean }) {
  const { map } = props
  const debug = isDebug()
  const [tab, setTab] = React.useState<"players" | "generals">("generals")

  return (
    <Accordion defaultExpanded={props.defaultExpanded}>
      <AccordionSummary expandIcon={<ArrowDownwardIcon />}>
        <Stack direction="row" spacing={1} alignItems="center">
          <Typography fontWeight="bold">
            {map.mapName.replace(/\.[^.]+$/, "")}
          </Typography>
          <Chip
            label={`${map.totalGames} games`}
            size="small"
            variant="outlined"
          />
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Stack direction="row" spacing={2} alignItems="flex-start">
          <Map mapname={map.mapName} />
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <Tabs value={tab} onChange={(_, v) => setTab(v)} sx={{ mb: 1 }}>
              <Tab value="generals" label="Generals" />
              {debug && <Tab value="players" label="Players" />}
            </Tabs>
            {tab === "generals" && (
              <GeneralWinRates generals={map.generalStats} />
            )}
            {tab === "players" && <PlayerWinRates players={map.playerStats} />}
          </Box>
        </Stack>
      </AccordionDetails>
    </Accordion>
  )
}

export default function DisplayMapStats() {
  const [mapStats, setMapStats] = React.useState<MapStatsResponse | null>(null)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    getMapStats(setMapStats, showError)
  }, [showError])

  if (mapStats === null) {
    return (
      <>
        <Loading />
        {errorSnackbar}
      </>
    )
  }

  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000 }}>
      <Typography variant="h4">Map Stats</Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        Win rates from competitive games. Players shown with ≥3 games on map.
        Maps sorted by total games played.
      </Typography>
      <Divider sx={{ mb: 1 }} />
      {mapStats.maps.map((m, i) => (
        <MapCard key={m.mapName} map={m} defaultExpanded={i < 3} />
      ))}
      {errorSnackbar}
    </Paper>
  )
}
