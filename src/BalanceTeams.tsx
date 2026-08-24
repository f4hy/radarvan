import { Typography } from "@mui/material"
import Alert from "@mui/material/Alert"
import Box from "@mui/material/Box"
import Checkbox from "@mui/material/Checkbox"
import Divider from "@mui/material/Divider"
import FormControlLabel from "@mui/material/FormControlLabel"
import FormGroup from "@mui/material/FormGroup"
import Grid from "@mui/material/Grid"
import LinearProgress from "@mui/material/LinearProgress"
import Loading from "./Loading"
import Page from "./Page"
import { PlayerChip } from "./PlayerChip"
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
import { useIsAdmin } from "./AuthContext"
import { CHART_PALETTE } from "./theme"
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

const SIDE_SX = {
  display: "flex",
  gap: 0.5,
  flexWrap: "wrap",
  px: 0.75,
  py: 0.5,
  borderRadius: 1,
  bgcolor: "action.hover",
} as const

function Side(props: { players: string[] }) {
  return (
    <Box sx={SIDE_SX}>
      {props.players.map((p) => (
        <PlayerChip key={p} name={p} disableNav />
      ))}
    </Box>
  )
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
        {/* Player identity comes from PlayerChip (same swatch and color as
            everywhere else); the two sides are told apart by their grouping
            rather than by repainting every chip primary/secondary. */}
        <Side players={team1} />
        <Typography variant="body2" sx={{ mx: 0.5, color: "text.secondary" }}>
          vs
        </Typography>
        <Side players={team2} />
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
          sx={{
            color: "text.secondary",
            whiteSpace: "nowrap",
          }}
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
  const isAdmin = useIsAdmin()

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
    return isAdmin
      ? entries
      : entries.filter(
          ([, winRate]) => 1.0 - Math.abs(winRate - 0.5) * 2 >= threshold,
        )
  }, [teamRating, isAdmin])

  if (props.selectedPlayers.length % 2 !== 0) {
    return (
      <Alert severity="warning">
        An odd number of players can&apos;t be split into even teams. Pick one
        more, or add HardArmy as a filler.
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
      <Alert severity="warning">
        An odd number of players can&apos;t be split into even teams.
      </Alert>
    )
  }
  if (loading && teamPartition.length === 0) {
    return <Loading />
  }
  if (!loading && teamPartition.length === 0) {
    return (
      <Alert severity="warning">
        Pick at least 6 players to build tournament teams.
      </Alert>
    )
  }
  // Team cards are neutral surfaces with a colored top rule, matching how the
  // rest of the app separates groups — the old hardcoded pastels carrying blue
  // "primary" chips were the one place that ignored the theme entirely.

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
            <Paper
              variant="outlined"
              sx={{
                p: 2,
                borderTop: `3px solid ${CHART_PALETTE[i % CHART_PALETTE.length]}`,
              }}
            >
              <Typography
                variant="overline"
                sx={{ color: "text.secondary", display: "block", mb: 0.5 }}
              >
                Team {i + 1}
              </Typography>
              <Stack direction="row" spacing={0.5} sx={{ flexWrap: "wrap" }}>
                {team.map((t) => (
                  <PlayerChip key={t} name={t} />
                ))}
              </Stack>
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
  const count = props.selectedPlayers.length
  // Parity is the constraint that decides whether this page can answer at all,
  // so it is stated up front rather than as a warning after the fact.
  const parity =
    count === 0
      ? "No one picked yet"
      : count % 2 === 0
        ? `${count} picked, even teams possible`
        : `${count} picked, needs an even number`
  return (
    <FormGroup>
      <Typography
        variant="body2"
        sx={{
          mb: 0.5,
          color:
            count > 0 && count % 2 !== 0 ? "warning.main" : "text.secondary",
          fontWeight: 500,
        }}
      >
        {parity}
      </Typography>
      <Box
        sx={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: 0.5,
          py: 1,
        }}
      >
        {props.players.map((option) => (
          <FormControlLabel
            key={option}
            sx={{ mr: 0.5 }}
            control={
              <Checkbox
                checked={props.selectedPlayers.includes(option)}
                onChange={props.onChange}
                value={option}
              />
            }
            // The same identity used everywhere else in the app; disableNav
            // because the chip sits inside a control whose job is toggling.
            label={<PlayerChip name={option} disableNav />}
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
    <Page
      title="Balance Teams"
      description="Pick who is playing, and every way of splitting them is ranked by how close the game should be."
    >
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
      <Divider sx={{ mt: 4, mb: 2 }} />
      <Typography variant="caption" sx={{ color: "text.secondary" }}>
        Ratings use the{" "}
        <Link href="https://jmlr.org/papers/volume12/weng11a/weng11a.pdf">
          Bayesian Plackett-Luce model of Weng and Lin
        </Link>
        , an extension of the TrueSkill algorithm Xbox Live uses.
      </Typography>
    </Page>
  )
}
