import Box from "@mui/material/Box"
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import DownloadIcon from "@mui/icons-material/Download"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import ErrorIcon from "@mui/icons-material/Error"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import Card from "@mui/material/Card"
import Loading, { MatchesLoading, MatchRowLoading } from "./Loading"
import Grid from "@mui/material/Grid"
import Stack from "@mui/material/Stack"
import Divider from "@mui/material/Divider"
import ListItem from "@mui/material/ListItem"
import ListItemText from "@mui/material/ListItemText"
import Paper from "@mui/material/Paper"
import Typography from "@mui/material/Typography"

import _ from "lodash"
import * as React from "react"
import DisplayGeneral from "./Generals"
import GameMap, { type PlayerPosition } from "./Map"
import { toGeneralName } from "./general_utils"
import ShowMatchDetails from "./ShowMatchDetails"
import { Client } from "./Client"
import {
  MatchInfo,
  Matches,
  Player,
  PlayerRatingDailyChange,
  Team,
} from "./api"
import QuestionMarkIcon from "@mui/icons-material/QuestionMark"
import { Tooltip } from "@mui/material"
import VisibilityIcon from "@mui/icons-material/Visibility"
import { ActivityCalendar } from "react-activity-calendar"
import { getColorHex } from "./utils"
import { useIsAdmin } from "./AuthContext"
import { useErrorSnackbar } from "./useErrorSnackbar"

function getDates(
  callback: (m: { [key: string]: number }) => void,
  onError = console.error,
) {
  Client.getDatesApiDatesGet().then(callback).catch(onError)
}

function getMatches(
  date: Date,
  callback: (m: Matches) => void,
  excludeDev: boolean,
  onError = console.error,
) {
  // Hide dev-build matches (is_dev) for non-admins.
  Client.getMatchesByDateApiMatchesByDateDateGet({
    date: date,
    excludeDev: excludeDev,
  })
    .then(callback)
    .catch(onError)
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
      .filter((p) => p.startingPosition != null)
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

function winRateColor(w: number, l: number): string {
  const rate = w + l === 0 ? 0.5 : w / (w + l)
  // interpolate muted red (rate=0) → muted green (rate=1)
  const r = Math.round(200 - 118 * rate)
  const g = Math.round(90 + 86 * rate)
  const b = Math.round(90 + 37 * rate)
  return `rgb(${r},${g},${b})`
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
        color: "#fff",
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
  const team = props.players[0]?.team
  let label = `${props.won ? "Won" : "Lost"} · Team ${team}`
  let icon = props.won ? <EmojiEventsIcon /> : <ErrorIcon />
  let bandColor = props.won ? WON_BAND : LOST_BAND
  if (team === Team.NUMBER_0) {
    label = "Unknown Team"
    icon = <QuestionMarkIcon />
    bandColor = NEUTRAL_BAND
  }
  if (team === Team.NUMBER_MINUS_1) {
    label = "Observers"
    icon = <VisibilityIcon />
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
            key={p.name + "-" + p.general}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              px: 1.5,
              py: 1,
            }}
          >
            <DisplayGeneral general={p.general} />
            <Typography
              variant="h6"
              fontWeight={700}
              noWrap
              sx={{ color: getColorHex(p.color) }}
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
      <Stack spacing={1} alignItems="center" sx={{ p: 1.5 }}>
        <DisplayGeneral general={player.general} />
        <Typography
          variant="subtitle1"
          fontWeight={700}
          noWrap
          sx={{ color: getColorHex(player.color) }}
        >
          {normalizePlayerName(player.name)}
        </Typography>
      </Stack>
    </Card>
  )
}

function FfaMatchDisplay(props: { match: MatchInfo }) {
  const { match } = props
  const [details, setDetails] = React.useState<boolean>(false)
  const playerPositions = React.useMemo(
    () => buildPlayerPositions(match.players),
    [match.players],
  )
  // Timestamps are stored UTC; render in the viewer's local zone with the zone
  // abbreviation (users span US Eastern/Mountain/Pacific) so the time is unambiguous.
  const date = match.timestamp.toLocaleString("en-US", {
    timeZoneName: "short",
  })
  const header = (
    <Box>
      <Typography variant="body2" fontWeight="bold">
        FFA · {date}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Map: {match.map.split("/").slice(-1)} ·{" "}
        {match.durationMinutes.toFixed(1)}min · v{match.gameVersion} · ID:
        {match.id}
      </Typography>
    </Box>
  )
  return (
    <Box sx={{ width: "99%", maxWidth: 1600, mb: 2 }}>
      <ListItem>
        <ListItemText primary={header} />
      </ListItem>
      <Stack direction="row" flexWrap="wrap" gap={1} sx={{ p: 1 }}>
        {match.players.map((p) => (
          <FfaPlayerCard key={p.name} player={p} />
        ))}
        <GameMap mapname={match.map} playerPositions={playerPositions} />
      </Stack>
      <Stack direction="row">
        <Button variant="contained" onClick={() => setDetails(!details)}>
          Match Details
        </Button>
        <Tooltip title={match.filename}>
          <Button
            variant="contained"
            onClick={() => downloadReplay(match.id, match.filename)}
            endIcon={<DownloadIcon />}
          >
            Download Replay
          </Button>
        </Tooltip>
      </Stack>
      {details ? <ShowMatchDetails id={match.id} /> : null}
    </Box>
  )
}

function downloadURI(uri: string, name: string) {
  var link = document.createElement("a")
  link.download = name
  link.href = uri
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function downloadReplay(matchId: number, fallbackUrl: string) {
  Client.getMatchReplayUrlApiReplayUrlMatchIdGet({ matchId })
    .then((result) => {
      const presigned = result["url"]
      if (!presigned) return
      const filename = fallbackUrl.split("/").pop() || `${matchId}.rep`
      downloadURI(presigned, filename)
    })
    .catch(console.error)
}

function displayTeam(team: Team): string {
  switch (team) {
    case Team.NUMBER_0:
      return "No Team"
    case Team.NUMBER_1:
      return "Team 1"
    case Team.NUMBER_2:
      return "Team 2"
    case Team.NUMBER_3:
      return "Team 3"
    case Team.NUMBER_4:
      return "Team 4"
    default:
      return "Unknown Team"
  }
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

  const date = props.match.timestamp.toLocaleString("en-US", {
    timeZoneName: "short",
  })
  const winningTeam = displayTeam(props.match.winningTeam)
  let header = (
    <Box>
      <Typography variant="body2" fontWeight="bold">
        {props.match.composition?.category} · Winner: {winningTeam} · {date}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        Map: {props.match.map.split("/").slice(-1)} ·{" "}
        {props.match.durationMinutes.toFixed(1)}min · v{props.match.gameVersion}{" "}
        · ID:{props.match.id}
      </Typography>
    </Box>
  )

  const teams = _.groupBy(props.match.players, "team")

  const paperprops: Record<string, string | number> = {
    width: "99%",
    maxWidth: 1600,
    borderRadius: 3,
    bgcolor: "transparent",
    border: "none",
    mb: 2,
  }
  const incomplete = (props.match.incomplete ?? "").length !== 0
  const matchDisplay = (
    <Paper sx={paperprops} variant="outlined">
      <ListItem key="match">
        <ListItemText key="match-text" primary={header} />
        {props.match?.notes?.length ? (
          <Typography color="warning.main" style={{ fontWeight: "bold" }}>
            {props.match.notes}
          </Typography>
        ) : null}
        {incomplete ? (
          <Typography color="error.main" style={{ fontWeight: "bold" }}>
            {props.match.incomplete}
          </Typography>
        ) : null}
      </ListItem>
      <Stack
        direction="row"
        justifyContent="flex-start"
        flexWrap={{ xs: "wrap", md: "nowrap" }}
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
      <Stack direction="row">
        <Button variant="contained" onClick={() => setDetails(!details)}>
          Match Details
        </Button>
        <Tooltip title={props.match.filename}>
          <Button
            variant="contained"
            onClick={() => downloadReplay(props.match.id, props.match.filename)}
            endIcon={<DownloadIcon />}
          >
            Download Replay
          </Button>
        </Tooltip>
      </Stack>
      {details ? <ShowMatchDetails id={props.match.id} /> : null}
    </Paper>
  )

  if (props.match.incomplete) {
    paperprops["bgcolor"] = "text.disabled"
    paperprops["borderColor"] = "red"
    return (
      <Accordion defaultExpanded={false}>
        <AccordionSummary
          expandIcon={<ArrowDownwardIcon />}
          sx={{ bgcolor: "text.disabled" }}
        >
          <Typography color="error.main">Mismatch: </Typography>
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
  const date = new Date(props.date)
  date.setDate(date.getDate() + 2)
  const categoryChips =
    props.matches.length > 0
      ? Object.entries(
          _.groupBy(props.matches, (m) =>
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
      for (const p of m.players) {
        if (p.team === Team.NUMBER_MINUS_1) continue
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
        sx={{ borderColor: winRateColor(w, l), borderWidth: 2 }}
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
      <Stack direction="row" spacing={2} alignItems="center" flexWrap="wrap">
        <Typography fontWeight="bold">
          {date.toLocaleString("en-US", {
            weekday: "short",
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
          })}
        </Typography>
        <Typography color="text.secondary">
          {props.count} {props.count === 1 ? "game" : "games"}
        </Typography>
        {categoryChips.length > 0 && (
          <Stack direction="row" spacing={1} flexWrap="wrap">
            {categoryChips}
          </Stack>
        )}
      </Stack>
      {(wlChips.length > 0 || ratingItems.length > 0) && (
        <Stack
          direction="row"
          spacing={1}
          flexWrap="wrap"
          sx={{ mt: 0.5, display: { xs: "none", sm: "flex" } }}
        >
          {wlChips}
          {ratingItems}
        </Stack>
      )}
    </Stack>
  )
}

function DisplayMatchesForDate(props: {
  date: Date
  count: number
  idx: number
  selected: boolean
}) {
  const [expanded, setExpanded] = React.useState<boolean>(props.idx === 0)
  const [matchList, setMatchList] = React.useState<Matches>(empty)
  const [ratingChanges, setRatingChanges] = React.useState<
    PlayerRatingDailyChange[]
  >([])
  const { showError, errorSnackbar } = useErrorSnackbar()
  const isAdmin = useIsAdmin()
  React.useEffect(() => {
    if (expanded && matchList.matches.length === 0) {
      getMatches(props.date, setMatchList, !isAdmin, showError)
      Client.getPlayerRatingDailyChangesApiPlayerRatingsDailyChangesGet({
        forDate: props.date,
      })
        .then(setRatingChanges)
        .catch(showError)
    }
  }, [expanded, matchList.matches.length, props.date, showError, isAdmin])

  const handleChange = React.useCallback(
    (_event: React.SyntheticEvent, isExpanded: boolean) => {
      setExpanded(isExpanded)
    },
    [],
  )
  const fmt = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
  const date = fmt(props.date)
  const borderProps = props.selected ? { border: "3px solid green" } : {}
  return (
    <>
      <Accordion
        expanded={expanded === true}
        onChange={handleChange}
        sx={borderProps}
      >
        <AccordionSummary expandIcon={<ArrowDownwardIcon />}>
          <MatchDateSummary
            date={date}
            count={props.count}
            matches={matchList.matches}
            ratingChanges={ratingChanges}
          />
        </AccordionSummary>
        <AccordionDetails sx={{ bgcolor: "background.default" }}>
          {matchList.matches.length === 0 ? (
            <MatchRowLoading />
          ) : (
            matchList.matches.map((m, matchIdx) => (
              <DisplayMatchInfo match={m} key={m.id} idx={matchIdx} />
            ))
          )}
        </AccordionDetails>
      </Accordion>
      {errorSnackbar}
    </>
  )
}

function groupByYear(
  dateCounts: Record<string, number>,
): Record<string, Record<string, number>> {
  const years: Record<string, Record<string, number>> = {}
  for (const [date, count] of Object.entries(dateCounts)) {
    const year = date.slice(0, 4)
    if (!years[year]) years[year] = {}
    years[year][date] = count
  }
  return years
}

function getEndDate(date: Date): Date {
  const now = new Date()
  if (date.getFullYear() === now.getFullYear()) {
    return now
  }
  return new Date(date.getFullYear(), 11, 31)
}

function toActivityData(dateCounts: Record<string, number>) {
  const dates = Object.keys(dateCounts).sort()
  if (dates.length === 0) return []
  const first = dates[0]
  const yearStart = new Date(`${first.slice(0, 4)}-01-01`)
  const end = getEndDate(new Date(dates[dates.length - 1]))
  const maxCount = Math.max(...Object.values(dateCounts))

  const data = []
  for (let d = new Date(yearStart); d <= end; d.setDate(d.getDate() + 1)) {
    const dateStr = d.toISOString().split("T")[0]
    const count = dateCounts[dateStr] ?? 0
    const level =
      count === 0 ? 0 : (Math.ceil((count / maxCount) * 4) as 0 | 1 | 2 | 3 | 4)
    data.push({ date: dateStr, count, level })
  }

  return data
}

function MatchActivityCalendar(props: {
  dataByYear: Record<string, Record<string, number>>
  dates: Record<string, number>
  itemRefs: React.MutableRefObject<(HTMLDivElement | null)[]>
  onDateClick: (date: string) => void
}) {
  const activityDataByYear = React.useMemo(
    () =>
      Object.fromEntries(
        Object.entries(props.dataByYear).map(([year, yearData]) => [
          year,
          toActivityData(yearData),
        ]),
      ),
    [props.dataByYear],
  )

  const renderBlock = React.useCallback(
    (block: React.ReactElement, activity: { date: string }) => (
      <g
        onClick={() => {
          const i = Object.keys(props.dates).indexOf(activity.date)
          props.itemRefs.current[i]?.scrollIntoView({
            behavior: "smooth",
            block: "start",
          })
          props.onDateClick(activity.date)
        }}
        style={{ cursor: "pointer" }}
      >
        {block}
      </g>
    ),
    [props.dates, props.itemRefs, props.onDateClick],
  )

  return (
    <Grid container sx={{ width: "80%", margin: "0" }}>
      {Object.entries(props.dataByYear).map(([year, yearData], idx) => (
        <Grid key={year} size={6}>
          <Box sx={{ overflowX: "auto", p: 2 }}>
            <Typography>{year}</Typography>
            {Object.keys(yearData).length > 0 ? (
              <ActivityCalendar
                data={activityDataByYear[year]}
                weekStart={1}
                showWeekdayLabels={["wed", "sat"]}
                blockSize={10}
                blockMargin={4}
                showColorLegend={idx === 0}
                labels={{
                  totalCount: "{{count}} team games in {{year}}",
                }}
                colorScheme="light"
                theme={{
                  light: [
                    "#ebedf0",
                    "#9be9a8",
                    "#40c463",
                    "#30a14e",
                    "#216e39",
                  ],
                }}
                tooltips={{
                  activity: {
                    text: (activity) =>
                      `  ${activity.count} team games on ${activity.date}`,
                    placement: "bottom",
                    offset: 6,
                    hoverRestMs: 10,
                    transitionStyles: {
                      duration: 50,
                      common: { fontFamily: "monospace" },
                    },
                    withArrow: true,
                  },
                }}
                renderBlock={renderBlock}
              />
            ) : (
              <Loading />
            )}
          </Box>
        </Grid>
      ))}
    </Grid>
  )
}

export default function DisplayMatches() {
  const [dates, setDates] = React.useState<{ [key: string]: number }>({})
  const [selectedDate, setSelectedDate] = React.useState<string | null>(null)
  const itemRefs = React.useRef<(HTMLDivElement | null)[]>([])
  const { showError, errorSnackbar } = useErrorSnackbar()
  React.useEffect(() => {
    getDates(setDates, showError)
  }, [showError])
  if (Object.keys(dates).length === 0) {
    return <MatchesLoading />
  }
  const dataByYear = groupByYear(dates)

  return (
    <Stack>
      <Accordion slotProps={{ transition: { unmountOnExit: true } }}>
        <AccordionSummary
          expandIcon={<ArrowDownwardIcon />}
          sx={{ bgcolor: "action.hover" }}
        >
          <Typography fontWeight={600} color="text.secondary">
            Activity Calendar (click to expand)
          </Typography>
        </AccordionSummary>
        <AccordionDetails>
          <MatchActivityCalendar
            dataByYear={dataByYear}
            dates={dates}
            itemRefs={itemRefs}
            onDateClick={setSelectedDate}
          />
        </AccordionDetails>
      </Accordion>
      {Object.entries(dates).map(([date, count], idx) => (
        <div
          key={idx}
          ref={(el) => {
            itemRefs.current[idx] = el
          }}
        >
          <DisplayMatchesForDate
            date={new Date(date)}
            count={count}
            idx={idx}
            selected={date === selectedDate}
          />
        </div>
      ))}
      {errorSnackbar}
    </Stack>
  )
}
