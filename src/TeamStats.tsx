import Box from "@mui/material/Box"
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
import { PlayerChip } from "./PlayerChip"
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
  // De-emphasize small-sample rows so a 100% (3 games) doesn't read as loudly
  // as a 64% (22 games). Bars fade in as the sample grows toward ~15 games.
  const confidence = Math.min(1, total / 15)
  return (
    <Paper elevation={1} sx={{ p: 1.5 }}>
      <Box
        sx={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: 1,
          mb: 0.75,
        }}
      >
        <Box sx={{ display: "flex", gap: 0.5, flexWrap: "wrap" }}>
          {team.players.map((p) => (
            <PlayerChip key={p} name={p} />
          ))}
        </Box>
        <Box sx={{ textAlign: "right", whiteSpace: "nowrap" }}>
          <Typography
            component="span"
            sx={{ fontWeight: 700, fontVariantNumeric: "tabular-nums" }}
            color={`${getRateColor(rate)}.main`}
          >
            {(rate * 100).toFixed(0)}%
          </Typography>
          <Typography
            variant="caption"
            sx={{
              color: "text.secondary",
              ml: 1,
            }}
          >
            {team.wins}W–{team.losses}L · {total}g
          </Typography>
        </Box>
      </Box>
      <LinearProgress
        variant="determinate"
        value={rate * 100}
        color={getRateColor(rate)}
        sx={{ height: 7, borderRadius: 4, opacity: 0.45 + 0.55 * confidence }}
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
      <Typography
        sx={{
          color: "text.secondary",
          mb: 2,
        }}
      >
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
