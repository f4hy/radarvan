import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import type { PlayerWL } from "../../api/types.gen"
import { PlayerChip } from "../../components/PlayerChip"
import { recordColor } from "../../lib/theme"

export function RecordText({ wins, losses }: { wins: number; losses: number }) {
  return (
    <Typography
      variant="body2"
      sx={{ color: recordColor(wins, losses), fontWeight: 600 }}
    >
      {wins}–{losses}
    </Typography>
  )
}

export function PlayerRecordChips({ players }: { players: PlayerWL[] }) {
  return (
    <Stack
      direction="row"
      spacing={1.5}
      useFlexGap
      sx={{ flexWrap: "wrap", alignItems: "center", mt: 0.75 }}
    >
      {players.map((p) => (
        <Stack
          key={p.player}
          direction="row"
          spacing={0.5}
          sx={{ alignItems: "center" }}
        >
          <PlayerChip name={p.player} />
          <RecordText wins={p.wins} losses={p.losses} />
        </Stack>
      ))}
    </Stack>
  )
}
