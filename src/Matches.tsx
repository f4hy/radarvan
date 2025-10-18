import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import DownloadIcon from "@mui/icons-material/Download"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import ThumbDownIcon from "@mui/icons-material/ThumbDown"
import ErrorIcon from '@mui/icons-material/Error';
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Button from "@mui/material/Button"
import Card from "@mui/material/Card"
import CardHeader from "@mui/material/CardHeader"
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
import { MatchInfoInput, Matches, Player, Team } from "./api"
import QuestionMarkIcon from '@mui/icons-material/QuestionMark';
import { Tooltip } from "@mui/material";

function getMatches(count: number, callback: (m: Matches) => void) {
  Client.getMatchesApiMatchesMatchCountGet({ matchCount: count })
    .then(callback)
    .catch((e) => alert(e))
}

function MatchCard(props: {
  avatar: React.ReactNode
  title: React.ReactNode
  color: string
}) {
  return (
    <Card sx={{ backgroundColor: props.color }}>
      <CardHeader
        sx={{ m: { md: 1, xs: 0 } }}
        title={props.title}
        avatar={props.avatar}
        component="div"
      />
    </Card>
  )
}

function playerNameStyle(player: Player) {
  return { WebkitTextStroke: `0.5px grey` }
}

function TeamCard(props: { players: Player[]; won: boolean }) {
  const color = props.won ? "#c5e1a5" : "#e57373"
  const team = (props.players[0]?.team)
  let title = (props.won ? "Won" : "Lost") + " Team:" + (props.players[0]?.team)
  let icon = props.won ? <EmojiEventsIcon /> : <ErrorIcon />
  if (team === Team.NUMBER_0 || team === Team.NUMBER_MINUS_1) {
    title = "Unkown Team"
    icon = <QuestionMarkIcon />
  }
  return (
    <Card sx={{ backgroundColor: color, minWidth: 300, width: 1 / 2 }} >
      <CardHeader title={title} avatar={icon} component="div" />
      {props.players.map((p) => (
        <CardContent component="div">
          <Stack direction="row" divider={<Divider flexItem />} spacing={4}>
            <DisplayGeneral
              general={p!.general}
              key={p?.name + "-" + p.general + "-general"}
            />{" "}
            <Typography variant="h5" color={p.color} fontWeight="fontWeightBold" sx={playerNameStyle(p)}>{p.name}</Typography>
          </Stack>
        </CardContent>
      ))}
    </Card>
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

function DisplayMatchInfo(props: { match: MatchInfoInput; idx: number }) {
  const [details, setDetails] = React.useState<boolean>(false)
  const date = props.match.timestamp.toLocaleString();
  const winningTeam = displayTeam(props.match.winningTeam)
  let header = (
    <Typography>
      {" MatchId:" +
        props.match.id +
        ` Winner:${winningTeam}` +
        " Date:" +
        date +
        " on Map:" +
        props.match.map.split("/").slice(-1) +
        " Duration:" +
        props.match.durationMinutes.toFixed(2) +
        " minutes"}
    </Typography>)

  const teams = _.groupBy(props.match.players, "team")

  const paperprops: any = { width: "99%", maxWidth: 1600, borderRadius: "20px" }
  if (props.match.incomplete) {
    paperprops["bgcolor"] = "text.disabled"
    paperprops["borderColor"] = "red"
  }
  return (
    <Paper sx={paperprops} variant="outlined">
      <ListItem key="match">
        <ListItemText key="match-text" primary={header} />
        {props.match.notes.length ? (
          <Typography color="warning.main" style={{ fontWeight: "bold" }}>
            {props.match.notes}
          </Typography>
        ) : null}
        {props.match.incomplete.length ? (
          <Typography color="error.main" style={{ fontWeight: "bold" }}>
            {props.match.incomplete}
          </Typography>
        ) : null}
      </ListItem>
      <Stack
        direction="row"
        justifyContent="flex-start"
      >
        {
          Object.values(teams).map((team) => (
            <TeamCard players={team} won={team[0].team === props.match.winningTeam} />
          ))}
        <Map mapname={props.match.map} />
      </Stack>
      <Stack direction="row">
        <Button variant="contained" onClick={() => setDetails(!details)}>
          Match Details
        </Button>
        <Tooltip title={props.match.filename}>
          <Button
            variant="contained"
            onClick={() =>
              downloadReplay(props.match.filename)
            }
            endIcon={<DownloadIcon />}
          >
            Download Replay
          </Button>
        </Tooltip>
      </Stack>
      {details ? <ShowMatchDetails id={props.match.id} /> : null}
    </Paper >
  )
}

const empty = { matches: [] }

function subtractHours(d: Date, hoursToSubtract: number): Date {
  const shifted = new Date(d)
  shifted.setHours(d.getHours() - hoursToSubtract)
  return shifted
}

export default function DisplayMatches() {
  const [getAll, setGetAll] = React.useState<boolean>(false)
  const [matchList, setMatchList] = React.useState<Matches>(empty)
  const partialCount = 50
  const maxCount = 2000
  React.useEffect(() => {
    getMatches(getAll ? maxCount : partialCount, setMatchList)
  }, [getAll])
  const showAll = () => {
    setGetAll(true)
  }
  const byDate = _.groupBy(matchList.matches, (m) => subtractHours(m.timestamp, 4).toLocaleDateString()
  )
  return (
    <>
      {Object.entries(byDate).map(([date, group], idx) => (
        <Accordion defaultExpanded={idx === 0}>
          <AccordionSummary expandIcon={<ArrowDownwardIcon />}>
            <Typography>{date + ": " + group.length + " Matches"} </Typography>
          </AccordionSummary>
          <AccordionDetails>
            {group.map((m, idx) => (
              <DisplayMatchInfo match={m} key={m.id} idx={idx} />
            ))}
          </AccordionDetails>
        </Accordion>
      ))}
      {getAll ? null : <Button onClick={() => showAll()}>Show All</Button>}
    </>
  )
}
