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
import Page from "./Page"
import { queryFallback } from "./QueryState"
import LinearProgress from "@mui/material/LinearProgress"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import { Chip, Tooltip as MuiTooltip, useTheme } from "@mui/material"
import useMediaQuery from "@mui/material/useMediaQuery"
import { useQuery } from "@tanstack/react-query"
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
import type {
  Tournament,
  TournamentResult,
  MatchupResult,
  WinLoss,
  MatchInfo,
} from "./api"
import { Client } from "./Client"
import { useIsAdmin } from "./AuthContext"
import { WIN_COLOR, WIN_COLOR_SOFT, LOSS_COLOR } from "./theme"
import { Typography } from "@mui/material"
import { DisplayMatchInfo } from "./Matches"

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
      <Typography
        sx={{
          color: "warning.main",
          fontWeight: "bold",
        }}
      >
        {props.override}
      </Typography>
    )
  }
  return <></>
}

function ShowMatchesForMatchup(props: { matches: MatchInfo[] }) {
  if (props.matches.length === 0) {
    return (
      <Typography
        sx={{
          color: "warning.main",
          fontWeight: "bold",
        }}
      >
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
  // Shares the ["match", id] key with Records, so a match opened on either page
  // is already in cache on the other.
  const query = useQuery({
    queryKey: ["match", props.matchId],
    queryFn: () =>
      Client.getMatchByIdApiMatchMatchIdGet({ matchId: props.matchId }),
  })
  const fallback = queryFallback(query, `match #${props.matchId}`)
  if (fallback) return fallback
  const match = query.data as MatchInfo
  // A match with no duration hasn't finished parsing; keep waiting rather than
  // rendering a half-built card.
  if (match.durationMinutes === undefined) return <Loading />
  return <DisplayMatchInfo match={match} idx={props.matchId} />
}

function DisplayMatchup(props: { matchup: MatchupResult }) {
  const gameDate =
    props.matchup.matches.find((m) => m.timestamp)?.timestamp?.toDateString() ??
    ""
  const header = `${Object.keys(props.matchup.outcome).join(" vs. ")} @ ${gameDate}`
  return (
    <Box>
      <Stack>
        <Typography>{header}</Typography>
        <DisplayOverrideBanner override={props.matchup.override} />
        <TableContainer component={Paper} sx={{ maxHeight: "50%" }}>
          <Table stickyHeader sx={{ maxHeight: "50%" }}>
            <TableHead>
              <TableRow>
                <TableCell sx={{ width: "20%" }}>Team</TableCell>
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

function TeamRecordsTable(props: {
  records: { [key: string]: WinLoss }
  total: number
}) {
  return (
    <TableContainer component={Paper} sx={{ maxHeight: "50%" }}>
      <Table stickyHeader sx={{ maxHeight: "50%", tableLayout: "fixed" }}>
        <TableHead>
          <TableRow>
            <TableCell sx={{ width: "10%" }}>
              <Typography>Team</Typography>
            </TableCell>
            <TableCell sx={{ width: "5%" }}>
              <Typography>W-L</Typography>
            </TableCell>
            <TableCell sx={{ width: "5%" }}>
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
            const maxPossibleWins = props.total - wl.losses
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
                      value={(100 * (wl.wins + wl.losses)) / props.total}
                      valueBuffer={
                        (100 * (props.total - wl.losses)) / props.total
                      }
                    />
                    <Typography>
                      {wl.wins + wl.losses} / {props.total} games played
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
                      value={(100 * wl.wins) / props.total}
                      valueBuffer={
                        (100 * (props.total - wl.losses)) / props.total
                      }
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
  )
}

function TeamProgressChart(props: {
  chartData: {
    team: string
    wins: number
    losses: number
    potentialWins: number
    gamesOutstanding: number
    maxPossibleWins: number
  }[]
  total: number
  isMobile: boolean
}) {
  const CustomTooltip = ({
    active,
    payload,
  }: {
    active?: boolean
    payload?: Array<{
      payload: {
        team: string
        wins: number
        losses: number
        gamesOutstanding: number
        maxPossibleWins: number
      }
    }>
  }) => {
    if (active && payload?.length) {
      const data = payload[0].payload
      return (
        <Paper elevation={3} sx={{ p: 1.5, lineHeight: 1.5 }}>
          <Typography
            variant="body2"
            sx={{
              fontWeight: 700,
              mb: 0.5,
            }}
          >
            {data.team}
          </Typography>
          <Typography variant="body2">Current Wins: {data.wins}</Typography>
          <Typography variant="body2">Losses: {data.losses}</Typography>
          <Typography variant="body2">
            Games Played: {data.wins + data.losses}/{props.total}
          </Typography>
          <Typography variant="body2">
            Outstanding: {data.gamesOutstanding}
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: "primary.main",
            }}
          >
            Max Possible: {data.maxPossibleWins}
          </Typography>
        </Paper>
      )
    }
    return null
  }
  return (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart
        data={props.chartData}
        layout="vertical"
        margin={{
          top: 5,
          right: 30,
          left: props.isMobile ? 5 : 150,
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis type="number" domain={[0, props.total]} />
        <YAxis
          dataKey="team"
          type="category"
          width={props.isMobile ? 65 : 140}
          tick={{ fontSize: props.isMobile ? 10 : 14 }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Legend />
        <Bar dataKey="wins" stackId="a" fill={WIN_COLOR} name="Current Wins" />
        <Bar
          dataKey="potentialWins"
          stackId="a"
          fill={WIN_COLOR_SOFT}
          name="Potential Additional Wins"
        />
        <Bar dataKey="losses" stackId="a" fill={LOSS_COLOR} name="Losses" />
      </BarChart>
    </ResponsiveContainer>
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
  const chartData = React.useMemo(
    () =>
      Object.entries(props.records).map(([team, wl]) => ({
        team: teamAlias(team.split(",").join("+")),
        wins: wl.wins,
        losses: wl.losses,
        potentialWins: total - wl.losses - wl.wins,
        gamesOutstanding: total - (wl.wins + wl.losses),
        maxPossibleWins: total - wl.losses,
      })),
    [props.records, total],
  )
  return (
    <Stack>
      <Typography>Team Records</Typography>
      <TeamRecordsTable records={props.records} total={total} />
      {props.complete || (
        <TeamProgressChart
          chartData={chartData}
          total={total}
          isMobile={isMobile}
        />
      )}
    </Stack>
  )
}

function MatchupButtonGrid(props: {
  matchups: MatchupResult[]
  selected: number
  onChange: (value: number) => void
  isMobile: boolean
}) {
  const buttonsPerRow: number = props.isMobile ? 2 : 5
  const rows = React.useMemo(() => {
    const buttonNumbers = Array.from(
      { length: props.matchups.length },
      (_, i) => i,
    )
    const result: number[][] = []
    for (let i = 0; i < props.matchups.length; i += buttonsPerRow) {
      result.push(buttonNumbers.slice(i, i + buttonsPerRow))
    }
    return result
  }, [props.matchups.length, buttonsPerRow])
  const handleChange = React.useCallback(
    (_event: React.MouseEvent<HTMLElement>, newValue: number | null) => {
      if (newValue !== null) {
        props.onChange(newValue)
      }
    },
    [props.onChange],
  )
  return (
    <Box sx={{ display: "flex", flexDirection: "column", gap: 1 }}>
      {rows.map((row, rowIndex) => (
        <ToggleButtonGroup
          color="primary"
          // biome-ignore lint/suspicious/noArrayIndexKey: rows are fixed-size chunks of one option list; the row index is the chunk's identity.
          key={rowIndex}
          value={props.selected}
          exclusive
          onChange={handleChange}
          size={props.isMobile ? "small" : "large"}
          sx={{ width: "100%" }}
        >
          {row.map((buttonIndex) => {
            const outcome = props.matchups[buttonIndex].outcome
            const teams = Object.keys(outcome).map((tn) =>
              teamAlias(tn.split(",").join("+")),
            )
            const first_record = Object.values(outcome)[0]
            const record = `${first_record.wins} - ${first_record.losses}`
            const disabled = !Object.entries(outcome).some(
              ([_tb, wl]) => wl.wins + wl.losses > 0,
            )
            return (
              <ToggleButton
                key={buttonIndex}
                value={buttonIndex}
                disabled={disabled}
                sx={{
                  flex: 1,
                  textTransform: "none",
                }}
              >
                <Typography
                  sx={{ fontWeight: "bold" }}
                  variant={props.isMobile ? "caption" : "body1"}
                >
                  {teams.join(" vs ")} {record}
                </Typography>
              </ToggleButton>
            )
          })}
        </ToggleButtonGroup>
      ))}
    </Box>
  )
}

function DisplayMatchupsPlayed(props: { matchups: MatchupResult[] }) {
  const [selected, setSelected] = React.useState<number>(0)
  const theme = useTheme()
  const isMobile = useMediaQuery(theme.breakpoints.down("sm"))

  return (
    <Stack>
      <Divider />
      <MatchupButtonGrid
        matchups={props.matchups}
        selected={selected}
        onChange={setSelected}
        isMobile={isMobile}
      />
      <DisplayMatchup matchup={props.matchups[selected]} />
    </Stack>
  )
}

function DisplayTournamentStats(props: { result: TournamentResult }) {
  const [selectedMatch, setSelectedMatch] = React.useState<number | null>(null)
  const debug = useIsAdmin()
  const show = props.result.complete === true || debug
  const reportQuery = useQuery({
    queryKey: ["tournamentReport", props.result.tournament.name],
    queryFn: () =>
      Client.getTournamentReportApiTournamentReportTournamentNameGet({
        tournamentName: props.result.tournament.name,
      }),
    // An in-progress tournament has no report to show, so don't ask for one.
    enabled: show,
  })
  const touramentStats = reportQuery.data ?? null

  if (!show) {
    return (
      <Paper>
        <Typography>Tournament still in progress</Typography>
      </Paper>
    )
  }
  const reportFallback = queryFallback(reportQuery, "this tournament's report")
  if (reportFallback) return reportFallback
  if (touramentStats == null) return null
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
              <TableCell sx={{ width: "20%" }}>Stat</TableCell>
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
                  <TableCell>{`${s.value}`}</TableCell>
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
      <Typography sx={{ bgcolor: "lightblue" }}>Matchups</Typography>
      <DisplayMatchupsPlayed matchups={props.result.matchups} />
      <Divider />
      <DisplayTournamentStats result={props.result} />
      <Divider />
    </Stack>
  )
}

export default function DisplayTournamentResults() {
  const query = useQuery({
    queryKey: ["tournamentResults"],
    queryFn: () => Client.getTournamentResultsApiTournamentResultsGet(),
  })
  const fallback = queryFallback(query, "tournaments")
  if (fallback) return fallback
  const touramentResults = query.data as TournamentResult[]
  return (
    <Page
      title="Tournaments"
      description="Every tournament we have run, with its standings and the games that decided them."
    >
      {touramentResults.map((r) => (
        <DisplayTournamentResult key={r.tournament.name} result={r} />
      ))}
    </Page>
  )
}
