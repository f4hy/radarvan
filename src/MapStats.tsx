import Tooltip from "@mui/material/Tooltip"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Tab from "@mui/material/Tab"
import TextField from "@mui/material/TextField"
import Tabs from "@mui/material/Tabs"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Typography from "@mui/material/Typography"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import DisplayGeneral from "./Generals"
import type { MapData, MapStatsResponse } from "./api"
import { MapClient } from "./clients/map"
import { toGeneralName } from "./general_utils"
import GameMap, { MapThumbnail } from "./Map"
import Page from "./Page"
import { useUrlChoice, useUrlParam } from "./useUrlState"
import { queryFallback } from "./QueryState"
import { WinRateBar } from "./WinRateChip"
import { PlayerLabel } from "./PlayerChip"
import { useIsAdmin } from "./AuthContext"
import { displayMapName, winRate } from "./utils"

function fetchMapStats(): Promise<MapStatsResponse> {
  return MapClient.getMapStatsApiMapStatsGet()
}

function mapId(mapName: string): string {
  return `map-${mapName.replace(/[^a-zA-Z0-9]/g, "-")}`
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
            sx={{
              color: "text.secondary",
              whiteSpace: "nowrap",
            }}
          >
            {(rate * 100).toFixed(0)}% ({props.wins}W–{props.losses}L)
            {deltaStr && (
              <Tooltip title="Win rate of this general on this map above that general's average win rate">
                <Typography
                  variant="caption"
                  color={deltaColor}
                  sx={{
                    fontWeight: "bold",
                  }}
                >
                  {deltaStr}
                </Typography>
              </Tooltip>
            )}
          </Typography>
        </Box>
      </Box>
      <WinRateBar wins={props.wins} losses={props.losses} />
    </Box>
  )
}

function PlayerWinRates(props: { players: MapData["playerStats"] }) {
  const sorted = [...props.players]
    .filter((p) => p.wins + p.losses >= 3)
    .sort((a, b) => winRate(b.wins, b.losses) - winRate(a.wins, a.losses))

  if (sorted.length === 0) {
    return (
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
        }}
      >
        Not enough data
      </Typography>
    )
  }

  return (
    <Stack>
      {sorted.map((p) => (
        <WinRateRow
          key={p.player}
          label={<PlayerLabel name={p.player} />}
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
  const displayName = displayMapName(props.entry.mapName)
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
  rows: Array<[number, BestWorst]>
  onMapClick: (mapName: string) => void
}) {
  const { rows } = props
  if (rows.length === 0) return null
  return (
    <Paper variant="outlined" sx={{ p: 2, flexGrow: 1 }}>
      <Typography
        variant="subtitle1"
        sx={{
          fontWeight: "bold",
          mb: 1,
        }}
      >
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
  rows: Array<[string, BestWorst]>
  onMapClick: (mapName: string) => void
}) {
  const { rows } = props
  if (rows.length === 0) return null
  return (
    <Paper variant="outlined" sx={{ p: 2, flexGrow: 1 }}>
      <Typography
        variant="subtitle1"
        sx={{
          fontWeight: "bold",
          mb: 1,
        }}
      >
        Player Best / Worst Maps
      </Typography>
      <Stack spacing={0.75}>
        {rows.map(([player, bw]) => (
          <BestWorstBadgePair
            key={player}
            bw={bw}
            onMapClick={props.onMapClick}
            label={
              <Box sx={{ minWidth: 110 }}>
                <PlayerLabel name={player} />
              </Box>
            }
          />
        ))}
      </Stack>
    </Paper>
  )
}

// --- Per-map accordion ---

const MapCard = React.memo(function MapCard(props: {
  map: MapData
  expanded: boolean
  onToggle: (mapName: string, expanded: boolean) => void
}) {
  const { map } = props
  const debug = useIsAdmin()
  const [tab, setTab] = React.useState<"players" | "generals">("generals")

  return (
    <Accordion
      id={mapId(map.mapName)}
      expanded={props.expanded}
      onChange={(_, isExpanded) => props.onToggle(map.mapName, isExpanded)}
      slotProps={{
        // unmountOnExit: with ~80 maps on the page, keeping every collapsed
        // map's win-rate tables and general icons mounted put >13k nodes in the
        // DOM (and ~850 <img>s) for the handful actually expanded, which made
        // every layout on this page cost tens of ms.
        transition: {
          unmountOnExit: true,
          onExit: () => setTab("generals"),
        },
      }}
    >
      <AccordionSummary expandIcon={<ArrowDownwardIcon />}>
        <Stack
          direction="row"
          spacing={1.5}
          sx={{
            alignItems: "center",
          }}
        >
          {/* Eighty collapsed rows of map names read as eighty strings; the
              picture is how anyone actually recognises a map. */}
          <MapThumbnail mapname={map.mapName} />
          <Typography
            sx={{
              fontWeight: "bold",
            }}
          >
            {displayMapName(map.mapName)}
          </Typography>
          <Chip
            label={`${map.totalGames} games`}
            size="small"
            variant="outlined"
          />
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Stack
          direction="row"
          spacing={2}
          sx={{
            alignItems: "flex-start",
          }}
        >
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
})

// The backend already drops maps under 5 games (map_stats.MIN_GAMES), which
// still leaves eighty of them, half sitting on a handful of games where every
// win rate is noise. This is the reader's own floor on top of that: a browsing
// aid, so it never applies to a search - if you typed a map's name you want
// that map, however little we have on it.
const MIN_GAMES_OPTIONS = [5, 10, 20] as const
type MinGames = (typeof MIN_GAMES_OPTIONS)[number]
const DEFAULT_MIN_GAMES: MinGames = 10

export default function DisplayMapStats() {
  const [expandedMaps, setExpandedMaps] = React.useState<Set<string>>(new Set())
  // `replace` while typing: one history entry per keystroke would take a dozen
  // presses of Back to leave the page.
  const [searchParam, setSearch] = useUrlParam("q", { replace: true })
  const search = searchParam ?? ""
  const [minGames, setMinGames] = useUrlChoice(
    "minGames",
    MIN_GAMES_OPTIONS,
    DEFAULT_MIN_GAMES,
  )
  // The map this page is pointed at, if any. Clicking a general's best/worst
  // badge used to expand and scroll to a map while leaving the URL on the bare
  // page, so the one view here worth sending someone was the one view that
  // couldn't be sent. It is also what makes Back undo a jump.
  const [focusedMap, setFocusedMap] = useUrlParam("map")
  // Maps a best/worst badge sent us to, kept visible regardless of the floor -
  // otherwise clicking "worst map" for a general scrolls to nothing whenever
  // that map is one of the thin ones the floor is there to hide.
  const [pinned, setPinned] = React.useState<Set<string>>(new Set())
  const [scrollTo, setScrollTo] = React.useState<string | null>(null)
  const mapStatsQuery = useQuery({
    queryKey: ["mapStats"],
    queryFn: fetchMapStats,
  })
  const mapStats = mapStatsQuery.data

  React.useEffect(() => {
    if (mapStats) {
      setExpandedMaps(new Set(mapStats.maps.slice(0, 3).map((m) => m.mapName)))
    }
  }, [mapStats])

  // One path for every way `?map=` can arrive — a pasted link, a badge click,
  // Back — so the three can't drift. It runs after the seed above and adds to
  // it rather than replacing, which is why both use the updater form.
  React.useEffect(() => {
    if (focusedMap === null || !mapStats) return
    setExpandedMaps((prev) => new Set([...prev, focusedMap]))
    setPinned((prev) => new Set([...prev, focusedMap]))
    // Not an inline scrollIntoView: pinning may be what puts the row on the
    // page at all, so the scroll has to wait for that render.
    setScrollTo(focusedMap)
  }, [focusedMap, mapStats])

  const handleToggle = React.useCallback(
    (mapName: string, isExpanded: boolean) => {
      setExpandedMaps((prev) => {
        const next = new Set(prev)
        if (isExpanded) next.add(mapName)
        else next.delete(mapName)
        return next
      })
    },
    [],
  )

  // Only the URL is set: the effect above turns that into expand + pin +
  // scroll, so a click and a pasted link do exactly the same thing.
  const handleMapClick = React.useCallback(
    (mapName: string) => setFocusedMap(mapName),
    [setFocusedMap],
  )

  React.useEffect(() => {
    if (scrollTo === null) return
    document
      .getElementById(mapId(scrollTo))
      ?.scrollIntoView({ behavior: "smooth", block: "start" })
    setScrollTo(null)
  }, [scrollTo])

  const query = search.trim().toLowerCase()
  const visibleMaps = React.useMemo(() => {
    const maps = mapStats?.maps ?? []
    if (query !== "") {
      return maps.filter((m) =>
        displayMapName(m.mapName).toLowerCase().includes(query),
      )
    }
    return maps.filter((m) => m.totalGames >= minGames || pinned.has(m.mapName))
  }, [mapStats, query, minGames, pinned])

  const generalBestWorst = React.useMemo(
    () => (mapStats ? computeGeneralBestWorst(mapStats.maps) : []),
    [mapStats],
  )
  const playerBestWorst = React.useMemo(
    () => (mapStats ? computePlayerBestWorst(mapStats.maps) : []),
    [mapStats],
  )

  const fallback = queryFallback(mapStatsQuery, "map stats")
  if (fallback) return fallback

  const hiddenCount = (mapStats?.maps.length ?? 0) - visibleMaps.length

  return (
    <Page
      title="Map Stats"
      description="Which generals and which players do well on each map. A player needs at least 3 games on a map to appear."
      actions={
        <>
          <TextField
            size="small"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search maps"
            sx={{ width: 240 }}
          />
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            Min games
          </Typography>
          <ToggleButtonGroup
            value={minGames}
            exclusive
            size="small"
            disabled={query !== ""}
            onChange={(_, next: MinGames | null) =>
              next !== null && setMinGames(next)
            }
          >
            {MIN_GAMES_OPTIONS.map((n) => (
              <ToggleButton key={n} value={n}>
                {n}+
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {visibleMaps.length} of {mapStats?.maps.length ?? 0} maps
            {query === "" && hiddenCount > 0
              ? `, ${hiddenCount} below the floor`
              : ""}
          </Typography>
        </>
      }
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        spacing={2}
        sx={{
          alignItems: "flex-start",
          mb: 2,
        }}
      >
        <GeneralBestWorstSummary
          rows={generalBestWorst}
          onMapClick={handleMapClick}
        />
        <PlayerBestWorstSummary
          rows={playerBestWorst}
          onMapClick={handleMapClick}
        />
      </Stack>
      <Divider sx={{ mb: 1 }} />
      {visibleMaps.length === 0 ? (
        <Typography variant="body2" sx={{ color: "text.secondary", py: 2 }}>
          No maps match “{search}”.
        </Typography>
      ) : (
        visibleMaps.map((m) => (
          <MapCard
            key={m.mapName}
            map={m}
            expanded={expandedMaps.has(m.mapName)}
            onToggle={handleToggle}
          />
        ))
      )}
    </Page>
  )
}
