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
  Legend,
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
const getWinRateStyle = (winRate: number) => {
  if (winRate >= 55) {
    return {
      color: "success.dark",
      fontWeight: 700,
      fontSize: "1.1em"
    };
  }
  if (winRate <= 45) {
    return {
      fontWeight: 500
    };
  }
  return {
    fontWeight: 400
  };
};

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
        sx={{
          bgcolor: "background.paper",
          borderLeft: 3,
          borderColor: "primary.main",
          '&:hover': {
            bgcolor: "action.hover"
          },
          '& .MuiAccordionSummary-content': {
            fontWeight: 500,
            color: "primary.main"
          }
        }}
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
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      return (
        <div className="bg-white p-3 border-2 border-gray-300 rounded shadow-lg">
          <p className="font-bold text-sm mb-1">{data.team}</p>
          <p className="text-sm">Current Wins: {data.wins}</p>
          <p className="text-sm">Losses: {data.losses}</p>
          <p className="text-sm">Games Played: {data.wins + data.losses}/{total}</p>
          <p className="text-sm">Outstanding: {data.gamesOutstanding}</p>
          <p className="text-sm text-blue-600">Max Possible: {data.maxPossibleWins}</p>
        </div>
      );
    }
    return null;
  }
  const chartData = Object.entries(props.records).map(([team, wl]) =>
  ({
    team: team.split(",").join("+"),
    wins: wl.wins,
    losses: wl.losses,
    potentialWins: total - wl.losses - wl.wins,
    gamesOutstanding: total - (wl.wins + wl.losses),
    maxPossibleWins: total - (wl.losses)
  }))
  return (
    <Stack>
      <Typography>Team Records</Typography>
      <TableContainer component={Paper} sx={{ maxHeight: "50%" }}>
        <Table stickyHeader sx={{ maxHeight: "50%", tableLayout: 'fixed' }}>
          <TableHead>
            <TableRow>
              <TableCell style={{ width: '20%' }}><Typography>Team</Typography></TableCell>
              <TableCell style={{ width: '5%' }}><Typography>W-L</Typography></TableCell>
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
                  const winRate: number = gamesPlayed ? ((wl.wins / gamesPlayed) * 100) : 0
                  return (
                    <TableRow>
                      <TableCell>{team.split(",").join("+")}</TableCell>
                      <TableCell><Typography>{wl.wins} - {wl.losses}</Typography></TableCell>
                      <TableCell><Typography sx={getWinRateStyle(winRate)} > {winRate.toFixed(1)}%</Typography> </TableCell>
                      <TableCell>
                        <Stack>
                          <LinearProgress color="info" sx={{ height: 25, borderRadius: 5 }} variant="determinate" value={100 * ((wl.wins + wl.losses)) / total} valueBuffer={100 * (total - (wl.losses)) / total} /><Typography>{wl.wins + wl.losses} / {total} games played</Typography>
                        </Stack>
                      </TableCell>
                      <TableCell>                       <Stack>
                        <LinearProgress color={"success"} sx={{ height: 25, borderRadius: 5 }} variant="buffer" value={100 * ((wl.wins)) / total} valueBuffer={100 * (total - (wl.losses)) / total} /><Typography>{wl.wins} wins with {maxPossibleWins} possible remaining</Typography>
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
      <ResponsiveContainer width="100%" height={400}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 5, right: 30, left: 150, bottom: 5 }}
        >
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis type="number" domain={[0, total]} />
          <YAxis dataKey="team" type="category" width={140} />
          <Tooltip content={<CustomTooltip />} />
          <Legend />
          <Bar dataKey="wins" stackId="a" fill="#10b981" name="Current Wins" />
          <Bar dataKey="potentialWins" stackId="a" fill="#93c5fd" name="Potential Additional Wins" />
          <Bar dataKey="losses" stackId="a" fill="#f87171" name="Losses" />
        </BarChart>
      </ResponsiveContainer>
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
