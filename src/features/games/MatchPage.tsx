import Alert from "@mui/material/Alert"
import Link from "@mui/material/Link"
import { useQuery } from "@tanstack/react-query"
import { Link as RouterLink, useParams } from "react-router"
import type { MatchInfo } from "../../api"
import { MatchesClient } from "../../clients/matches"
import { MatchCard } from "../../components/MatchCard"
import Page from "../../components/Page"
import QueryState from "../../components/QueryState"
import { gameNightHref } from "../../lib/links"

function matchupLabel(match: MatchInfo): string {
  const teams = new Map<number, string[]>()
  for (const p of match.players) {
    teams.set(p.team, [...(teams.get(p.team) ?? []), p.name])
  }
  return [...teams.values()].map((names) => names.join(", ")).join(" vs ")
}

export default function MatchPage() {
  const { matchId = "" } = useParams()
  const valid = /^\d+$/.test(matchId)
  const id = Number(matchId)
  // Shares the ["match", id] key with Records and Tournaments.
  const query = useQuery({
    queryKey: ["match", id],
    // An unknown ID comes back as 200 with `null`, which the generated type
    // doesn't admit.
    queryFn: (): Promise<MatchInfo | null> =>
      MatchesClient.getMatchByIdApiMatchMatchIdGet({ matchId: id }),
    enabled: valid,
  })
  const notFound = (
    <Alert severity="warning">
      There's no match with ID <code>{matchId}</code>.
    </Alert>
  )
  const match = query.data
  return (
    <Page
      title="Match"
      tabTitle={match ? matchupLabel(match) : undefined}
      surface={false}
      description={
        match && (
          <Link
            component={RouterLink}
            to={gameNightHref(match.date.toISOString().slice(0, 10))}
          >
            See the rest of that night
          </Link>
        )
      }
    >
      {valid ? (
        <QueryState query={query} what={`match #${matchId}`}>
          {(m) =>
            m == null ? (
              notFound
            ) : (
              <MatchCard match={m} idx={0} defaultDetailsOpen />
            )
          }
        </QueryState>
      ) : (
        notFound
      )}
    </Page>
  )
}
