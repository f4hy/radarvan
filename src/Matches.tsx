import Box from "@mui/material/Box"
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import DownloadIcon from "@mui/icons-material/Download"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import ErrorIcon from "@mui/icons-material/Error"
import SmartToyIcon from "@mui/icons-material/SmartToy"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Autocomplete from "@mui/material/Autocomplete"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import Card from "@mui/material/Card"
import Collapse from "@mui/material/Collapse"
import IconButton from "@mui/material/IconButton"
import Link from "@mui/material/Link"
import { Link as RouterLink, useSearchParams } from "react-router"
import { gameNightHref } from "./links"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import { MatchesLoading, MatchRowLoading } from "./Loading"
import FormatToggle, { ALL_FORMATS } from "./FormatToggle"
import Page from "./Page"
import { queryFallback } from "./QueryState"
import Stack from "@mui/material/Stack"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import TextField from "@mui/material/TextField"
import Typography from "@mui/material/Typography"

import groupBy from "lodash/groupBy"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import DisplayGeneral from "./Generals"
import GameMap, { type PlayerPosition } from "./Map"
import { toGeneralName } from "./general_utils"
import { PlayersClient } from "./clients/players"
import { FilesClient } from "./clients/files"
import { MapClient } from "./clients/map"
import { MatchesClient } from "./clients/matches"
import {
  type MatchInfo,
  type Matches,
  type Player,
  type PlayerRatingDailyChange,
  Team,
} from "./api"
import QuestionMarkIcon from "@mui/icons-material/QuestionMark"
import { Tooltip } from "@mui/material"
import VisibilityIcon from "@mui/icons-material/Visibility"
import { PlayerDot } from "./PlayerChip"
import { usePlayerColors } from "./PlayerColorsContext"
import {
  displayMapName,
  getColorHex,
  isCompetitor,
  isObserver,
  localDate,
  playerPalette,
  winRateTone,
} from "./utils"
import { useIsAdmin } from "./AuthContext"
import { useUrlPatch } from "./useUrlState"

// ShowMatchDetails drags in recharts, and this is the landing page — most
// visits never expand a match, so it is split out and only fetched on demand.
const ShowMatchDetails = React.lazy(() => import("./ShowMatchDetails"))

function LazyMatchDetails(props: { id: number }) {
  return (
    <React.Suspense fallback={<MatchRowLoading />}>
      <ShowMatchDetails id={props.id} />
    </React.Suspense>
  )
}

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

function normalizePlayerName(name: string): string {
  if (name === "TacticalAI" || name === "Tactical AI") return "T AI"
  const armyMatch = name.match(/^(.+?)\s?Army$/)
  if (armyMatch) return `${armyMatch[1]}A`
  return name
}

function buildPlayerPositions(
  players: Player[],
): Record<number, PlayerPosition> {
  return Object.fromEntries(
    players
      // Observers carry a starting position too, and since these are keyed by
      // it a spectator can otherwise overwrite the real player standing there.
      .filter((p) => isCompetitor(p) && p.startingPosition != null)
      .map((p) => [
        p.startingPosition!,
        {
          name: normalizePlayerName(p.name),
          color: p.color,
          general: toGeneralName(p.general),
        },
      ]),
  )
}

// Win/loss is carried by a single colored status band at the top of an
// otherwise-neutral card, so names stay readable and the page isn't wall-to-wall
// saturated panels. Solid enough for white band text.
const WON_BAND = "#2f8f57"
const LOST_BAND = "#c2544f"
const NEUTRAL_BAND = "#7a828f"

function StatusBand(props: {
  color: string
  icon: React.ReactNode
  label: string
  center?: boolean
}) {
  return (
    <Box
      sx={{
        bgcolor: props.color,
        color: "common.white",
        px: 1.5,
        py: 0.5,
        display: "flex",
        alignItems: "center",
        justifyContent: props.center ? "center" : "flex-start",
        gap: 0.75,
        "& .MuiSvgIcon-root": { fontSize: "1.1rem" },
      }}
    >
      {props.icon}
      <Typography variant="subtitle2" sx={{ fontWeight: 700 }} noWrap>
        {props.label}
      </Typography>
    </Box>
  )
}

function TeamCard(props: { players: Player[]; won: boolean }) {
  const first = props.players[0]
  const team = first?.team
  let label = `${props.won ? "Won" : "Lost"} · Team ${team}`
  let icon = props.won ? <EmojiEventsIcon /> : <ErrorIcon />
  let bandColor = props.won ? WON_BAND : LOST_BAND
  // Observer-ness comes from `role`, not `team` - see utils.isObserver.
  if (first != null && isObserver(first)) {
    label = "Observers"
    icon = <VisibilityIcon />
    bandColor = NEUTRAL_BAND
  } else if (team === Team.NUMBER_0) {
    label = "Unknown Team"
    icon = <QuestionMarkIcon />
    bandColor = NEUTRAL_BAND
  }
  return (
    <Card
      sx={{
        width: { xs: "100%", sm: "50%", md: "auto" },
        flex: { md: 1 },
        minWidth: 0,
        overflow: "hidden",
      }}
    >
      <StatusBand color={bandColor} icon={icon} label={label} />
      <Stack divider={<Divider />}>
        {props.players.map((p) => (
          <Box
            // Color is unique per player in a match; names aren't (twin CPUs).
            key={`${p.name}-${p.color}`}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              px: 1.5,
              py: 1,
            }}
          >
            <DisplayGeneral general={p.general} />
            <PlayerDot color={getColorHex(p.color)} size={10} />
            <Typography
              variant="h6"
              noWrap
              sx={{
                fontWeight: 700,
                color: playerPalette(getColorHex(p.color)).ink,
              }}
            >
              {normalizePlayerName(p.name)}
            </Typography>
          </Box>
        ))}
      </Stack>
    </Card>
  )
}

function FfaPlayerCard(props: { player: Player }) {
  const { player } = props
  return (
    <Card sx={{ minWidth: 150, overflow: "hidden" }}>
      <StatusBand
        color={player.won ? WON_BAND : NEUTRAL_BAND}
        icon={player.won ? <EmojiEventsIcon /> : <ErrorIcon />}
        label={player.won ? "Winner" : "Lost"}
        center
      />
      <Stack
        spacing={1}
        sx={{
          alignItems: "center",
          p: 1.5,
        }}
      >
        <DisplayGeneral general={player.general} />
        <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
          <PlayerDot color={getColorHex(player.color)} size={10} />
          <Typography
            variant="subtitle1"
            noWrap
            sx={{
              fontWeight: 700,
              color: playerPalette(getColorHex(player.color)).ink,
            }}
          >
            {normalizePlayerName(player.name)}
          </Typography>
        </Stack>
      </Stack>
    </Card>
  )
}

// Shared frame for one match so consecutive matches in a day read as distinct
// panels: a white surface lifted off the grey page with a hairline border + soft
// shadow, padded so the inner team cards sit inside a clear boundary.
const MATCH_CARD_SX = {
  width: "99%",
  maxWidth: 1600,
  borderRadius: 2,
  bgcolor: "background.paper",
  p: 1.5,
  mb: 2.5,
  boxShadow: 1,
} as const

// Compact, scannable match header shared by the FFA and team cards: the key
// facts (format, map, length) read on one line; date/version/id are demoted to a
// muted caption, with a small secondary action (download) at the top-right. The
// winner is intentionally omitted — each team card carries a "Won/Lost" band.
function MatchHeader(props: {
  match: MatchInfo
  formatLabel: string
  action?: React.ReactNode
}) {
  const { match } = props
  const mapName = match.map.split("/").slice(-1)[0]
  const date = match.timestamp.toLocaleString("en-US", {
    timeZoneName: "short",
  })
  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{
        justifyContent: "space-between",
        alignItems: "flex-start",
        width: "100%",
      }}
    >
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          flexWrap: "wrap",
          minWidth: 0,
        }}
      >
        <Chip label={props.formatLabel} size="small" variant="outlined" />
        <Typography
          variant="body2"
          sx={{
            fontWeight: 600,
          }}
        >
          {mapName}
        </Typography>
        {match.hasAi && (
          <Tooltip title="AI player present — ratings for this game are only minorly impacted">
            <SmartToyIcon fontSize="small" sx={{ color: "text.secondary" }} />
          </Tooltip>
        )}
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
          }}
        >
          {match.durationMinutes.toFixed(1)} min · {date} · v{match.gameVersion}{" "}
          · ID {match.id}
        </Typography>
      </Stack>
      {props.action}
    </Stack>
  )
}

// Small, secondary download action that lives in the header rather than as a
// full-width button below the match.
function DownloadReplayButton(props: { matchId: number }) {
  return (
    <Tooltip title="Download replay">
      <IconButton
        size="small"
        aria-label="Download replay"
        onClick={() => downloadReplay(props.matchId)}
      >
        <DownloadIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  )
}

// An accordion-style expander for the heavy match details: full-width row with a
// rotating chevron. The caller renders the details inside a <Collapse> with
// unmountOnExit so they aren't fetched until the row is first opened.
function DetailsExpander(props: { open: boolean; onToggle: () => void }) {
  return (
    <Button
      fullWidth
      onClick={props.onToggle}
      endIcon={
        <ExpandMoreIcon
          sx={{
            transform: props.open ? "rotate(180deg)" : "none",
            transition: "transform 0.2s",
          }}
        />
      }
      sx={{
        mt: 1,
        py: 0.75,
        justifyContent: "space-between",
        color: "text.secondary",
        borderTop: 1,
        borderColor: "divider",
        borderRadius: 0,
        "&:hover": { bgcolor: "action.hover" },
      }}
    >
      {props.open ? "Hide match details" : "Show match details"}
    </Button>
  )
}

function FfaMatchDisplay(props: { match: MatchInfo }) {
  const { match } = props
  const [details, setDetails] = React.useState<boolean>(false)
  const playerPositions = React.useMemo(
    () => buildPlayerPositions(match.players),
    [match.players],
  )
  return (
    <Paper variant="outlined" sx={MATCH_CARD_SX}>
      <MatchHeader
        match={match}
        formatLabel="FFA"
        action={<DownloadReplayButton matchId={match.id} />}
      />
      <Stack
        direction="row"
        sx={{
          flexWrap: "wrap",
          gap: 1,
          mt: 1,
        }}
      >
        {match.players.map((p) => (
          // Color is unique per player in a match; names aren't (twin CPUs).
          <FfaPlayerCard key={`${p.name}-${p.color}`} player={p} />
        ))}
        <GameMap mapname={match.map} playerPositions={playerPositions} />
      </Stack>
      <DetailsExpander open={details} onToggle={() => setDetails((v) => !v)} />
      <Collapse in={details} unmountOnExit>
        <LazyMatchDetails id={match.id} />
      </Collapse>
    </Paper>
  )
}

function downloadURI(uri: string, name: string) {
  const link = document.createElement("a")
  link.download = name
  link.href = uri
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function downloadReplay(matchId: number) {
  FilesClient.getMatchReplayUrlApiReplayUrlMatchIdGet({ matchId })
    .then((result) => {
      if (!result.url) return
      // The name is also signed into the presigned URL's Content-Disposition -
      // `download` alone is ignored on a cross-origin (S3) href.
      downloadURI(result.url, result.filename)
    })
    .catch(console.error)
}

export const DisplayMatchInfo = React.memo(function DisplayMatchInfo(props: {
  match: MatchInfo
  idx: number
}) {
  const [details, setDetails] = React.useState<boolean>(false)
  const playerPositions = React.useMemo(
    () => buildPlayerPositions(props.match.players),
    [props.match.players],
  )

  if (props.match.composition?.isFfa && !props.match.incomplete) {
    return <FfaMatchDisplay match={props.match} />
  }

  const header = (
    <MatchHeader
      match={props.match}
      formatLabel={props.match.composition?.category ?? "?"}
    />
  )

  // Group observers together regardless of the team they happen to carry:
  // historically they sit on team 0 and only re-parsed matches have -1, so
  // grouping on `team` alone splits them across cards (and labels the team-0
  // ones "Unknown Team").
  const teams = groupBy(props.match.players, (p) =>
    isObserver(p) ? "observers" : p.team,
  )

  const paperprops: Record<string, string | number> = { ...MATCH_CARD_SX }
  const incomplete = (props.match.incomplete ?? "").length !== 0
  const matchDisplay = (
    <Paper sx={paperprops} variant="outlined">
      <MatchHeader
        match={props.match}
        formatLabel={props.match.composition?.category ?? "?"}
        action={<DownloadReplayButton matchId={props.match.id} />}
      />
      {props.match?.notes?.length ? (
        <Typography
          sx={{
            color: "warning.main",
            fontWeight: "bold",
            mt: 0.5,
          }}
        >
          {props.match.notes}
        </Typography>
      ) : null}
      {incomplete ? (
        <Typography
          sx={{
            color: "error.main",
            fontWeight: "bold",
            mt: 0.5,
          }}
        >
          {props.match.incomplete}
        </Typography>
      ) : null}
      <Stack
        direction="row"
        sx={{
          justifyContent: "flex-start",
          flexWrap: { xs: "wrap", md: "nowrap" },
          mt: 1,
        }}
      >
        {Object.values(teams).map((team) => (
          <TeamCard
            key={team[0].team}
            players={team}
            won={team[0].team === props.match.winningTeam}
          />
        ))}
        <Box sx={{ flexShrink: 0 }}>
          <GameMap
            mapname={props.match.map}
            playerPositions={playerPositions}
          />
        </Box>
      </Stack>
      <DetailsExpander open={details} onToggle={() => setDetails((v) => !v)} />
      <Collapse in={details} unmountOnExit>
        <LazyMatchDetails id={props.match.id} />
      </Collapse>
    </Paper>
  )

  if (props.match.incomplete) {
    paperprops.bgcolor = "action.disabledBackground"
    paperprops.borderColor = "error.main"
    return (
      <Accordion defaultExpanded={false}>
        <AccordionSummary
          expandIcon={<ArrowDownwardIcon />}
          sx={{ bgcolor: "action.hover" }}
        >
          <Typography
            sx={{
              color: "error.main",
            }}
          >
            Mismatch:{" "}
          </Typography>
          {header}
        </AccordionSummary>
        <AccordionDetails>{matchDisplay}</AccordionDetails>
      </Accordion>
    )
  }
  return matchDisplay
})

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
              <DisplayMatchInfo match={m} key={m.id} idx={matchIdx} />
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
