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
import CardHeader from "@mui/material/CardHeader"
import Loading, { MatchesLoading, MatchRowLoading } from "./Loading"
import CardContent from "@mui/material/CardContent"
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
import Map from "./Map"
import ShowMatchDetails from "./ShowMatchDetails"
import { Client } from "./Client"
import { MatchInfo, Matches, Player, Team } from "./api"
import QuestionMarkIcon from "@mui/icons-material/QuestionMark"
import { Tooltip } from "@mui/material"
import VisibilityIcon from "@mui/icons-material/Visibility"
import { ActivityCalendar } from "react-activity-calendar"
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
  onError = console.error,
) {
  Client.getMatchesByDateApiMatchesByDateDateGet({ date: date })
    .then(callback)
    .catch(onError)
}

function playerNameStyle(player: Player) {
  return { WebkitTextStroke: `0.5px grey` }
}

function TeamCard(props: { players: Player[]; won: boolean }) {
  let color = props.won ? "#c5e1a5" : "#e57373"
  const team = props.players[0]?.team
  let title = (props.won ? "Won" : "Lost") + " Team:" + props.players[0]?.team
  let icon = props.won ? <EmojiEventsIcon /> : <ErrorIcon />
  if (team === Team.NUMBER_0) {
    title = "Unkown Team"
    icon = <QuestionMarkIcon />
  }
  if (team === Team.NUMBER_MINUS_1) {
    title = "Observer"
    icon = <VisibilityIcon />
    color = "#D3D3D3"
  }
  return (
    <Card
      sx={{
        backgroundColor: color,
        width: { xs: "100%", sm: "50%", md: "auto" },
        flex: { md: 1 },
        minWidth: 0,
      }}
    >
      <CardHeader title={title} avatar={icon} component="div" />
      {props.players.map((p) => (
        <CardContent key={p?.name + "-" + p.general} component="div">
          <Stack direction="row" divider={<Divider flexItem />} spacing={4}>
            <DisplayGeneral general={p!.general} />{" "}
            <Typography
              variant="h5"
              color={p.color}
              fontWeight="fontWeightBold"
              sx={playerNameStyle(p)}
            >
              {p.name}
            </Typography>
          </Stack>
        </CardContent>
      ))}
    </Card>
  )
}

function FfaPlayerCard(props: { player: Player }) {
  const { player } = props
  const bgColor = player.won ? "#c5e1a5" : "#eeeeee"
  return (
    <Card sx={{ backgroundColor: bgColor, minWidth: 160 }}>
      <CardContent component="div">
        <Stack spacing={1} alignItems="center">
          {player.won ? (
            <EmojiEventsIcon color="success" />
          ) : (
            <ErrorIcon color="disabled" />
          )}
          <DisplayGeneral general={player.general} />
          <Typography
            variant="h6"
            color={player.color}
            fontWeight="fontWeightBold"
            sx={playerNameStyle(player)}
          >
            {player.name}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  )
}

function FfaMatchDisplay(props: { match: MatchInfo }) {
  const { match } = props
  const [details, setDetails] = React.useState<boolean>(false)
  const date = match.timestamp.toLocaleString("en-US", {
    timeZone: "America/New_York",
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
    <Paper
      sx={{ width: "99%", maxWidth: 1600, borderRadius: "20px" }}
      variant="outlined"
    >
      <ListItem>
        <ListItemText primary={header} />
      </ListItem>
      <Stack direction="row" flexWrap="wrap" gap={1} sx={{ p: 1 }}>
        {match.players.map((p) => (
          <FfaPlayerCard key={p.name} player={p} />
        ))}
        <Map mapname={match.map} />
      </Stack>
      <Stack direction="row">
        <Button variant="contained" onClick={() => setDetails(!details)}>
          Match Details
        </Button>
        <Tooltip title={match.filename}>
          <Button
            variant="contained"
            onClick={() => downloadReplay(match.filename)}
            endIcon={<DownloadIcon />}
          >
            Download Replay
          </Button>
        </Tooltip>
      </Stack>
      {details ? <ShowMatchDetails id={match.id} /> : null}
    </Paper>
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

function downloadReplay(url: string) {
  const filename = url.split("/").pop()
  if (filename) {
    downloadURI(url, filename)
  }
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

export function DisplayMatchInfo(props: { match: MatchInfo; idx: number }) {
  const [details, setDetails] = React.useState<boolean>(false)

  if (props.match.composition?.isFfa && !props.match.incomplete) {
    return <FfaMatchDisplay match={props.match} />
  }

  const date = props.match.timestamp.toLocaleString("en-US", {
    timeZone: "America/New_York",
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

  const paperprops: any = { width: "99%", maxWidth: 1600, borderRadius: "20px" }
  const incomplete = (props.match.incomplete ?? "").length === 0
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
          <Map mapname={props.match.map} />
        </Box>
      </Stack>
      <Stack direction="row">
        <Button variant="contained" onClick={() => setDetails(!details)}>
          Match Details
        </Button>
        <Tooltip title={props.match.filename}>
          <Button
            variant="contained"
            onClick={() => downloadReplay(props.match.filename)}
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
}

const empty = { matches: [] }

function DisplayMatchesForDate(props: {
  date: Date
  count: number
  idx: number
  selected: boolean
}) {
  const [expanded, setExpanded] = React.useState<boolean>(props.idx === 0)
  const [matchList, setMatchList] = React.useState<Matches>(empty)
  const { showError, errorSnackbar } = useErrorSnackbar()
  React.useEffect(() => {
    if (expanded && matchList.matches.length === 0) {
      getMatches(props.date, setMatchList, showError)
    }
  }, [expanded, matchList.matches.length, props.date, showError])

  const handleChange =
    (panel: string) => (event: React.SyntheticEvent, isExpanded: boolean) => {
      if (matchList.matches.length === 0) {
        getMatches(props.date, setMatchList, showError)
      }
      setExpanded(isExpanded)
    }
  const fmt = (d: Date) =>
    `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`
  const date = fmt(props.date)
  const idx = props.idx
  const borderProps = props.selected ? { border: "3px solid green" } : {}
  return (
    <>
      <Accordion
        expanded={expanded === true}
        onChange={handleChange(`${idx}`)}
        sx={borderProps}
      >
        <AccordionSummary expandIcon={<ArrowDownwardIcon />}>
          <Stack
            direction="row"
            spacing={2}
            alignItems="center"
            sx={{ flexGrow: 1, flexWrap: "wrap" }}
          >
            <Typography fontWeight="bold">{date}</Typography>
            <Typography color="text.secondary">
              {props.count} {props.count === 1 ? "game" : "games"}
            </Typography>
            {matchList.matches.length > 0 && (
              <>
                {Object.entries(
                  _.groupBy(matchList.matches, (m) =>
                    m.composition?.isFfa
                      ? "FFA"
                      : (m.composition?.category ?? "?"),
                  ),
                ).map(([cat, ms]) => (
                  <Chip
                    key={cat}
                    label={`${ms.length}× ${cat}`}
                    size="small"
                    variant="outlined"
                  />
                ))}
                <Typography variant="body2" color="text.secondary">
                  {_.uniq(
                    matchList.matches.flatMap((m) =>
                      m.players
                        .filter((p) => p.team !== Team.NUMBER_MINUS_1)
                        .map((p) => p.name),
                    ),
                  ).join(" · ")}
                </Typography>
              </>
            )}
          </Stack>
        </AccordionSummary>
        <AccordionDetails>
          <AccordionDetails>
            {matchList.matches.length === 0 ? (
              <MatchRowLoading />
            ) : (
              matchList.matches.map((m, idx) => (
                <DisplayMatchInfo match={m} key={m.id} idx={idx} />
              ))
            )}
          </AccordionDetails>
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
      <Grid container sx={{ width: "80%", margin: "0" }}>
        {Object.entries(dataByYear).map(([year, yearData], idx) => (
          <Grid key={year} xs={6}>
            <Box sx={{ overflowX: "auto", p: 2 }}>
              <Typography>{year}</Typography>
              {Object.keys(yearData).length > 0 ? (
                <ActivityCalendar
                  data={toActivityData(yearData)}
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
                  renderBlock={(block, activity) => (
                    <g
                      onClick={() => {
                        const i = Object.keys(dates).findIndex(
                          (d) => d === activity.date,
                        )
                        itemRefs.current[i]?.scrollIntoView({
                          behavior: "smooth",
                          block: "start",
                        })
                        setSelectedDate(activity.date)
                      }}
                      style={{ cursor: "pointer" }}
                    >
                      {block}
                    </g>
                  )}
                />
              ) : (
                <Loading />
              )}
            </Box>
          </Grid>
        ))}
      </Grid>
      {Object.entries(dates).map(([date, count], idx) => (
        <div key={idx} ref={(el) => (itemRefs.current[idx] = el)}>
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
