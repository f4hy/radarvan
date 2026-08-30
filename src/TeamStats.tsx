import Box from "@mui/material/Box"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Tab from "@mui/material/Tab"
import Tabs from "@mui/material/Tabs"
import Typography from "@mui/material/Typography"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import type { TeamRecord, TeamSizeGroup, TeamStatsResponse } from "./api"
import { TeamsClient } from "./clients/teams"
import Page from "./Page"
import QueryState from "./QueryState"
import { WinRateBar } from "./WinRateChip"
import { PlayerChip } from "./PlayerChip"
import { formatPercent, wilsonLowerBound, winRateTone } from "./utils"

function fetchTeamStats(): Promise<TeamStatsResponse> {
  return TeamsClient.getTeamStatsApiTeamStatsGet()
}

function TeamRow(props: { team: TeamRecord }) {
  const { team } = props
  // One rule for the color, shared with every other page (utils.winRateTone):
  // a 3-0 pairing reads neutral rather than triumphantly green.
  const verdict = winRateTone(team.wins, team.losses)
  const total = team.wins + team.losses
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
            sx={{
              fontWeight: 700,
              fontVariantNumeric: "tabular-nums",
              color: verdict.hex,
            }}
          >
            {formatPercent(verdict.rate)}
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
      <WinRateBar wins={team.wins} losses={team.losses} />
    </Paper>
  )
}

function TeamSizeTab(props: { group: TeamSizeGroup }) {
  // Ranked by the Wilson lower bound rather than the raw rate, so a 4-0 duo
  // no longer outranks a 20-8 one — matching how the row's own bar is faded.
  // Keyed once per team rather than twice per comparison: the bound costs a
  // sqrt and an object, and this list runs to ~80 teams.
  const sorted = React.useMemo(
    () =>
      props.group.teams
        .map((team) => ({
          team,
          key: wilsonLowerBound(team.wins, team.losses),
        }))
        .sort((a, b) => b.key - a.key)
        .map((entry) => entry.team),
    [props.group],
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
  // null until the groups arrive: hardcoding 2v2 leaves the Tabs pointing at a
  // value that may not exist, which renders no tab as selected while the
  // content silently falls back to the first group.
  const [tab, setTab] = React.useState<number | null>(null)
  const query = useQuery({
    queryKey: ["teamStats"],
    queryFn: fetchTeamStats,
  })

  return (
    <Page
      title="Team Stats"
      description="Which pairings actually work. A team needs more than 3 games together to show up here."
    >
      <QueryState query={query} what="team stats">
        {(teamStats) => {
          const groups = teamStats.groups
          // Prefer 2v2 when it exists (the most common format), else the first
          // group that does — and keep the Tabs value and the rendered group in
          // agreement.
          const activeGroup =
            groups.find((g) => g.size === (tab ?? 2)) ?? groups[0]
          return (
            <>
              <Divider sx={{ mb: 1 }} />
              <Tabs
                value={activeGroup?.size ?? false}
                onChange={(_, v) => setTab(v)}
              >
                {groups.map((g) => (
                  <Tab
                    key={g.size}
                    value={g.size}
                    label={`${g.size}v${g.size}`}
                  />
                ))}
              </Tabs>
              {activeGroup && <TeamSizeTab group={activeGroup} />}
            </>
          )
        }}
      </QueryState>
    </Page>
  )
}
