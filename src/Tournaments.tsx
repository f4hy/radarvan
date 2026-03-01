import Table from "@mui/material/Table"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import Box from "@mui/material/Box"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import Button from "@mui/material/Button"
import Stack from "@mui/material/Stack"
import Loading from "./Loading"
import LinearProgress from "@mui/material/LinearProgress"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import { Chip, Tooltip as MuiTooltip, useTheme } from "@mui/material"
import useMediaQuery from "@mui/material/useMediaQuery"
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
import {
  Tournament,
  TournamentResult,
  MatchupResult,
  WinLoss,
  MatchInfo,
  TournamentReport,
} from "./api"
import { Client } from "./Client"
import { isDebug } from "./utils"
import { Typography } from "@mui/material"
import { DisplayMatchInfo } from "./Matches"

function getTournamentResults(callback: (m: TournamentResult[]) => void) {
  Client.getTournamentResultsApiTournamentResultsGet()
    .then(callback)
    .catch((e) => alert(e))
}

function getTournamentReport(
  name: string,
  callback: (m: TournamentReport) => void,
) {
  Client.getTournamentReportApiTournamentReportTournamentNameGet({
    tournamentName: name,
  })
    .then(callback)
    .catch((e) => alert(e))
}
function getMatch(matchId: number, callback: (m: MatchInfo) => void) {
  Client.getMatchByIdApiMatchMatchIdGet({ matchId: matchId })
    .then(callback)
    .catch((e) => alert(e))
}

const getWinRateStyle = (winRate: number) => {
  if (winRate >= 55) {
    return {
      color: "success.dark",
      fontWeight: 700,
      fontSize: "1.1em",
    }
  }
  if (winRate <= 45) {
    return {
      fontWeight: 500,
    }
  }
  return {
    fontWeight: 400,
  }
}

function teamAlias(players: string): string {
  switch (players) {
    case "OneThree111+Pancake":
      return "Pan31"
    case "CoreDawg+Neo":
      return "NeDog"
    case "EnragedFerret+Gorn":
      return "Gorret"
    case "Syn+WildCard":
      return "Syld"
    case "Modus+Tytan":
      return "MoTy"
    case "STM+Skip":
      return "SkiTM"
    default:
      return players
  }
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
      </Typography>
    )
  }
  return <></>
}

function ShowMatchesForMatchup(props: { matches: MatchInfo[] }) {
  if (props.matches.length === 0) {
    return (
      <Typography color="warning.main" style={{ fontWeight: "bold" }}>
        No recorded matches to show
      </Typography>
    )
  }
  return (
    <Stack>
      {props.matches.map((m) => (
        <DisplayMatchInfo key={m.id} match={m} idx={0} />
      ))}
    </Stack>
  )
}

function LoadAndShowMatch(props: { matchId: number }) {
  const [match, setMatch] = React.useState<MatchInfo | null>(null)
  React.useEffect(() => {
    getMatch(props.matchId, setMatch)
  }, [props.matchId])
  if (match === null || match.durationMinutes === undefined) {
    return (
      <>
        <Loading />
        <Typography>{JSON.stringify(match?.durationMinutes)}</Typography>
      </>
    )
  }
  return <DisplayMatchInfo match={match} idx={props.matchId} />
}

function DisplayMatchup(props: { matchup: MatchupResult }) {
  const gameDate =
    props.matchup.matches.find((m) => m.timestamp)?.timestamp?.toDateString() ??
    ""
  const header =
    Object.keys(props.matchup.outcome).join(" vs. ") + ` @ ${gameDate}`
  return (
    <Box>
      <Stack>
        <Typography>{header}</Typography>
        <DisplayOverrideBanner override={props.matchup.override} />
        <TableContainer component={Paper} sx={{ maxHeight: "50%" }}>
          <Table stickyHeader sx={{ maxHeight: "50%" }}>
            <TableHead>
              <TableRow>
                <TableCell style={{ width: "20%" }}>Team</TableCell>
                <TableCell>Wins</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {Object.entries(props.matchup.outcome).map(([team, wl]) => (
                <TableRow
                  key={team}
                  sx={{
                    "&:nth-of-type(odd)": {
                      backgroundColor: "action.hover", // Uses theme's hover color
                    },
                    "&:last-child td, &:last-child th": { border: 0 },
                  }}
                >
                  <TableCell>{team}</TableCell>
                  <TableCell>{wl.wins}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
        <ShowMatchesForMatchup matches={props.matchup.matches} />
      </Stack>
    </Box>
  )
}

function DisplayRecords(props: {
  records: { [key: string]: WinLoss }
  totalGames: number
  complete: boolean
}) {
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"))
  const total = props.totalGames
  const CustomTooltip = ({ active, payload }: any) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border-2 border-gray-300 rounded shadow-lg">
          <p className="font-bold text-sm mb-1">{data.team}</p>
          <p className="text-sm">Current Wins: {data.wins}</p>
          <p className="text-sm">Losses: {data.losses}</p>
          <p className="text-sm">
            Games Played: {data.wins + data.losses}/{total}
          </p>
          <p className="text-sm">Outstanding: {data.gamesOutstanding}</p>
          <p className="text-sm text-blue-600">
            Max Possible: {data.maxPossibleWins}
          </p>
        </div>
      )
    }
    return null
  }
  const chartData = Object.entries(props.records).map(([team, wl]) => ({
    team: teamAlias(team.split(",").join("+")),
    wins: wl.wins,
    losses: wl.losses,
    potentialWins: total - wl.losses - wl.wins,
    gamesOutstanding: total - (wl.wins + wl.losses),
    maxPossibleWins: total - wl.losses,
  }))
  return (
    <Stack>
      <Typography>Team Records</Typography>
      <TableContainer component={Paper} sx={{ maxHeight: "50%" }}>
        <Table stickyHeader sx={{ maxHeight: "50%", tableLayout: "fixed" }}>
          <TableHead>
            <TableRow>
              <TableCell style={{ width: "10%" }}>
                <Typography>Team</Typography>
              </TableCell>
              <TableCell style={{ width: "5%" }}>
                <Typography>W-L</Typography>
              </TableCell>
              <TableCell style={{ width: "5%" }}>
                <Typography>Win %</Typography>
              </TableCell>
              <TableCell>
                <Typography>Progress</Typography>
              </TableCell>
              <TableCell>
                <Typography>Max possible wins</Typography>
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {Object.entries(props.records).map(([team, wl]) => {
              const gamesPlayed = wl.wins + wl.losses
              const maxPossibleWins = total - wl.losses
              const winRate: number = gamesPlayed
                ? (wl.wins / gamesPlayed) * 100
                : 0
              const teamMembers = (
                <Typography> {team.split(",").join("+")} </Typography>
              )
              const teamName: string = teamAlias(team.split(",").join("+"))
              return (
                <TableRow key={team}>
                  <TableCell>
                    <MuiTooltip title={teamMembers} arrow>
                      <Chip label={teamName} color="primary" />
                    </MuiTooltip>{" "}
                  </TableCell>
                  <TableCell>
                    <Typography>
                      {wl.wins} - {wl.losses}
                    </Typography>
                  </TableCell>
                  <TableCell>
                    <Typography sx={getWinRateStyle(winRate)}>
                      {" "}
                      {winRate.toFixed(1)}%
                    </Typography>{" "}
                  </TableCell>
                  <TableCell>
                    <Stack>
                      <LinearProgress
                        color="info"
                        sx={{ height: 25, borderRadius: 5 }}
                        variant="determinate"
                        value={(100 * (wl.wins + wl.losses)) / total}
                        valueBuffer={(100 * (total - wl.losses)) / total}
                      />
                      <Typography>
                        {wl.wins + wl.losses} / {total} games played
                      </Typography>
                    </Stack>
                  </TableCell>
                  <TableCell>
                    {" "}
                    <Stack>
                      <LinearProgress
                        color={"success"}
                        sx={{ height: 25, borderRadius: 5 }}
                        variant="buffer"
                        value={(100 * wl.wins) / total}
                        valueBuffer={(100 * (total - wl.losses)) / total}
                      />
                      <Typography>
                        {wl.wins} wins with {maxPossibleWins} possible remaining
                      </Typography>
                    </Stack>
                  </TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </TableContainer>
      {props.complete || (
        <ResponsiveContainer width="100%" height={400}>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 30, left: isMobile ? 5 : 150, bottom: 5 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis type="number" domain={[0, total]} />
            <YAxis dataKey="team" type="category" width={isMobile ? 65 : 140} tick={{ fontSize: isMobile ? 10 : 14 }} />
            <Tooltip content={<CustomTooltip />} />
            <Legend />
            <Bar
              dataKey="wins"
              stackId="a"
              fill="#10b981"
              name="Current Wins"
            />
            <Bar
              dataKey="potentialWins"
              stackId="a"
              fill="#93c5fd"
              name="Potential Additional Wins"
            />
            <Bar dataKey="losses" stackId="a" fill="#f87171" name="Losses" />
          </BarChart>
        </ResponsiveContainer>
      )}
    </Stack>
  )
}

function DisplayMatchupsPlayed(props: { matchups: MatchupResult[] }) {
  const [selected, setSelected] = React.useState<number>(0)
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"))
  const buttonsPerRow: number = isMobile ? 2 : 5

  const buttonNumbers: number[] = Array.from(
    { length: props.matchups.length },
    (_, i) => i,
  )
  const rows: number[][] = []
  for (let i = 0; i < props.matchups.length; i += buttonsPerRow) {
    rows.push(buttonNumbers.slice(i, i + buttonsPerRow))
  }

  const handleChange = (
    event: React.MouseEvent<HTMLElement>,
    newValue: number | null,
  ) => {
    if (newValue !== null) {
      setSelected(newValue)
    }
  }

  return (
    <Stack>
      <Divider />
      <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
        {rows.map((row, rowIndex) => (
          <ToggleButtonGroup
            color="primary"
            key={rowIndex}
            value={selected}
            exclusive
            onChange={handleChange}
            size={isMobile ? "small" : "large"}
            sx={{ width: "100%" }}
          >
            {row.map((buttonIndex) => {
              const outcome = props.matchups[buttonIndex].outcome
              const teams = Object.keys(outcome).map((tn) =>
                teamAlias(tn.split(",").join("+")),
              )
              const first_record = Object.values(outcome)[0]
              const record = `${first_record.wins} - ${first_record.losses}`
              const disabled = Object.entries(outcome).find(
                ([tb, wl]) => wl.wins + wl.losses > 0,
              )
                ? false
                : true
              return (
                <ToggleButton
                  key={buttonIndex}
                  value={buttonIndex}
                  disabled={disabled}
                  sx={{
                    flex: 1, // Make buttons fill available space
                    textTransform: "none", // Prevent all-caps
                  }}
                >
                  <Typography style={{ fontWeight: "bold" }} variant={isMobile ? "caption" : "body1"}>
                    {teams.join(" vs ")} {record}
                  </Typography>
                </ToggleButton>
              )
            })}
          </ToggleButtonGroup>
        ))}
      </Box>
      <DisplayMatchup matchup={props.matchups[selected]} />
    </Stack>
  )
}

function DisplayTournamentStats(props: { result: TournamentResult }) {
  const [touramentStats, setTournamentStats] =
    React.useState<TournamentReport | null>(null)
  const [selectedMatch, setSelectedMatch] = React.useState<number | null>(null)
  const debug = isDebug()
  const show = props.result.complete === true || debug
  React.useEffect(() => {
    getTournamentReport(props.result.tournament.name, setTournamentStats)
  }, [props.result.tournament.name])

  if (!show) {
    return (
      <Paper>
        <Typography>Tournament still in progress</Typography>
      </Paper>
    )
  }
  if (touramentStats == null) {
    return <></>
  }
  function matchButton(mId: number | null | undefined) {
    if (mId === null || mId === undefined) {
      return <></>
    }
    return (
      <Button
        sx={{ minWidth: 200 }}
        variant="contained"
        onClick={() => setSelectedMatch(mId)}
      >
        {" "}
        {mId}{" "}
      </Button>
    )
  }

  return (
    <Paper>
      {selectedMatch && <LoadAndShowMatch matchId={selectedMatch} />}
      <TableContainer component={Paper} sx={{ maxHeight: "50%" }}>
        <Table stickyHeader sx={{ maxHeight: "50%" }}>
          <TableHead>
            <TableRow>
              <TableCell style={{ width: "20%" }}>Stat</TableCell>
              <TableCell>Value</TableCell>
              <TableCell>Player</TableCell>
              <TableCell>MatchId</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {touramentStats.stats.map((s) => {
              return (
                <TableRow
                  key={s.statName}
                  sx={{
                    "&:nth-of-type(odd)": {
                      backgroundColor: "action.hover", // Uses theme's hover color
                    },
                    "&:last-child td, &:last-child th": { border: 0 },
                  }}
                >
                  <TableCell>{s.statName}</TableCell>
                  <TableCell>{"" + s.value}</TableCell>
                  <TableCell>{s.player}</TableCell>
                  <TableCell>{matchButton(s.matchId)}</TableCell>
                </TableRow>
              )
            })}
          </TableBody>
        </Table>
      </TableContainer>
      <Divider />
    </Paper>
  )
}

function DisplayTournamentResult(props: { result: TournamentResult }) {
  return (
    <Stack>
      <DisplayTournamentInfo tournament={props.result.tournament} />
      <Divider />
      <DisplayRecords
        records={props.result.records}
        totalGames={props.result.tournament.totalGamesPlayedPerTeam}
        complete={props.result.complete}
      />
      <Divider sx={{ height: "100px" }} />
      <DisplayTournamentStats result={props.result} />
      <Typography sx={{ bgcolor: "lightblue" }}>Matchups</Typography>
      <DisplayMatchupsPlayed matchups={props.result.matchups} />
      <Divider />
    </Stack>
  )
}

export default function DisplayTournamentResults() {
  const [touramentResults, setTournamentResults] = React.useState<
    TournamentResult[]
  >([])
  React.useEffect(() => {
    getTournamentResults(setTournamentResults)
  }, [])
  if (touramentResults.length === 0) {
    return <Loading />
  }
  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000 }}>
      <Typography variant="h4">Tournament Results!</Typography>
      {/* <Button variant="contained" onClick={() => getGeneralStats(setGeneralStats)} >Get Matches</Button> */}
      {touramentResults.map((r) => (
        <DisplayTournamentResult key={r.tournament.name} result={r} />
      ))}
    </Paper>
  )
}
