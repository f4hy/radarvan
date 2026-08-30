import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import type { MatchInfo, Statistic, Superlatives } from "./api"
import { Client } from "./Client"
import Page from "./Page"
import QueryState from "./QueryState"
import { DisplayMatchInfo } from "./Matches"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Card from "@mui/material/Card"
import CardContent from "@mui/material/CardContent"
import Chip from "@mui/material/Chip"
import Divider from "@mui/material/Divider"
import Grid from "@mui/material/Grid"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import SportsScoreIcon from "@mui/icons-material/SportsScore"
import { PlayerChip } from "./PlayerChip"

// First match wins, so the order is load-bearing: a more specific bucket has
// to sit above one whose keywords are substrings of the same stat names.
// "Efficiency" used to sit below "Combat & Activity" and "Money", which made it
// unreachable - every "… to Win" record matched "Units"/"Buildings"/"Money"
// first, and the section never rendered.
const CATEGORY_ORDER: { label: string; keywords: string[] }[] = [
  { label: "Overview", keywords: ["Games"] },
  { label: "Ratings", keywords: ["Rating", "Record", "Upset"] },
  { label: "Streaks", keywords: ["Streak", "Game Night"] },
  { label: "Maps", keywords: ["Map"] },
  { label: "Match Duration", keywords: ["Longest", "Shortest"] },
  { label: "First Blood", keywords: ["First Blood"] },
  { label: "Hunted", keywords: ["Hunted"] },
  { label: "APM", keywords: ["APM"] },
  { label: "Superweapons & Tech", keywords: ["Superweapon", "Tech Captures"] },
  { label: "Efficiency", keywords: ["to Win"] },
  { label: "Money", keywords: ["Money"] },
  {
    label: "Combat & Activity",
    keywords: ["Units", "Buildings", "XP", "Upgrades", "Rank 5", "Destroy"],
  },
  { label: "Teamwork", keywords: ["Duo"] },
  { label: "Activity", keywords: ["Day"] },
]

function categorize(statName: string): string {
  for (const { label, keywords } of CATEGORY_ORDER) {
    if (keywords.some((kw) => statName.includes(kw))) return label
  }
  return "Other"
}

function LoadAndShowMatch({ matchId }: { matchId: number }) {
  const query = useQuery({
    queryKey: ["match", matchId],
    queryFn: () => Client.getMatchByIdApiMatchMatchIdGet({ matchId }),
  })
  return (
    <QueryState query={query} what={`match #${matchId}`}>
      {(match) => <DisplayMatchInfo match={match} idx={matchId} />}
    </QueryState>
  )
}

const StatCard = React.memo(function StatCard({
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
          gutterBottom
          sx={{
            color: "text.secondary",
            display: "block",
          }}
        >
          {stat.statName}
        </Typography>
        <Typography
          variant="h4"
          sx={{
            fontWeight: "bold",
            my: 1,
          }}
        >
          {displayValue}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 0.5, mt: 1 }}>
          {stat.player && <PlayerChip name={stat.player} />}
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
})

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
          <Grid size={{ xs: 12, sm: 6, md: 4, lg: 3 }} key={stat.statName}>
            <StatCard stat={stat} onMatchClick={onMatchClick} />
          </Grid>
        ))}
      </Grid>
    </Box>
  )
}

function SuperlativesBody({ data }: { data: Superlatives }) {
  const [selectedMatch, setSelectedMatch] = React.useState<number | null>(null)
  const matchPanelRef = React.useRef<HTMLDivElement | null>(null)

  // The panel renders above every category section, so a chip clicked from the
  // Money section (hundreds of pixels down) would otherwise change the page
  // entirely off-screen and read as a dead click.
  React.useEffect(() => {
    if (selectedMatch === null) return
    matchPanelRef.current?.scrollIntoView({
      behavior: "smooth",
      block: "start",
    })
  }, [selectedMatch])

  const grouped = React.useMemo(() => {
    const map = new Map<string, Statistic[]>()
    for (const stat of data.stats) {
      const cat = categorize(stat.statName)
      const bucket = map.get(cat)
      if (bucket) {
        bucket.push(stat)
      } else {
        map.set(cat, [stat])
      }
    }
    return map
  }, [data])

  const orderedGroups = React.useMemo(() => {
    const groups: [string, Statistic[]][] = CATEGORY_ORDER.map(
      ({ label }): [string, Statistic[]] => [label, grouped.get(label) ?? []],
    ).filter(([, stats]) => stats.length > 0)
    if (grouped.has("Other")) {
      groups.push(["Other", grouped.get("Other")!])
    }
    return groups
  }, [grouped])

  if (data.stats.length === 0) {
    return (
      <Typography sx={{ color: "text.secondary" }}>
        Nothing here yet. Records are computed overnight, so they appear after
        the next run.
      </Typography>
    )
  }

  return (
    <>
      <Typography variant="body2" sx={{ color: "text.secondary", mb: 1 }}>
        All-time bests across 2v2, 3v3 and 4v4 team games. Updated nightly, last
        on {data.computedAt.toLocaleDateString()}.
      </Typography>
      <Divider sx={{ mb: 3 }} />
      {selectedMatch !== null && (
        <Box ref={matchPanelRef} sx={{ mb: 3, scrollMarginTop: 80 }}>
          <Stack
            direction="row"
            sx={{ alignItems: "center", justifyContent: "space-between" }}
          >
            <Typography variant="subtitle2" sx={{ color: "text.secondary" }}>
              Match #{selectedMatch}
            </Typography>
            <Button size="small" onClick={() => setSelectedMatch(null)}>
              Close
            </Button>
          </Stack>
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
    </>
  )
}

export default function DisplaySuperlatives() {
  const query = useQuery({
    queryKey: ["superlatives"],
    queryFn: () => Client.getSuperlativesApiSuperlativesGet(),
  })
  return (
    <Page title="Records">
      <QueryState query={query} what="records">
        {(data) => <SuperlativesBody data={data} />}
      </QueryState>
    </Page>
  )
}
