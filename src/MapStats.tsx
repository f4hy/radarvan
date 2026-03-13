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
import GameMap from "./Map"
import { useErrorSnackbar } from "./useErrorSnackbar"
import { isDebug, winRate } from "./utils"

function getMapStats(
  callback: (m: MapStatsResponse) => void,
  onError = console.error,
) {
  Client.getMapStatsApiMapStatsGet().then(callback).catch(onError)
}

function mapId(mapName: string): string {
  return `map-${mapName.replace(/[^a-zA-Z0-9]/g, "-")}`
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

// --- Best/Worst summary ---

const MIN_SUMMARY_GAMES = 3

interface MapEntry {
  mapName: string
  wins: number
  losses: number
}

interface BestWorst {
  best: MapEntry
  worst: MapEntry
}

function computeGeneralBestWorst(maps: MapData[]): Array<[number, BestWorst]> {
  const acc = new Map<
    number,
    { best: MapEntry | null; worst: MapEntry | null }
  >()
  for (const map of maps) {
    for (const g of map.generalStats) {
      if (g.wins + g.losses < MIN_SUMMARY_GAMES) continue
      const wr = winRate(g.wins, g.losses)
      const entry: MapEntry = {
        mapName: map.mapName,
        wins: g.wins,
        losses: g.losses,
      }
      const cur = acc.get(g.general) ?? { best: null, worst: null }
      if (!cur.best || wr > winRate(cur.best.wins, cur.best.losses))
        cur.best = entry
      if (!cur.worst || wr < winRate(cur.worst.wins, cur.worst.losses))
        cur.worst = entry
      acc.set(g.general, cur)
    }
  }
  const result: Array<[number, BestWorst]> = []
  for (const [g, bw] of acc.entries()) {
    if (bw.best && bw.worst && bw.best.mapName !== bw.worst.mapName) {
      result.push([g, { best: bw.best, worst: bw.worst }])
    }
  }
  result.sort(
    ([, a], [, b]) =>
      winRate(b.best.wins, b.best.losses) - winRate(a.best.wins, a.best.losses),
  )
  return result
}

function computePlayerBestWorst(maps: MapData[]): Array<[string, BestWorst]> {
  const acc = new Map<
    string,
    { best: MapEntry | null; worst: MapEntry | null }
  >()
  for (const map of maps) {
    for (const p of map.playerStats) {
      if (p.wins + p.losses < MIN_SUMMARY_GAMES) continue
      const wr = winRate(p.wins, p.losses)
      const entry: MapEntry = {
        mapName: map.mapName,
        wins: p.wins,
        losses: p.losses,
      }
      const cur = acc.get(p.player) ?? { best: null, worst: null }
      if (!cur.best || wr > winRate(cur.best.wins, cur.best.losses))
        cur.best = entry
      if (!cur.worst || wr < winRate(cur.worst.wins, cur.worst.losses))
        cur.worst = entry
      acc.set(p.player, cur)
    }
  }
  const result: Array<[string, BestWorst]> = []
  for (const [p, bw] of acc.entries()) {
    if (bw.best && bw.worst && bw.best.mapName !== bw.worst.mapName) {
      result.push([p, { best: bw.best, worst: bw.worst }])
    }
  }
  result.sort(
    ([, a], [, b]) =>
      winRate(b.best.wins, b.best.losses) - winRate(a.best.wins, a.best.losses),
  )
  return result
}

function MapBadge(props: {
  entry: MapEntry
  variant: "best" | "worst"
  onMapClick: (mapName: string) => void
}) {
  const wr = winRate(props.entry.wins, props.entry.losses)
  const displayName = props.entry.mapName.replace(/\.[^.]+$/, "")
  const total = props.entry.wins + props.entry.losses
  return (
    <Tooltip
      title={`${props.entry.wins}W–${props.entry.losses}L (${total} games) — click to scroll`}
    >
      <Chip
        size="small"
        color={props.variant === "best" ? "success" : "error"}
        variant="outlined"
        label={`${displayName} ${(wr * 100).toFixed(0)}%`}
        onClick={() => props.onMapClick(props.entry.mapName)}
        sx={{ fontSize: "0.7rem", cursor: "pointer" }}
      />
    </Tooltip>
  )
}

function BestWorstBadgePair(props: {
  label: React.ReactNode
  bw: BestWorst
  onMapClick: (mapName: string) => void
}) {
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1,
        flexWrap: "wrap",
      }}
    >
      {props.label}
      <MapBadge
        entry={props.bw.best}
        variant="best"
        onMapClick={props.onMapClick}
      />
      <MapBadge
        entry={props.bw.worst}
        variant="worst"
        onMapClick={props.onMapClick}
      />
    </Box>
  )
}

function GeneralBestWorstSummary(props: {
  maps: MapData[]
  onMapClick: (mapName: string) => void
}) {
  const rows = computeGeneralBestWorst(props.maps)
  if (rows.length === 0) return null
  return (
    <Paper variant="outlined" sx={{ p: 2, flexGrow: 1 }}>
      <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 1 }}>
        General Best / Worst Maps
      </Typography>
      <Stack spacing={0.75}>
        {rows.map(([general, bw]) => (
          <BestWorstBadgePair
            key={general}
            bw={bw}
            onMapClick={props.onMapClick}
            label={
              <Box
                sx={{
                  display: "flex",
                  alignItems: "center",
                  gap: 0.5,
                  minWidth: 130,
                }}
              >
                <DisplayGeneral general={general} />
                <Typography variant="body2">
                  {toGeneralName(general)}
                </Typography>
              </Box>
            }
          />
        ))}
      </Stack>
    </Paper>
  )
}

function PlayerBestWorstSummary(props: {
  maps: MapData[]
  onMapClick: (mapName: string) => void
}) {
  const rows = computePlayerBestWorst(props.maps)
  if (rows.length === 0) return null
  return (
    <Paper variant="outlined" sx={{ p: 2, flexGrow: 1 }}>
      <Typography variant="subtitle1" fontWeight="bold" sx={{ mb: 1 }}>
        Player Best / Worst Maps
      </Typography>
      <Stack spacing={0.75}>
        {rows.map(([player, bw]) => (
          <BestWorstBadgePair
            key={player}
            bw={bw}
            onMapClick={props.onMapClick}
            label={
              <Typography variant="body2" sx={{ minWidth: 80 }}>
                {player}
              </Typography>
            }
          />
        ))}
      </Stack>
    </Paper>
  )
}

// --- Per-map accordion ---

function MapCard(props: {
  map: MapData
  expanded: boolean
  onToggle: (expanded: boolean) => void
}) {
  const { map } = props
  const debug = isDebug()
  const [tab, setTab] = React.useState<"players" | "generals">("generals")

  return (
    <Accordion
      id={mapId(map.mapName)}
      expanded={props.expanded}
      onChange={(_, isExpanded) => props.onToggle(isExpanded)}
    >
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
          <GameMap mapname={map.mapName} />
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
  const [expandedMaps, setExpandedMaps] = React.useState<Set<string>>(new Set())
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    getMapStats(setMapStats, showError)
  }, [showError])

  React.useEffect(() => {
    if (mapStats) {
      setExpandedMaps(new Set(mapStats.maps.slice(0, 3).map((m) => m.mapName)))
    }
  }, [mapStats])

  const handleMapClick = React.useCallback((mapName: string) => {
    setExpandedMaps((prev) => new Set([...prev, mapName]))
    document
      .getElementById(mapId(mapName))
      ?.scrollIntoView({ behavior: "smooth", block: "start" })
  }, [])

  if (mapStats === null) {
    return (
      <>
        <Loading />
        {errorSnackbar}
      </>
    )
  }

  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000, p: 2 }}>
      <Typography variant="h4">Map Stats</Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        Win rates from competitive games. Players shown with ≥3 games on map.
        Maps sorted by total games played.
      </Typography>
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        alignItems="flex-start"
        sx={{ mb: 2 }}
      >
        <GeneralBestWorstSummary
          maps={mapStats.maps}
          onMapClick={handleMapClick}
        />
        <PlayerBestWorstSummary
          maps={mapStats.maps}
          onMapClick={handleMapClick}
        />
      </Stack>
      <Divider sx={{ mb: 1 }} />
      {mapStats.maps.map((m) => (
        <MapCard
          key={m.mapName}
          map={m}
          expanded={expandedMaps.has(m.mapName)}
          onToggle={(isExpanded) =>
            setExpandedMaps((prev) => {
              const next = new Set(prev)
              if (isExpanded) next.add(m.mapName)
              else next.delete(m.mapName)
              return next
            })
          }
        />
      ))}
      {errorSnackbar}
    </Paper>
  )
}
