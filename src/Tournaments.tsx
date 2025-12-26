import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Table from '@mui/material/Table';
import Link from '@mui/material/Link';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TablePagination from '@mui/material/TablePagination';
import TableRow from '@mui/material/TableRow';
import Stack from "@mui/material/Stack"
import Skeleton from "@mui/material/Skeleton"
import LinearProgress from "@mui/material/LinearProgress"
import Box from "@mui/material/Box"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import Grid from "@mui/material/Grid"
import * as React from "react"
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import DisplayGeneral from "./Generals"
import { General, GeneralStatOutput, GeneralStats, Tournament, TournamentResultOutput, MatchupResultOutput, WinLoss, MatchInfoOutput } from "./api"
import { Client } from "./Client"
import { toGeneralName } from "./general_utils"
import { Typography } from "@mui/material"
import { DisplayMatchInfo } from './Matches';

function getTournamentResults(callback: (m: TournamentResultOutput[]) => void) {
  Client.getTournamentResultsApiTournamentResultsGet()
    .then(callback)
    .catch((e) => alert(e))
}


function Loading() {
  return (
    <Stack>
      <LinearProgress />
      <Stack direction="row">
        <Skeleton variant="rectangular" height={150} />
        <Skeleton variant="rectangular" height={150} />
      </Stack>
    </Stack>
  )
}

function DisplayTournamentInfo(props: { tournament: Tournament }) {
  return (
    <Stack>
      <Typography>{props.tournament.name}</Typography>
    </Stack>
  )
}
function DisplayOverrideBanner(props: { override: string | undefined | null }) {
  if (props.override) {
    return (
      <Typography color="warning.main" style={{ fontWeight: "bold" }}>
        {props.override}
      </Typography>)
  }
  return (<></>)
}

function ShowMatchesForMatchup(props: { matches: MatchInfoOutput[] }) {
  if (props.matches.length == 0) {
    return (<Typography color="warning.main" style={{ fontWeight: "bold" }}>
      No recorded matches to show
    </Typography>)
  }
  return (
    <Accordion defaultExpanded={false}>
      <AccordionSummary
        expandIcon={<ArrowDownwardIcon />}
        sx={{ bgcolor: "green" }}
      >
        See matches from this matchup
      </AccordionSummary>
      <AccordionDetails>
        {props.matches.map(
          m =>
          (
            <DisplayMatchInfo match={m} idx={0} />
          )
        )
        }
      </AccordionDetails>
    </Accordion>
  )
}

function DisplayMatchup(props: { matchup: MatchupResultOutput }) {
  const header = Object.keys(props.matchup.outcome).join(" vs. ")
  return (
    <Box>
      <Stack >
        <Typography>Matchup {header}</Typography>
        <DisplayOverrideBanner override={props.matchup.override} />
        <TableContainer component={Paper} sx={{ maxHeight: "50%" }} >
          <Table stickyHeader sx={{ maxHeight: "50%" }} >
            <TableHead>
              <TableRow>
                <TableCell style={{ width: '20%' }}>Team</TableCell>
                <TableCell>Wins</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {
                Object.entries(props.matchup.outcome).map(
                  ([team, wl]) => (
                    <TableRow>
                      <TableCell>{team}</TableCell>
                      <TableCell>{wl.wins}</TableCell>
                    </TableRow>
                  )
                )}
            </TableBody>
          </Table>
        </TableContainer    >
        <ShowMatchesForMatchup matches={props.matchup.matches} />
      </Stack>
    </Box>
  )
}

function DisplayRecords(props: { records: ({ [key: string]: WinLoss; }), totalGames: number }) {
  const total = props.totalGames
  return (
    <Stack>
      <Typography>Team Records</Typography>
      <TableContainer component={Paper} sx={{ maxHeight: "50%" }}>
        <Table stickyHeader sx={{ maxHeight: "50%", tableLayout: 'fixed' }}>
          <TableHead>
            <TableRow>
              <TableCell  style={{ width: '20%' }}><Typography>Team</Typography></TableCell>
              <TableCell style={{ width: '5%' }}><Typography>Wins</Typography></TableCell>
              <TableCell style={{ width: '5%' }}><Typography>Losses</Typography></TableCell>
              <TableCell style={{ width: '5%' }}><Typography>Win %</Typography></TableCell>
              <TableCell><Typography>Progress</Typography></TableCell>
              <TableCell><Typography>Max possible wins</Typography></TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {
              Object.entries(props.records).map(
            ([team, wl]) => {
						const gamesPlayed = wl.wins + wl.losses
						const maxPossibleWins = total - (wl.losses)
						const winRate = gamesPlayed ? ((wl.wins / gamesPlayed)*100).toFixed(1) : 0
            return (
                    <TableRow>
                      <TableCell>{team}</TableCell>
                      <TableCell>{wl.wins}</TableCell>
                      <TableCell>{wl.losses}</TableCell>
                      <TableCell>{winRate}%</TableCell>
                      <TableCell>
												<Stack>
													<LinearProgress color="info" sx={{ height: 25, borderRadius: 5 }} variant="determinate" value={100 * ((wl.wins + wl.losses)) / total} valueBuffer={100 * (total - (wl.losses)) / total} /><Typography>{wl.wins + wl.losses} / {total} games played</Typography>
												</Stack>
												</TableCell>
                      <TableCell>												<Stack>
													<LinearProgress color={"success"} sx={{ height: 25, borderRadius: 5 }} variant="buffer" value={100 * ((wl.wins )) / total} valueBuffer={100 * (total - (wl.losses)) / total} /><Typography>{wl.wins} wins with {maxPossibleWins} possible remaining</Typography>
												</Stack>
</TableCell>
                    </TableRow>
                  )
                }
              )
            }
          </TableBody>
        </Table>
      </TableContainer    >
      {}
    </Stack>
  )
}

function DisplayTournamentResult(props: { result: TournamentResultOutput }) {
  return (
    <Stack>
      <DisplayTournamentInfo tournament={props.result.tournament} />
      <Divider />
      <DisplayRecords records={props.result.records} totalGames={props.result.tournament.totalGamesPlayedPerTeam} />
      <Divider sx={{ height: '200px' }} />
      {props.result.matchups.map(m => (<DisplayMatchup matchup={m} />))}
    </Stack>
  )
}


export default function DisplayTournamentResults() {
  const [touramentResults, setTournamentResults] = React.useState<TournamentResultOutput[]>([])
  React.useEffect(() => {
    getTournamentResults(setTournamentResults)
  }, [])
  if (touramentResults.length === 0) {
    return (<Loading />)
  }
  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000 }}>
      <Typography variant="h4">Tournament Results!</Typography>
      {/* <Button variant="contained" onClick={() => getGeneralStats(setGeneralStats)} >Get Matches</Button> */}
      {touramentResults.map(r => (<DisplayTournamentResult result={r} />))}
    </Paper>
  )
}
