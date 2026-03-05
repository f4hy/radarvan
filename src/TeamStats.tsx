import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Divider from "@mui/material/Divider"
import LinearProgress from "@mui/material/LinearProgress"
import Loading from "./Loading"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Tab from "@mui/material/Tab"
import Tabs from "@mui/material/Tabs"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { TeamRecord, TeamSizeGroup, TeamStatsResponse } from "./api"
import { Client } from "./Client"
import { useErrorSnackbar } from "./useErrorSnackbar"
import { winRate } from "./utils"

function getTeamStats(
  callback: (m: TeamStatsResponse) => void,
  onError = console.error,
) {
  Client.getTeamStatsApiTeamStatsGet().then(callback).catch(onError)
}

const getRateColor = (rate: number): "success" | "warning" | "error" => {
  if (rate >= 0.55) return "success"
  if (rate >= 0.45) return "warning"
  return "error"
}

function TeamRow(props: { team: TeamRecord }) {
  const { team } = props
  const rate = winRate(team.wins, team.losses)
  const total = team.wins + team.losses
  return (
    <Paper elevation={1} sx={{ p: 1.5 }}>
      <Box sx={{ display: "flex", justifyContent: "space-between", mb: 0.75 }}>
        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
          {team.players.map((p) => (
            <Chip key={p} label={p} size="small" />
          ))}
        </Box>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ whiteSpace: "nowrap", ml: 1, alignSelf: "center" }}
        >
          {(rate * 100).toFixed(0)}% &nbsp;({team.wins}W–{team.losses}L ·{" "}
          {total} games)
        </Typography>
      </Box>
      <LinearProgress
        variant="determinate"
        value={rate * 100}
        color={getRateColor(rate)}
        sx={{ height: 7, borderRadius: 4 }}
      />
    </Paper>
  )
}

function TeamSizeTab(props: { group: TeamSizeGroup }) {
  const sorted = [...props.group.teams].sort(
    (a, b) => winRate(b.wins, b.losses) - winRate(a.wins, a.losses),
  )
  return (
    <Stack
      spacing={1}
      sx={{ p: 1.5, bgcolor: "background.default", borderRadius: 1 }}
    >
      {sorted.map((team) => (
        <TeamRow key={team.players.join(",")} team={team} />
      ))}
    </Stack>
  )
}

export default function DisplayTeamStats() {
  const [teamStats, setTeamStats] = React.useState<TeamStatsResponse | null>(
    null,
  )
  const [tab, setTab] = React.useState<number>(2)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    getTeamStats(setTeamStats, showError)
  }, [showError])

  if (teamStats === null) {
    return (
      <>
        <Loading />
        {errorSnackbar}
      </>
    )
  }

  const groups = teamStats.groups
  const activeGroup = groups.find((g) => g.size === tab) ?? groups[0]

  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000, p: 2 }}>
      <Typography variant="h4">Team Stats</Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        Win rates for teams with more than 3 games together. Sorted by win rate.
      </Typography>
      <Divider sx={{ mb: 1 }} />
      <Tabs value={tab} onChange={(_, v) => setTab(v)}>
        {groups.map((g) => (
          <Tab key={g.size} value={g.size} label={`${g.size}v${g.size}`} />
        ))}
      </Tabs>
      {activeGroup && <TeamSizeTab group={activeGroup} />}
      {errorSnackbar}
    </Paper>
  )
}
