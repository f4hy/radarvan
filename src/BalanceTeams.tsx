import { Chip, Typography } from "@mui/material"
import Alert from "@mui/material/Alert"
import Box from "@mui/material/Box"
import Checkbox from "@mui/material/Checkbox"
import Divider from "@mui/material/Divider"
import FormControlLabel from "@mui/material/FormControlLabel"
import FormGroup from "@mui/material/FormGroup"
import Grid from "@mui/material/Grid"
import LinearProgress from "@mui/material/LinearProgress"
import Loading from "./Loading"
import Link from "@mui/material/Link"
import Paper from "@mui/material/Paper"
import Radio from "@mui/material/Radio"
import RadioGroup from "@mui/material/RadioGroup"
import Stack from "@mui/material/Stack"
import Tab from "@mui/material/Tab"
import Tabs from "@mui/material/Tabs"
import * as React from "react"
import { PlayerEnum, PlayerEnumFromJSON } from "./api"
import { Client } from "./Client"
import { isDebug } from "./utils"
import { useErrorSnackbar } from "./useErrorSnackbar"

interface TeamWinRating {
  [key: string]: number
}

function getTeamWinRating(
  players: PlayerEnum[],
  callback: (m: TeamWinRating) => void,
  onError = console.error,
) {
  if (players.length < 2) {
    callback({})
    return
  }
  Client.balanceTeamsApiBalanceTeamsGet({ players: players })
    .then(callback)
    .catch(onError)
}

function getTeamPartition(
  players: PlayerEnum[],
  teamSize: number,
  callback: (m: string[][]) => void,
  onError = console.error,
) {
  if (
    players.length < 6 ||
    players.length % 2 !== 0 ||
    players.length % teamSize !== 0
  ) {
    callback([])
    return
  }
  Client.partitionTeamsApiPartitionTeamsTeamSizeGet({
    teamSize: teamSize,
    players: players,
  })
    .then((result) =>
      callback(
        result.map((team) => team.filter((p): p is string => p !== null)),
      ),
    )
    .catch(onError)
}

const getScoreStyle = (score: number) => {
  if (score >= 90) {
    return "success"
  }
  if (score >= 60) {
    return "info"
  }
  return "warning"
}

export function ScoreBar(props: {
  team: string
  score: number
  selectedPlayers: string[]
}) {
  const team1 = props.team.split(",")
  const team2 = props.selectedPlayers.filter((p) => !team1.includes(p))

  return (
    <Paper elevation={1} sx={{ padding: 1.5 }}>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 0.5,
          mb: 1,
        }}
      >
        {team1.map((p) => (
          <Chip key={p} label={p} color="primary" size="small" />
        ))}
        <Typography variant="body2" sx={{ mx: 0.5 }}>
          vs
        </Typography>
        {team2.map((p) => (
          <Chip key={p} label={p} color="secondary" size="small" />
        ))}
      </Box>
      <Box sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <LinearProgress
          sx={{ flex: 1, height: 10, borderRadius: 5 }}
          color={getScoreStyle(props.score)}
          variant="determinate"
          value={props.score}
        />
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ whiteSpace: "nowrap" }}
        >
          {`${Math.round(props.score)}% Balanced`}
        </Typography>
      </Box>
    </Paper>
  )
}

function BalanceTeams(props: { selectedPlayers: PlayerEnum[] }) {
  const [teamRating, setTeamRating] = React.useState<TeamWinRating>({})
  const [loading, setLoading] = React.useState(false)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    if (props.selectedPlayers.length >= 2) {
      setLoading(true)
      getTeamWinRating(
        props.selectedPlayers,
        (data) => {
          setTeamRating(data)
          setLoading(false)
        },
        showError,
      )
    } else {
      setTeamRating({})
    }
  }, [props.selectedPlayers, showError])

  const filtered = React.useMemo(() => {
    const entries = Object.entries(teamRating)
    const threshold = Math.min(
      0.7,
      Math.max(
        ...entries.map(([, winRate]) => 1.0 - Math.abs(winRate - 0.5) * 2),
      ),
    )
    return isDebug()
      ? entries
      : entries.filter(
          ([, winRate]) => 1.0 - Math.abs(winRate - 0.5) * 2 >= threshold,
        )
  }, [teamRating])

  if (props.selectedPlayers.length % 2 !== 0) {
    return (
      <Alert severity="warning">
        Not an even number of selected players. Try adding a HardArmy
      </Alert>
    )
  }
  if (loading && Object.keys(teamRating).length === 0) {
    return <Loading />
  }
  return (
    <Stack
      spacing={1}
      sx={{ mt: 1, p: 1.5, bgcolor: "action.hover", borderRadius: 1 }}
    >
      {loading && <LinearProgress />}
      {filtered.map(([team, winRate]) => (
        <ScoreBar
          key={team}
          team={team}
          score={(1.0 - Math.abs(winRate - 0.5) * 2.0) * 100}
          selectedPlayers={props.selectedPlayers}
        />
      ))}
      {errorSnackbar}
    </Stack>
  )
}

function PartitionTeams(props: { selectedPlayers: PlayerEnum[] }) {
  const [teamPartition, setTeamPartition] = React.useState<string[][]>([])
  const [teamSize, setTeamSize] = React.useState<number>(2)
  const [loading, setLoading] = React.useState(false)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    const eligible =
      props.selectedPlayers.length >= 6 &&
      props.selectedPlayers.length % 2 === 0 &&
      props.selectedPlayers.length % teamSize === 0
    if (eligible) {
      setLoading(true)
      getTeamPartition(
        props.selectedPlayers,
        teamSize,
        (data) => {
          setTeamPartition(data)
          setLoading(false)
        },
        showError,
      )
    } else {
      setTeamPartition([])
    }
  }, [props.selectedPlayers, teamSize, showError])

  if (props.selectedPlayers.length % 2 !== 0) {
    return (
      <Alert severity="warning">Not an even number of selected players</Alert>
    )
  }
  if (loading && teamPartition.length === 0) {
    return <Loading />
  }
  if (!loading && teamPartition.length === 0) {
    return (
      <Alert severity="warning">
        Need to select at least 6 players for a tournament
      </Alert>
    )
  }
  const colors = [
    "#FFB3BA",
    "#FFDFBA",
    "#FFFFBA",
    "#BAFFC9",
    "#BAE1FF",
    "#E8BAFF",
  ]
  const handleChange = (
    event: React.ChangeEvent<HTMLInputElement>,
    value: string,
  ) => {
    setTeamSize(parseInt(value))
  }
  return (
    <Stack>
      {loading && <LinearProgress />}
      <RadioGroup
        row
        value={teamSize}
        onChange={handleChange}
        name="row-radio-buttons-group"
      >
        <FormControlLabel value={2} control={<Radio />} label="Teams of 2" />
        <FormControlLabel value={3} control={<Radio />} label="Teams of 3" />
        <FormControlLabel value={4} control={<Radio />} label="Teams of 4" />
      </RadioGroup>
      <Grid container spacing={2}>
        {teamPartition.map((team, i) => (
          <Grid key={i}>
            <Paper sx={{ padding: 2, background: colors[i] }}>
              {team.map((t) => (
                <Chip key={t} label={t} color="primary" sx={{ padding: 2 }} />
              ))}
              <Divider />
            </Paper>
          </Grid>
        ))}
      </Grid>
      {errorSnackbar}
    </Stack>
  )
}

function PlayerSelector(props: {
  players: PlayerEnum[]
  selectedPlayers: PlayerEnum[]
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void
}) {
  return (
    <FormGroup>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          padding: 1,
        }}
      >
        {props.players.map((option) => (
          <FormControlLabel
            key={option}
            control={
              <Checkbox
                checked={props.selectedPlayers.includes(option)}
                onChange={props.onChange}
                value={option}
              />
            }
            label={option}
          />
        ))}
      </Box>
    </FormGroup>
  )
}

export default function DisplayBalanceTeams() {
  const [selectedPlayers, setSelectedPlayers] = React.useState<PlayerEnum[]>([])
  const [selectedTab, setSelectedTab] = React.useState<string>("balanceTeams")

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value, checked } = event.target
    const player = PlayerEnumFromJSON(value)
    setSelectedPlayers((prevSelected) => {
      if (checked) {
        return [...prevSelected, player]
      } else {
        return prevSelected.filter((item) => item !== value)
      }
    })
  }
  const players = Object.values(PlayerEnum).sort()

  const handleTabChange = (event: React.SyntheticEvent, newValue: string) => {
    setSelectedTab(newValue)
    if (newValue === "partitionTeams" && selectedPlayers.length < 6) {
      const allPlayers = players.filter((p) => p !== "HardArmy")
      setSelectedPlayers(allPlayers)
    }
  }

  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000 }}>
      <Typography variant="h4">Determine Balanced Teams</Typography>
      <Typography>
        Select at least 4 players and the balance of each team combination will
        be ranked
      </Typography>
      <PlayerSelector
        players={players}
        selectedPlayers={selectedPlayers}
        onChange={handleChange}
      />
      <Tabs
        sx={{ width: "100%" }}
        value={selectedTab}
        onChange={handleTabChange}
      >
        <Tab
          sx={{ width: "50%", whiteSpace: "normal", lineHeight: 1.3, py: 1 }}
          value="balanceTeams"
          label="Balance players into two teams"
        />
        <Tab
          sx={{ width: "50%", whiteSpace: "normal", lineHeight: 1.3, py: 1 }}
          value="partitionTeams"
          label="Create teams for tournament"
        />
      </Tabs>
      {selectedTab === "balanceTeams" && (
        <BalanceTeams selectedPlayers={selectedPlayers} />
      )}
      {selectedTab === "partitionTeams" && (
        <PartitionTeams selectedPlayers={selectedPlayers} />
      )}
      <Divider sx={{ height: 40 }} />
      <Typography>
        Results are computed using all recorded 2v2 3v3 4v4 games and the{" "}
        <Link href="https://jmlr.org/papers/volume12/weng11a/weng11a.pdf">
          Bayesian Plackett-Luce model by Weng and Lin
        </Link>{" "}
        which is an extension of the "TrueSkill" algorithm used by xbox-live.
      </Typography>
    </Paper>
  )
}
