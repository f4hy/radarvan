import * as React from "react"
import type { MatchInfo, Statistic, Superlatives } from "./api"
import { Client } from "./Client"
import { useErrorSnackbar } from "./useErrorSnackbar"
import Loading from "./Loading"
import { DisplayMatchInfo } from "./Matches"
import Box from "@mui/material/Box"
import Card from "@mui/material/Card"
import CardContent from "@mui/material/CardContent"
import Chip from "@mui/material/Chip"
import Divider from "@mui/material/Divider"
import Grid from "@mui/material/Grid"
import Paper from "@mui/material/Paper"
import Typography from "@mui/material/Typography"
import PersonIcon from "@mui/icons-material/Person"
import SportsScoreIcon from "@mui/icons-material/SportsScore"

const CATEGORY_ORDER: { label: string; keywords: string[] }[] = [
  { label: "Overview", keywords: ["Games"] },
  { label: "Streaks", keywords: ["Streak"] },
  { label: "Maps", keywords: ["Map"] },
  { label: "Match Duration", keywords: ["Longest", "Shortest"] },
  { label: "First Blood", keywords: ["First Blood"] },
  { label: "APM", keywords: ["APM"] },
  { label: "Money", keywords: ["Money"] },
  {
    label: "Combat & Activity",
    keywords: ["Units", "Buildings", "XP", "Upgrades"],
  },
  { label: "Efficiency", keywords: ["to Win"] },
  { label: "Activity", keywords: ["Day"] },
]

function categorize(statName: string): string {
  for (const { label, keywords } of CATEGORY_ORDER) {
    if (keywords.some((kw) => statName.includes(kw))) return label
  }
  return "Other"
}

function LoadAndShowMatch({ matchId }: { matchId: number }) {
  const [match, setMatch] = React.useState<MatchInfo | null>(null)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    Client.getMatchByIdApiMatchMatchIdGet({ matchId })
      .then(setMatch)
      .catch(showError)
  }, [matchId, showError])

  if (match === null) {
    return (
      <>
        <Loading />
        {errorSnackbar}
      </>
    )
  }
  return (
    <>
      <DisplayMatchInfo match={match} idx={matchId} />
      {errorSnackbar}
    </>
  )
}

function StatCard({
  stat,
  onMatchClick,
}: {
  stat: Statistic
  onMatchClick: (id: number) => void
}) {
  const displayValue = stat.value != null ? String(stat.value) : "—"

  return (
    <Card
      variant="outlined"
      sx={{ height: "100%", display: "flex", flexDirection: "column" }}
    >
      <CardContent sx={{ flexGrow: 1 }}>
        <Typography
          variant="caption"
          color="text.secondary"
          display="block"
          gutterBottom
        >
          {stat.statName}
        </Typography>
        <Typography variant="h4" fontWeight="bold" sx={{ my: 1 }}>
          {displayValue}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}>
          {stat.player && (
            <Chip
              icon={<PersonIcon />}
              label={stat.player}
              size="small"
              variant="outlined"
            />
          )}
          {stat.matchId != null && (
            <Chip
              icon={<SportsScoreIcon />}
              label={`Match #${stat.matchId}`}
              size="small"
              variant="outlined"
              color="primary"
              clickable
              onClick={() => onMatchClick(stat.matchId!)}
            />
          )}
        </Box>
      </CardContent>
    </Card>
  )
}

function CategorySection({
  label,
  stats,
  onMatchClick,
}: {
  label: string
  stats: Statistic[]
  onMatchClick: (id: number) => void
}) {
  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h6" gutterBottom>
        {label}
      </Typography>
      <Grid container spacing={2}>
        {stats.map((stat) => (
          <Grid item xs={12} sm={6} md={4} lg={3} key={stat.statName}>
            <StatCard stat={stat} onMatchClick={onMatchClick} />
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

export default function DisplaySuperlatives() {
  const [data, setData] = React.useState<Superlatives | null>(null)
  const [selectedMatch, setSelectedMatch] = React.useState<number | null>(null)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    Client.getSuperlativesApiSuperlativesGet().then(setData).catch(showError)
  }, [showError])

  if (data === null) {
    return <Loading />
  }

  if (data.stats.length === 0) {
    return (
      <Paper sx={{ p: 3, maxWidth: 600 }}>
        <Typography variant="h6" gutterBottom>
          No records yet
        </Typography>
        <Typography color="text.secondary">
          Statistics are computed nightly. Use the recompute endpoint to
          generate them now.
        </Typography>
      </Paper>
    )
  }

  const grouped = new Map<string, Statistic[]>()
  for (const stat of data.stats) {
    const cat = categorize(stat.statName)
    const bucket = grouped.get(cat)
    if (bucket) {
      bucket.push(stat)
    } else {
      grouped.set(cat, [stat])
    }
  }

  const orderedGroups: [string, Statistic[]][] = CATEGORY_ORDER.map(
    ({ label }): [string, Statistic[]] => [label, grouped.get(label) ?? []],
  ).filter(([, stats]) => stats.length > 0)

  if (grouped.has("Other")) {
    orderedGroups.push(["Other", grouped.get("Other")!])
  }

  return (
    <Paper sx={{ flexGrow: 1, p: 2, maxWidth: 1400 }}>
      <Box sx={{ mb: 2 }}>
        <Typography variant="h5" fontWeight="bold">
          Records
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Computed {data.computedAt.toLocaleDateString()}. From 2v2, 3v3 and 4v4 team matches
        </Typography>
      </Box>
      <Divider sx={{ mb: 3 }} />
      {selectedMatch !== null && (
        <Box sx={{ mb: 3 }}>
          <LoadAndShowMatch matchId={selectedMatch} />
          <Divider sx={{ mt: 2 }} />
        </Box>
      )}
      {orderedGroups.map(([label, stats]) => (
        <CategorySection
          key={label}
          label={label}
          stats={stats}
          onMatchClick={setSelectedMatch}
        />
      ))}
      {errorSnackbar}
    </Paper>
  )
}
