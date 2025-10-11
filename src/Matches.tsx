import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import DownloadIcon from "@mui/icons-material/Download"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import ThumbDownIcon from "@mui/icons-material/ThumbDown"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Button from "@mui/material/Button"
import Card from "@mui/material/Card"
import CardHeader from "@mui/material/CardHeader"
import Grid from "@mui/material/Grid"
import ListItem from "@mui/material/ListItem"
import ListItemText from "@mui/material/ListItemText"
import Paper from "@mui/material/Paper"
import Typography from "@mui/material/Typography"
import _ from "lodash"
import * as React from "react"
import DisplayGeneral from "./Generals"
import Map from "./Map"
import { Matches, MatchInfo } from "./proto/match"
import ShowMatchDetails from "./ShowMatchDetails"

function getMatches(count: number, callback: (m: Matches) => void) {
  fetch("/api/matches/" + count).then((r) =>
    r
      .blob()
      .then((b) => b.arrayBuffer())
      .then((j) => {
        const a = new Uint8Array(j)
        const matches = Matches.decode(a)
        matches.matches.sort(
          (m1, m2) =>
            (m2.timestamp?.getTime() ?? 0) - (m1.timestamp?.getTime() ?? 0)
        )
        callback(matches)
      })
  )
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

function downloadURI(uri: string, name: string) {
  var link = document.createElement("a")
  link.download = name
  link.href = uri
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function downloadReplay(filename: string) {
  fetch("/api/getRepaly/" + filename).then((r) =>
    r.text().then((url) => downloadURI(url, filename))
  )
}

function DisplayMatchInfo(props: { match: MatchInfo; idx: number }) {
  const [details, setDetails] = React.useState<boolean>(false)

  const date: string = props.match.timestamp
    ? props.match.timestamp.toDateString()
    : "unknown"
  let header =
    " MatchId:" +
    props.match.id +
    " Date:" +
    date +
    " on Map:'" +
    props.match.map.split("/").slice(-1) +
    "'  Winner:Team" +
    props.match.winningTeam +
    " Duration " +
    props.match.durationMinutes.toFixed(2) +
    " minutes"
  const winners = _.sortBy(
    props.match.players.filter((p) => p.team === props.match.winningTeam),
    ["team", "name"]
  )
  const losers = _.sortBy(
    props.match.players.filter((p) => p.team !== props.match.winningTeam),
    ["team", "name"]
  )
  if (losers.length === 0) {
    return <div>Loading {props.idx}</div>
  }

  const losingTeam = losers[0].team
  const paperprops: any = { width: "99%", maxWidth: 1600, borderRadius: "20px" }
  if (props.match.incomplete) {
    paperprops["bgcolor"] = "text.disabled"
    paperprops["borderColor"] = "red"
  }
  const showTeam = props.match.winningTeam !== 0 ? "block" : "none"
  const showTeamSpacing = props.match.winningTeam !== 0 ? 4 : 6
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
      <Grid container spacing={{ sx: 0, md: 1, width: "99%" }}>
        <Grid item xs={12} md={10}>
          <Grid container spacing={{ sx: 0, md: 1 }} sx={{ width: "99%" }}>
            <Grid item xs={4} sx={{ display: { xs: "none", md: showTeam } }}>
              <MatchCard
                title={
                  <Typography variant="h5">
                    {"Team:" + props.match.winningTeam}
                  </Typography>
                }
                avatar={<EmojiEventsIcon />}
                color="#c5e1a5"
              />
            </Grid>
            {winners.map((p) => (
              <Grid item xs={6} md={showTeamSpacing}>
                <MatchCard
                  key={p.name + "-" + p.general + "-generalcard"}
                  title={
                    <Typography variant="h5">{`${p.name.padEnd(
                      50,
                      " "
                    )}`}</Typography>
                  }
                  avatar={
                    <DisplayGeneral
                      general={p.general}
                      key={p.name + "-" + p.general + "-general"}
                    />
                  }
                  color="#c5e1a5"
                />
              </Grid>
            ))}
            <Grid
              item
              xs={6}
              md={4}
              sx={{ display: { xs: "none", md: showTeam } }}
            >
              <MatchCard
                title={
                  <Typography variant="h5">{"Team:" + losingTeam}</Typography>
                }
                avatar={<ThumbDownIcon />}
                color="#e57373"
              />
            </Grid>
            {losers.map((p) => (
              <Grid item xs={6} md={showTeamSpacing}>
                <MatchCard
                  title={
                    <Typography variant="h5">{`${p.name.padEnd(
                      50,
                      " "
                    )}`}</Typography>
                  }
                  avatar={
                    <DisplayGeneral
                      general={p.general}
                      key={p.name + "-" + p.general + "-general"}
                    />
                  }
                  color="#e57373"
                />
              </Grid>
            ))}
            <Grid item xs={6} md={6}>
              <Button variant="contained" onClick={() => setDetails(!details)}>
                Match Details
              </Button>
            </Grid>
            <Grid item xs={6} md={6}>
              <Button
                variant="contained"
                onClick={() =>
                  downloadReplay(props.match.filename.replace(".json", ".rep"))
                }
                endIcon={<DownloadIcon />}
              >
                Download Replay
              </Button>
            </Grid>
          </Grid>
        </Grid>
        <Grid item xs={12} md={2}>
          <Map mapname={props.match.map} />
        </Grid>
      </Grid>
      {details ? <ShowMatchDetails id={props.match.id} /> : null}
    </Paper>
  )
}

const empty = { matches: [] }

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
  const byDate = _.groupBy(matchList.matches, (m) =>
    m.timestamp?.toDateString()
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
