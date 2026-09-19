import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Autocomplete from "@mui/material/Autocomplete"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import Link from "@mui/material/Link"
import Stack from "@mui/material/Stack"
import TextField from "@mui/material/TextField"
import Typography from "@mui/material/Typography"

import groupBy from "lodash/groupBy"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import { Link as RouterLink, useSearchParams } from "react-router"

import type { MatchInfo, Matches, PlayerRatingDailyChange } from "../../api"
import { MapClient } from "../../clients/map"
import { MatchesClient } from "../../clients/matches"
import { PlayersClient } from "../../clients/players"
import FormatToggle, { ALL_FORMATS } from "../../components/FormatToggle"
import { MatchesLoading, MatchRowLoading } from "../../components/Loading"
import { MatchCard, normalizePlayerName } from "../../components/MatchCard"
import Page from "../../components/Page"
import { queryFallback } from "../../components/QueryState"
import { useIsAdmin } from "../../lib/AuthContext"
import { usePlayerColors } from "../../lib/PlayerColorsContext"
import { gameNightHref } from "../../lib/links"
import { useUrlPatch } from "../../lib/useUrlState"
import {
  displayMapName,
  isObserver,
  localDate,
  winRateTone,
} from "../../lib/utils"

type GameFormat = (typeof ALL_FORMATS)[number]

/** What the reader has narrowed the history down to. */
interface MatchFilters {
  player: string | null
  mapName: string | null
  format: GameFormat
}

const NO_FILTERS: MatchFilters = { player: null, mapName: null, format: "All" }

function hasActiveFilters(filters: MatchFilters): boolean {
  return (
    filters.player !== null ||
    filters.mapName !== null ||
    filters.format !== "All"
  )
}

/** The filters as query params, with "not filtering on this" left off entirely.
 *
 * Both endpoints below take the same three, which is the point: the night list
 * and the matches inside a night are filtered by the same server-side rule, so
 * a night's headline count always equals what it expands to. */
function filterParams(filters: MatchFilters) {
  return {
    player: filters.player ?? undefined,
    mapName: filters.mapName ?? undefined,
    gameFormat: filters.format === "All" ? undefined : filters.format,
  }
}

function fetchDates(filters: MatchFilters): Promise<{ [key: string]: number }> {
  return MatchesClient.getDatesApiDatesGet(filterParams(filters))
}

function fetchMatches(
  date: Date,
  filters: MatchFilters,
  excludeDev: boolean,
): Promise<Matches> {
  // Hide dev-build matches (is_dev) for non-admins.
  return MatchesClient.getMatchesByDateApiMatchesByDateDateGet({
    date: date,
    excludeDev: excludeDev,
    ...filterParams(filters),
  })
}

const empty = { matches: [] }

function MatchDateSummary(props: {
  date: string
  count: number
  matches: MatchInfo[]
  ratingChanges?: PlayerRatingDailyChange[]
}) {
  const date = localDate(props.date)
  const categoryChips =
    props.matches.length > 0
      ? Object.entries(
          groupBy(props.matches, (m) =>
            m.composition?.isFfa ? "FFA" : (m.composition?.category ?? "?"),
          ),
        ).map(([cat, ms]) => (
          <Chip
            key={cat}
            label={`${ms.length}× ${cat}`}
            size="small"
            variant="outlined"
          />
        ))
      : []

  const wlChips = (() => {
    if (props.matches.length === 0) return []
    const wl: Record<string, { w: number; l: number }> = {}
    for (const m of props.matches) {
      if (m.incomplete) continue
      for (const p of m.players) {
        if (isObserver(p)) continue
        if (!wl[p.name]) wl[p.name] = { w: 0, l: 0 }
        if (p.won) wl[p.name].w++
        else wl[p.name].l++
      }
    }
    return Object.entries(wl).map(([name, { w, l }]) => (
      <Chip
        key={name}
        label={`${normalizePlayerName(name)}: ${w}-${l}`}
        size="small"
        variant="outlined"
        // Shared verdict (utils.winRateTone) rather than a local red-to-green
        // ramp: one night is a small sample, so most chips read neutral and the
        // ones that don't actually mean something.
        sx={{ borderColor: winRateTone(w, l).hex, borderWidth: 2 }}
      />
    ))
  })()

  const ratingItems = (props.ratingChanges ?? []).map((r) => {
    const scaled = Math.round(r.delta * 10)
    const color = scaled >= 0 ? "success.main" : "error.main"
    const prefix = scaled >= 0 ? "+" : ""
    return (
      <Typography key={r.name} variant="body2" color={color}>
        {normalizePlayerName(r.name)}: {prefix}
        {scaled}
      </Typography>
    )
  })

  return (
    <Stack sx={{ flexGrow: 1, minWidth: 0 }}>
      <Stack
        direction="row"
        spacing={2}
        sx={{
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <Typography
          sx={{
            fontWeight: "bold",
          }}
        >
          {date.toLocaleString("en-US", {
            weekday: "short",
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
          })}
        </Typography>
        <Typography
          sx={{
            color: "text.secondary",
          }}
        >
          {props.count} {props.count === 1 ? "game" : "games"}
        </Typography>
        {/* Straight to that night's recap page. A real link rather than a
            navigate() callback so it is copyable and opens in a new tab -
            sharing one night in chat is what the recap page is for. Routed
            through RouterLink so it doesn't reload the app on a normal click.
            Clicks are stopped from reaching the AccordionSummary, which would
            otherwise toggle the row open on the way out. */}
        <Link
          component={RouterLink}
          to={gameNightHref(props.date)}
          underline="hover"
          variant="body2"
          onClick={(e) => e.stopPropagation()}
        >
          Recap
        </Link>
        {categoryChips.length > 0 && (
          <Stack
            direction="row"
            spacing={1}
            sx={{
              flexWrap: "wrap",
            }}
          >
            {categoryChips}
          </Stack>
        )}
      </Stack>
      {(wlChips.length > 0 || ratingItems.length > 0) && (
        <Stack
          direction="row"
          spacing={1}
          sx={{
            flexWrap: "wrap",
            mt: 0.5,
            display: { xs: "none", sm: "flex" },
          }}
        >
          {wlChips}
          {ratingItems}
        </Stack>
      )}
    </Stack>
  )
}

function DisplayMatchesForDate(props: {
  dateStr: string // backend game-night date key, "YYYY-MM-DD"
  count: number
  filters: MatchFilters
  /** The most recent night opens on arrival; older ones are one click. */
  openByDefault: boolean
}) {
  const [expanded, setExpanded] = React.useState<boolean>(props.openByDefault)
  const isAdmin = useIsAdmin()
  // The generated client serializes Date params via toISOString() (UTC), so
  // the API param must be UTC midnight of the backend's date key — which is
  // exactly what new Date("YYYY-MM-DD") produces. Display uses the raw string.
  const apiDate = React.useMemo(() => new Date(props.dateStr), [props.dateStr])

  // Both queries are keyed on the filter set as well as the night, which is
  // what makes an already-expanded row refetch instead of showing what it
  // loaded under the old filter. `enabled` keeps a collapsed night silent.
  const matchesQuery = useQuery({
    queryKey: ["matchesByDate", props.dateStr, props.filters, isAdmin],
    queryFn: () => fetchMatches(apiDate, props.filters, !isAdmin),
    enabled: expanded,
  })
  const ratingChangesQuery = useQuery({
    queryKey: ["ratingDailyChanges", props.dateStr],
    queryFn: () =>
      PlayersClient.getPlayerRatingDailyChangesApiPlayerRatingsDailyChangesGet({
        forDate: apiDate,
      }),
    enabled: expanded,
  })
  const matchList = matchesQuery.data ?? empty
  const ratingChanges = ratingChangesQuery.data ?? []

  const handleChange = React.useCallback(
    (_event: React.SyntheticEvent, isExpanded: boolean) => {
      setExpanded(isExpanded)
    },
    [],
  )
  return (
    <Accordion expanded={expanded === true} onChange={handleChange}>
      <AccordionSummary expandIcon={<ArrowDownwardIcon />}>
        <MatchDateSummary
          date={props.dateStr}
          count={props.count}
          matches={matchList.matches}
          ratingChanges={ratingChanges}
        />
      </AccordionSummary>
      <AccordionDetails sx={{ bgcolor: "background.default" }}>
        {queryFallback(matchesQuery, "this night's games") ??
          (matchList.matches.length === 0 ? (
            <MatchRowLoading />
          ) : (
            matchList.matches.map((m, matchIdx) => (
              <MatchCard match={m} key={m.id} idx={matchIdx} />
            ))
          ))}
      </AccordionDetails>
    </Accordion>
  )
}

/** Player, map and format, as one row of controls.
 *
 * Players come from the colors already loaded at app startup rather than a
 * request of their own; maps from the match-count endpoint, so the list is
 * ordered by how often we actually play them and the value sent back is the
 * stored map string the backend matches on, not a prettied-up display name.
 */
function MatchFilterBar(props: {
  filters: MatchFilters
  mapOptions: string[]
  onChange: (filters: MatchFilters) => void
}) {
  const { filters, onChange } = props
  const colors = usePlayerColors()
  const playerOptions = React.useMemo(
    () => Object.keys(colors).sort(),
    [colors],
  )
  const cleared = !hasActiveFilters(filters)
  return (
    <>
      <Autocomplete
        options={playerOptions}
        value={filters.player}
        onChange={(_, player) => onChange({ ...filters, player })}
        size="small"
        sx={{ width: 200 }}
        renderInput={(params) => <TextField {...params} label="Player" />}
      />
      <Autocomplete
        options={props.mapOptions}
        value={filters.mapName}
        onChange={(_, mapName) => onChange({ ...filters, mapName })}
        getOptionLabel={displayMapName}
        size="small"
        sx={{ width: 260 }}
        renderInput={(params) => <TextField {...params} label="Map" />}
      />
      <FormatToggle
        options={ALL_FORMATS}
        value={filters.format}
        onChange={(format) => onChange({ ...filters, format })}
      />
      <Button
        size="small"
        disabled={cleared}
        onClick={() => onChange(NO_FILTERS)}
      >
        Clear
      </Button>
    </>
  )
}

const NIGHTS_PER_PAGE = 25

export default function DisplayMatches() {
  // The three filters are one fact for everything downstream — the query key,
  // the remount key, `hasActiveFilters` — so they are read as one object and
  // written in one go. Written separately they would clobber each other; see
  // useUrlPatch.
  const [params] = useSearchParams()
  const patch = useUrlPatch()
  const filters: MatchFilters = React.useMemo(
    () => ({
      player: params.get("player"),
      mapName: params.get("map"),
      // Validated, not trusted: `format` goes straight out as an API query
      // parameter, so an unknown one reads as "All".
      format:
        ALL_FORMATS.find((f) => f === params.get("format")) ??
        NO_FILTERS.format,
    }),
    [params],
  )
  const setFilters = React.useCallback(
    (next: MatchFilters) =>
      patch({
        player: next.player,
        map: next.mapName,
        format: next.format === NO_FILTERS.format ? null : next.format,
      }),
    [patch],
  )
  const [visibleNights, setVisibleNights] = React.useState(NIGHTS_PER_PAGE)

  const datesQuery = useQuery({
    queryKey: ["dates", filters],
    queryFn: () => fetchDates(filters),
  })
  const dates = datesQuery.data ?? null

  // Changing the filter set starts the list over: page 3 of the old filter is
  // not page 3 of the new one.
  React.useEffect(() => {
    setVisibleNights(NIGHTS_PER_PAGE)
  }, [filters])

  // Best-effort: without it the map filter is an empty picker, which is better
  // than failing the page.
  const { data: mapOptions = [] } = useQuery({
    queryKey: ["mapMatchCounts"],
    queryFn: async () => {
      const counts = await MapClient.getMapMatchCountsApiMapMatchCountsGet()
      return counts.map((c) => c.map)
    },
    retry: false,
  })

  const nights = Object.entries(dates ?? {})
  const shown = nights.slice(0, visibleNights)
  const totalGames = nights.reduce((sum, [, count]) => sum + count, 0)
  const filtered = hasActiveFilters(filters)
  // Remounts every night's row when the filters move, so a night that was
  // already expanded refetches under the new filter instead of showing the
  // matches it loaded under the old one.
  const filterKey = `${filters.player ?? ""}|${filters.mapName ?? ""}|${filters.format}`

  return (
    <Page
      surface={false}
      title="Matches"
      description="Every game we have played, newest night first."
      actions={
        <MatchFilterBar
          filters={filters}
          mapOptions={mapOptions}
          onChange={setFilters}
        />
      }
    >
      {dates === null ? (
        <MatchesLoading />
      ) : nights.length === 0 ? (
        <Typography variant="body2" sx={{ color: "text.secondary", py: 2 }}>
          No games match these filters.
        </Typography>
      ) : (
        <Stack>
          <Typography
            variant="body2"
            sx={{ color: "text.secondary", mb: 1, px: 0.5 }}
          >
            {nights.length} {nights.length === 1 ? "night" : "nights"},{" "}
            {totalGames} {totalGames === 1 ? "game" : "games"}
            {filtered ? " matching" : ""}
          </Typography>
          {shown.map(([date, count], idx) => (
            <DisplayMatchesForDate
              key={`${date}|${filterKey}`}
              dateStr={date}
              count={count}
              filters={filters}
              openByDefault={idx === 0}
            />
          ))}
          {nights.length > shown.length && (
            <Button
              onClick={() => setVisibleNights((v) => v + NIGHTS_PER_PAGE)}
              sx={{ mt: 2, alignSelf: "center" }}
            >
              Show older nights ({nights.length - shown.length} left)
            </Button>
          )}
        </Stack>
      )}
    </Page>
  )
}
