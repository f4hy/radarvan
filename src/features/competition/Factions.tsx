import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Divider from "@mui/material/Divider"
import Link from "@mui/material/Link"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import { useQuery } from "@tanstack/react-query"
import React from "react"
import { Link as RouterLink } from "react-router"
import {
  getBracketFactionGamesApiBracketFactionGamesGetOptions,
  getBracketGeneralRecordsApiBracketGeneralRecordsGetOptions,
} from "../../api/@tanstack/react-query.gen"
import type {
  BracketFactionGame,
  GeneralPickRecord,
  PlayerWL,
} from "../../api/types.gen"
import { FactionAvatar, GeneralAvatar } from "../../components/Generals"
import { PlayerChip } from "../../components/PlayerChip"
import QueryState from "../../components/QueryState"
import { WinLossVolumeBar } from "../../components/WinRateChip"
import type { General } from "../../lib/General"
import { FACTIONS, toGeneralName } from "../../lib/general_utils"
import { matchHref } from "../../lib/links"
import {
  type Grain,
  type Matchup,
  matchups,
  type Side,
  setLoserRecords,
} from "./factionMatchups"
import { PlayerRecordChips, RecordText } from "./PlayerRecords"

type WL = { wins: number; losses: number }

const sumWL = (rows: WL[]): WL => ({
  wins: rows.reduce((n, r) => n + r.wins, 0),
  losses: rows.reduce((n, r) => n + r.losses, 0),
})

const gamesLabel = (n: number) => `${n} game${n === 1 ? "" : "s"}`

function GeneralRow({
  general,
  players,
  maxGames,
}: {
  general: General
  players: PlayerWL[] | undefined
  maxGames: number
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
          {total ? gamesLabel(total.wins + total.losses) : "not played yet"}
        </Typography>
        {total && <RecordText {...total} />}
      </Stack>
      {players && total && (
        <>
          <Box sx={{ display: "flex", mt: 0.5 }}>
            <WinLossVolumeBar {...total} max={maxGames} />
          </Box>
          <PlayerRecordChips players={players} />
        </>
      )}
    </Box>
  )
}

// Factions, then general-vs-general matchups, then how the player who lost
// each set fared on each side - all over the bracket's linked games.
export default function FactionsPanel() {
  const records = useQuery(
    getBracketGeneralRecordsApiBracketGeneralRecordsGetOptions(),
  )
  const games = useQuery(
    getBracketFactionGamesApiBracketFactionGamesGetOptions(),
  )
  const [grain, setGrain] = React.useState<Grain>("general")
  return (
    <Stack spacing={4}>
      <QueryState query={records} what="faction records">
        {(rows) =>
          rows.length === 0 ? (
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              No tournament games have been played yet.
            </Typography>
          ) : (
            <FactionBreakdown records={rows} />
          )
        }
      </QueryState>
      <QueryState query={games} what="matchups">
        {(rows) =>
          rows.length === 0 ? null : (
            <Stack spacing={4}>
              <Box>
                <Stack
                  direction="row"
                  spacing={2}
                  useFlexGap
                  sx={{ alignItems: "center", flexWrap: "wrap", mb: 1.5 }}
                >
                  <Typography variant="h5" sx={{ flexGrow: 1 }}>
                    Matchups
                  </Typography>
                  <ToggleButtonGroup
                    value={grain}
                    exclusive
                    size="small"
                    onChange={(_, next: Grain | null) =>
                      next !== null && setGrain(next)
                    }
                  >
                    <ToggleButton value="general">Generals</ToggleButton>
                    <ToggleButton value="faction">Factions</ToggleButton>
                  </ToggleButtonGroup>
                </Stack>
                <MatchupList games={rows} grain={grain} />
              </Box>
              <SetLoserSection games={rows} grain={grain} />
            </Stack>
          )
        }
      </QueryState>
    </Stack>
  )
}

function FactionBreakdown({ records }: { records: GeneralPickRecord[] }) {
  const byGeneral = new Map(records.map((r) => [r.general, r.players]))
  const totals = records.map((r) => sumWL(r.players))
  const totalGames = totals.reduce((n, t) => n + t.wins + t.losses, 0)
  const maxGames = Math.max(...totals.map((t) => t.wins + t.losses))

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
        const played = total.wins + total.losses
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
                  {gamesLabel(played)} ·{" "}
                  {Math.round((played / totalGames) * 100)}% of all
                </Typography>
              </Box>
              {played > 0 && <RecordText {...total} />}
            </Stack>
            <Stack spacing={1.5} divider={<Divider flexItem />}>
              {generals.map((g) => (
                <GeneralRow
                  key={g}
                  general={g}
                  players={byGeneral.get(g)}
                  maxGames={maxGames}
                />
              ))}
            </Stack>
          </Paper>
        )
      })}
    </Box>
  )
}

function sideName(side: Side): string {
  return typeof side === "number"
    ? toGeneralName(side)
    : (FACTIONS.find((f) => f.faction === side)?.name ?? side)
}

function SideAvatar({ side, size }: { side: Side; size: string }) {
  return typeof side === "number" ? (
    <GeneralAvatar general={side} size={size} />
  ) : (
    <FactionAvatar faction={side} size={size} />
  )
}

function SideLabel({ side }: { side: Side }) {
  return (
    <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
      <SideAvatar side={side} size="1.5rem" />
      <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
        {sideName(side)}
      </Typography>
    </Stack>
  )
}

function GameLine({ game }: { game: BracketFactionGame }) {
  return (
    <Stack
      direction="row"
      spacing={1}
      useFlexGap
      sx={{ alignItems: "center", flexWrap: "wrap" }}
    >
      <PlayerChip name={game.winner} size="small" />
      <Typography variant="body2">
        ({toGeneralName(game.winnerGeneral)}) beat
      </Typography>
      <PlayerChip name={game.loser} size="small" />
      <Typography variant="body2">
        ({toGeneralName(game.loserGeneral)})
      </Typography>
      <Link
        component={RouterLink}
        to={matchHref(game.matchId)}
        variant="caption"
        sx={{ color: "text.secondary" }}
      >
        {game.stage}
      </Link>
      {game.winnerLostSet && (
        <Tooltip title="Won this game, but lost the set">
          <Chip
            size="small"
            variant="outlined"
            color="warning"
            label="lost the set"
          />
        </Tooltip>
      )}
    </Stack>
  )
}

function MatchupRow({ row }: { row: Matchup }) {
  const mirror = row.a === row.b
  return (
    <Accordion disableGutters variant="outlined">
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack
          direction="row"
          spacing={1.5}
          useFlexGap
          sx={{ alignItems: "center", flexWrap: "wrap", width: "100%" }}
        >
          <SideLabel side={row.a} />
          {mirror ? (
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              mirror
            </Typography>
          ) : (
            <>
              <RecordText wins={row.aWins} losses={row.bWins} />
              <SideLabel side={row.b} />
            </>
          )}
          <Box sx={{ flexGrow: 1 }} />
          {row.setLoserWins > 0 && (
            <Typography variant="caption" sx={{ color: "warning.main" }}>
              {row.setLoserWins} won by the set loser
            </Typography>
          )}
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {gamesLabel(row.games.length)}
          </Typography>
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1}>
          {row.games.map((g) => (
            <GameLine key={g.matchId} game={g} />
          ))}
        </Stack>
      </AccordionDetails>
    </Accordion>
  )
}

function MatchupList({
  games,
  grain,
}: {
  games: BracketFactionGame[]
  grain: Grain
}) {
  const rows = React.useMemo(() => matchups(games, grain), [games, grain])
  return (
    <Box>
      <Typography variant="body2" sx={{ color: "text.secondary", mb: 1 }}>
        Every pairing that has come up, with how many games each side won.
        Expand one to see who played it.
      </Typography>
      {rows.map((row) => (
        <MatchupRow key={`${row.a}|${row.b}`} row={row} />
      ))}
    </Box>
  )
}

function SetLoserSection({
  games,
  grain,
}: {
  games: BracketFactionGame[]
  grain: Grain
}) {
  const rows = React.useMemo(
    () => setLoserRecords(games, grain),
    [games, grain],
  )
  const overall = sumWL(rows)
  const overallGames = overall.wins + overall.losses
  const maxGames = Math.max(...rows.map((r) => r.wins + r.losses), 0)
  if (overallGames === 0) return null
  return (
    <Box>
      <Typography variant="h5" sx={{ mb: 0.5 }}>
        Wins by players who didn't advance
      </Typography>
      <Typography variant="body2" sx={{ color: "text.secondary", mb: 1.5 }}>
        Every set has a loser, and they still win games along the way. This is
        their record in their sets by the {grain} they played each game: they
        won {overall.wins} of {overallGames} (
        {Math.round((overall.wins / overallGames) * 100)}%) overall, so a{" "}
        {grain} well above that is where losing players kept winning.
      </Typography>
      <Stack spacing={1.5} divider={<Divider flexItem />}>
        {rows.map((row) => (
          <Box key={row.side}>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <SideLabel side={row.side} />
              <Box sx={{ flexGrow: 1 }} />
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                {gamesLabel(row.wins + row.losses)}
              </Typography>
              <RecordText wins={row.wins} losses={row.losses} />
            </Stack>
            <Box sx={{ display: "flex", mt: 0.5 }}>
              <WinLossVolumeBar
                wins={row.wins}
                losses={row.losses}
                max={maxGames}
              />
            </Box>
            <PlayerRecordChips players={row.players} />
          </Box>
        ))}
      </Stack>
    </Box>
  )
}
