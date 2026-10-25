import Box from "@mui/material/Box"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import { useQuery } from "@tanstack/react-query"
import { getBracketGeneralRecordsApiBracketGeneralRecordsGetOptions } from "../../api/@tanstack/react-query.gen"
import type { GeneralPickRecord, PlayerWL } from "../../api/types.gen"
import { FactionAvatar, GeneralAvatar } from "../../components/Generals"
import QueryState from "../../components/QueryState"
import { WinLossVolumeBar } from "../../components/WinRateChip"
import type { General } from "../../lib/General"
import { FACTIONS, toGeneralName } from "../../lib/general_utils"
import { PlayerRecordChips, RecordText } from "./PlayerRecords"

type WL = { wins: number; losses: number }

const sumWL = (rows: WL[]): WL => ({
  wins: rows.reduce((n, r) => n + r.wins, 0),
  losses: rows.reduce((n, r) => n + r.losses, 0),
})

const picksLabel = ({ wins, losses }: WL) =>
  `${wins + losses} pick${wins + losses === 1 ? "" : "s"}`

function GeneralRow({
  general,
  players,
  maxPicks,
}: {
  general: General
  players: PlayerWL[] | undefined
  maxPicks: number
}) {
  const total = players && sumWL(players)
  return (
    <Box sx={{ opacity: total ? 1 : 0.5 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
        <GeneralAvatar general={general} size="1.5rem" />
        <Typography variant="subtitle2" sx={{ fontWeight: 600, flexGrow: 1 }}>
          {toGeneralName(general)}
        </Typography>
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          {total ? picksLabel(total) : "not picked yet"}
        </Typography>
        {total && <RecordText {...total} />}
      </Stack>
      {players && total && (
        <>
          <Box sx={{ display: "flex", mt: 0.5 }}>
            <WinLossVolumeBar {...total} max={maxPicks} />
          </Box>
          <PlayerRecordChips players={players} />
        </>
      )}
    </Box>
  )
}

// Which factions and generals have been picked across the bracket's linked
// games, and how each pick went. Every player in a game is one pick.
export default function FactionsPanel() {
  const query = useQuery(
    getBracketGeneralRecordsApiBracketGeneralRecordsGetOptions(),
  )
  return (
    <QueryState query={query} what="faction picks">
      {(records) =>
        records.length === 0 ? (
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            No tournament games have been played yet.
          </Typography>
        ) : (
          <FactionBreakdown records={records} />
        )
      }
    </QueryState>
  )
}

function FactionBreakdown({ records }: { records: GeneralPickRecord[] }) {
  const byGeneral = new Map(records.map((r) => [r.general, r.players]))
  const totals = records.map((r) => sumWL(r.players))
  const totalPicks = totals.reduce((n, t) => n + t.wins + t.losses, 0)
  const maxPicks = Math.max(...totals.map((t) => t.wins + t.losses))

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(min(300px, 100%), 1fr))",
        gap: 2,
      }}
    >
      {FACTIONS.map(({ faction, name, generals }) => {
        const total = sumWL(generals.flatMap((g) => byGeneral.get(g) ?? []))
        const picks = total.wins + total.losses
        return (
          <Paper key={faction} variant="outlined" sx={{ p: 2 }}>
            <Stack
              direction="row"
              spacing={1.5}
              sx={{ alignItems: "center", mb: 1 }}
            >
              <FactionAvatar faction={faction} size="2.5rem" />
              <Box sx={{ flexGrow: 1 }}>
                <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
                  {name}
                </Typography>
                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                  {picksLabel(total)} · {Math.round((picks / totalPicks) * 100)}
                  % of all
                </Typography>
              </Box>
              {picks > 0 && <RecordText {...total} />}
            </Stack>
            <Stack spacing={1.5} divider={<Divider flexItem />}>
              {generals.map((g) => (
                <GeneralRow
                  key={g}
                  general={g}
                  players={byGeneral.get(g)}
                  maxPicks={maxPicks}
                />
              ))}
            </Stack>
          </Paper>
        )
      })}
    </Box>
  )
}
