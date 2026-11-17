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
import { alpha } from "@mui/material/styles"
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
import {
  FACTION_COLOR,
  FACTIONS,
  type Faction,
  generalFaction,
  toGeneralName,
} from "../../lib/general_utils"
import { matchHref } from "../../lib/links"
import { winRate } from "../../lib/utils"
import {
  type Grain,
  type Matchup,
  matchups,
  type Side,
  setLoserRecords,
  sumWL,
} from "./factionMatchups"
import { PlayerRecordChips, RecordText } from "./PlayerRecords"

const gamesLabel = (n: number) => `${n} game${n === 1 ? "" : "s"}`
const pct = (x: number) => `${Math.round(x * 100)}%`

function sideFaction(side: Side): Faction {
  return typeof side === "number" ? (generalFaction(side) ?? "USA") : side
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

function SideLabel({
  side,
  reverse = false,
}: {
  side: Side
  reverse?: boolean
}) {
  return (
    <Stack
      direction={reverse ? "row-reverse" : "row"}
      spacing={0.75}
      sx={{ alignItems: "center", minWidth: 0 }}
    >
      <SideAvatar side={side} size="1.5rem" />
      <Typography variant="subtitle2" noWrap sx={{ fontWeight: 600 }}>
        {sideName(side)}
      </Typography>
    </Stack>
  )
}

function SectionHeader({
  title,
  subtitle,
  action,
}: {
  title: string
  subtitle: React.ReactNode
  action?: React.ReactNode
}) {
  return (
    <Box sx={{ mb: 1.5 }}>
      <Stack
        direction="row"
        spacing={2}
        useFlexGap
        sx={{ alignItems: "center", flexWrap: "wrap", mb: 0.5 }}
      >
        <Typography variant="h5" sx={{ flexGrow: 1 }}>
          {title}
        </Typography>
        {action}
      </Stack>
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        {subtitle}
      </Typography>
    </Box>
  )
}

function GrainToggle({
  grain,
  onChange,
}: {
  grain: Grain
  onChange: (grain: Grain) => void
}) {
  return (
    <ToggleButtonGroup
      value={grain}
      exclusive
      size="small"
      onChange={(_, next: Grain | null) => next !== null && onChange(next)}
    >
      <ToggleButton value="general">Generals</ToggleButton>
      <ToggleButton value="faction">Factions</ToggleButton>
    </ToggleButtonGroup>
  )
}

// One general or faction: its record, a games-scaled bar, and who played it.
function SideRow({
  side,
  players,
  maxGames,
  note,
}: {
  side: Side
  players: PlayerWL[] | undefined
  maxGames: number
  note?: React.ReactNode
}) {
  const total = players && sumWL(players)
  return (
    <Box sx={{ opacity: total ? 1 : 0.5 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
        <SideLabel side={side} />
        <Box sx={{ flexGrow: 1 }} />
        {note}
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

// Faction cards, then matchups, then how the player who lost each set fared
// on each side - all over the bracket's linked games.
export default function FactionsPanel() {
  const records = useQuery(
    getBracketGeneralRecordsApiBracketGeneralRecordsGetOptions(),
  )
  const games = useQuery(
    getBracketFactionGamesApiBracketFactionGamesGetOptions(),
  )
  const [grain, setGrain] = React.useState<Grain>("general")
  return (
    <Stack spacing={5}>
      <QueryState query={records} what="faction records">
        {(rows) =>
          rows.length === 0 ? (
            <Typography variant="body2" sx={{ color: "text.secondary" }}>
              No tournament games have been played yet.
            </Typography>
          ) : (
            <Box>
              <SectionHeader
                title="Factions"
                subtitle="Each faction's record across the bracket, then every general within it."
              />
              <FactionBreakdown records={rows} />
            </Box>
          )
        }
      </QueryState>
      <QueryState query={games} what="matchups">
        {(rows) =>
          rows.length === 0 ? null : (
            <Stack spacing={5}>
              <MatchupList games={rows} grain={grain} onGrain={setGrain} />
              <SetLoserSection games={rows} grain={grain} onGrain={setGrain} />
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
        const color = FACTION_COLOR[faction]
        return (
          <Paper
            key={faction}
            variant="outlined"
            sx={{ overflow: "hidden", borderTop: `3px solid ${color}` }}
          >
            <Stack
              direction="row"
              spacing={1.5}
              sx={{
                alignItems: "center",
                px: 2,
                py: 1.5,
                bgcolor: alpha(color, 0.12),
              }}
            >
              <FactionAvatar faction={faction} size="2.75rem" />
              <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                <Typography
                  variant="overline"
                  sx={{ color, lineHeight: 1.2, display: "block" }}
                >
                  Faction
                </Typography>
                <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
                  {name}
                </Typography>
                <Typography variant="caption" sx={{ color: "text.secondary" }}>
                  {gamesLabel(played)} · {pct(played / totalGames)} of all
                </Typography>
              </Box>
              {played > 0 && (
                <Box sx={{ textAlign: "right" }}>
                  <RecordText {...total} />
                  <Typography
                    variant="caption"
                    sx={{ color: "text.secondary" }}
                  >
                    {pct(winRate(total.wins, total.losses))}
                  </Typography>
                </Box>
              )}
            </Stack>
            <Divider textAlign="left" sx={{ px: 2, pt: 1 }}>
              <Typography variant="overline" sx={{ color: "text.secondary" }}>
                Generals
              </Typography>
            </Divider>
            <Stack
              spacing={1.5}
              divider={<Divider flexItem />}
              sx={{ px: 2, pb: 2, pt: 0.5 }}
            >
              {generals.map((g) => (
                <SideRow
                  key={g}
                  side={g}
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

// Each side's share of the games won, in its faction's color. Same-faction
// pairs fade side b so the two halves stay distinguishable.
function SplitBar({ row }: { row: Matchup }) {
  const total = row.aWins + row.bWins
  const a = FACTION_COLOR[sideFaction(row.a)]
  const bBase = FACTION_COLOR[sideFaction(row.b)]
  const b = a === bBase ? alpha(bBase, 0.4) : bBase
  return (
    <Box
      sx={{
        display: "flex",
        height: 6,
        borderRadius: 3,
        overflow: "hidden",
        bgcolor: "action.hover",
      }}
    >
      <Box sx={{ width: `${(row.aWins / total) * 100}%`, bgcolor: a }} />
      <Box sx={{ width: `${(row.bWins / total) * 100}%`, bgcolor: b }} />
    </Box>
  )
}

function MatchupRow({ row }: { row: Matchup }) {
  const mirror = row.a === row.b
  const setLoserWins = row.games.filter((g) => g.winnerLostSet).length
  return (
    <Accordion
      disableGutters
      square
      elevation={0}
      slotProps={{ transition: { unmountOnExit: true } }}
      sx={{
        "&:not(:last-of-type)": { borderBottom: 1, borderColor: "divider" },
        "&::before": { display: "none" },
      }}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr 4.5rem 1fr",
              sm: "minmax(0, 10rem) 7rem minmax(0, 10rem) 1fr",
            },
            columnGap: 1.5,
            rowGap: 0.5,
            alignItems: "center",
            width: "100%",
          }}
        >
          <Box sx={{ justifySelf: "end", minWidth: 0 }}>
            <SideLabel side={row.a} reverse />
          </Box>
          <Box sx={{ textAlign: "center" }}>
            {mirror ? (
              <Typography variant="body2" sx={{ color: "text.secondary" }}>
                mirror
              </Typography>
            ) : (
              <>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {row.aWins} – {row.bWins}
                </Typography>
                <SplitBar row={row} />
              </>
            )}
          </Box>
          <Box sx={{ minWidth: 0 }}>
            {!mirror && <SideLabel side={row.b} />}
          </Box>
          <Stack
            direction="row"
            spacing={1}
            sx={{
              justifyContent: { xs: "center", sm: "flex-end" },
              alignItems: "center",
              gridColumn: { xs: "1 / -1", sm: "auto" },
            }}
          >
            {setLoserWins > 0 && (
              <Tooltip title="Games won by the player who went on to lose the set">
                <Chip
                  size="small"
                  variant="outlined"
                  color="warning"
                  label={`${setLoserWins} by set loser`}
                />
              </Tooltip>
            )}
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {gamesLabel(row.games.length)}
            </Typography>
          </Stack>
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ bgcolor: "action.hover" }}>
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
  onGrain,
}: {
  games: BracketFactionGame[]
  grain: Grain
  onGrain: (grain: Grain) => void
}) {
  const rows = React.useMemo(() => matchups(games, grain), [games, grain])
  return (
    <Box>
      <SectionHeader
        title="Matchups"
        subtitle={`Every ${grain} pairing that has come up, busiest first. Expand one to see each game and who played it.`}
        action={<GrainToggle grain={grain} onChange={onGrain} />}
      />
      <Paper variant="outlined" sx={{ overflow: "hidden" }}>
        {rows.map((row) => (
          <MatchupRow key={`${row.a}|${row.b}`} row={row} />
        ))}
      </Paper>
    </Box>
  )
}

function SetLoserSection({
  games,
  grain,
  onGrain,
}: {
  games: BracketFactionGame[]
  grain: Grain
  onGrain: (grain: Grain) => void
}) {
  const rows = React.useMemo(
    () => setLoserRecords(games, grain),
    [games, grain],
  )
  const overall = sumWL(rows)
  const overallGames = overall.wins + overall.losses
  const baseline = winRate(overall.wins, overall.losses)
  const maxGames = Math.max(...rows.map((r) => r.wins + r.losses), 0)
  if (overallGames === 0) return null
  return (
    <Box>
      <SectionHeader
        title="Wins by players who didn't advance"
        subtitle={
          <>
            The record of each set's loser within that set, by the {grain} they
            played each game. Overall they won {overall.wins} of {overallGames}{" "}
            ({pct(baseline)}) — a {grain} marked above that is where losing
            players kept winning.
          </>
        }
        action={<GrainToggle grain={grain} onChange={onGrain} />}
      />
      <Paper variant="outlined" sx={{ p: 2 }}>
        <Stack spacing={1.5} divider={<Divider flexItem />}>
          {rows.map((row) => {
            const rate = winRate(row.wins, row.losses)
            return (
              <SideRow
                key={row.side}
                side={row.side}
                players={row.players}
                maxGames={maxGames}
                note={
                  <Typography
                    variant="caption"
                    sx={{
                      fontWeight: 600,
                      color:
                        rate > baseline ? "warning.main" : "text.secondary",
                    }}
                  >
                    {pct(rate)}
                    {rate > baseline && " · above avg"}
                  </Typography>
                }
              />
            )
          })}
        </Stack>
      </Paper>
    </Box>
  )
}
