import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import { useQuery } from "@tanstack/react-query"

import {
  getEligiblePlayersApiPlayerProfileEligiblePlayersGetOptions,
  getPlayerGameCountsApiPlayerGameCountsGetOptions,
} from "../api/@tanstack/react-query.gen"
import { PlayerChip } from "./PlayerChip"

/** Empty-state shortcut for a player picker: the regulars, busiest first, as
 * links. The eligible list already excludes computer players. */
export function PlayerQuickPick(props: {
  prompt: string
  hrefFor: (name: string) => string
  exclude?: string | null
}) {
  const { data: eligible = [] } = useQuery({
    ...getEligiblePlayersApiPlayerProfileEligiblePlayersGetOptions(),
    select: (names) => names.filter((n): n is string => n != null),
  })
  const { data: counts } = useQuery(
    getPlayerGameCountsApiPlayerGameCountsGetOptions(),
  )
  const games = new Map(counts?.map((c) => [c.name, c.count]))
  const names = eligible
    .filter((n) => n !== props.exclude)
    .sort((a, b) => (games.get(b) ?? 0) - (games.get(a) ?? 0))

  return (
    <Stack spacing={1} sx={{ mt: 2 }}>
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        {props.prompt}
      </Typography>
      <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
        {names.map((name) => (
          <PlayerChip
            key={name}
            name={name}
            size="medium"
            to={props.hrefFor(name)}
          />
        ))}
      </Stack>
    </Stack>
  )
}
