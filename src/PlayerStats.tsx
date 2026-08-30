import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Collapse from "@mui/material/Collapse"
import IconButton from "@mui/material/IconButton"
import FormatToggle, { TEAM_FORMATS } from "./FormatToggle"
import Page from "./Page"
import QueryState from "./QueryState"
import { PlayerChip, PlayerLabel } from "./PlayerChip"
import Divider from "@mui/material/Divider"
import Grid from "@mui/material/Grid"
import List from "@mui/material/List"
import ListItem from "@mui/material/ListItem"
import ListItemAvatar from "@mui/material/ListItemAvatar"
import ListItemText from "@mui/material/ListItemText"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import ExpandLessIcon from "@mui/icons-material/ExpandLess"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import DisplayGeneral from "./Generals"
import { toGeneralName } from "./general_utils"

import {
  General,
  GeneralFromJSON,
  instanceOfGeneral,
  PlayerStat,
  PlayerStats,
  WinLoss,
} from "./api"
import { Client } from "./Client"
import { winRate, wilsonLowerBound } from "./utils"
import WinRateRadar from "./WinRateRadar"
import WinRateChip, { WinLossVolumeBar } from "./WinRateChip"

const FORMAT_OPTIONS = TEAM_FORMATS
type GameFormat = (typeof FORMAT_OPTIONS)[number]

function fetchPlayerStats(gameFormat: GameFormat): Promise<PlayerStats> {
  const params = gameFormat === "All" ? {} : { gameFormat }
  return Client.getPlayerStatsApiPlayerstatsGet(params)
}

function toGeneral(s: string | number): General {
  let num = typeof s === "string" ? parseInt(s) : s
  if (instanceOfGeneral(num)) {
    return GeneralFromJSON(num)
  }
  return General.NUMBER_MINUS_1
}

const FORMAT_ORDER = ["total", "1v1", "2v2", "3v3", "4v4"]

// Anchor for one player's section, shared by the section and the jump list.
function playerSectionId(name: string): string {
  return `player-${name.replace(/[^a-zA-Z0-9]/g, "-")}`
}

function GameCountsTable(props: { playerStats: PlayerStats }) {
  const [open, setOpen] = React.useState(false)

  const columns = React.useMemo(
    () =>
      FORMAT_ORDER.filter((fmt) =>
        props.playerStats.playerStats.some((s) => s.gameCounts?.[fmt] != null),
      ),
    [props.playerStats.playerStats],
  )

  const rows = React.useMemo(
    () =>
      [...props.playerStats.playerStats].sort(
        (a, b) =>
          (b.gameCounts?.["total"] ?? 0) - (a.gameCounts?.["total"] ?? 0),
      ),
    [props.playerStats.playerStats],
  )

  return (
    <Box sx={{ mb: 2 }}>
      <Paper
        variant="outlined"
        onClick={() => setOpen((v) => !v)}
        sx={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          px: 2,
          py: 1,
          cursor: "pointer",
          userSelect: "none",
          bgcolor: open ? "action.selected" : "action.hover",
          "&:hover": { bgcolor: "action.selected" },
          borderBottomLeftRadius: open ? 0 : undefined,
          borderBottomRightRadius: open ? 0 : undefined,
        }}
      >
        <Typography variant="h6">Game Counts</Typography>
        <Stack
          direction="row"
          spacing={0.5}
          sx={{
            alignItems: "center",
          }}
        >
          <Typography
            variant="caption"
            sx={{
              color: "text.secondary",
            }}
          >
            {open ? "collapse" : "expand"}
          </Typography>
          <IconButton size="small" tabIndex={-1}>
            {open ? <ExpandLessIcon /> : <ExpandMoreIcon />}
          </IconButton>
        </Stack>
      </Paper>
      <Collapse in={open}>
        <TableContainer
          component={Paper}
          variant="outlined"
          sx={{ borderTop: 0, borderTopLeftRadius: 0, borderTopRightRadius: 0 }}
        >
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>
                  <strong>Player</strong>
                </TableCell>
                {columns.map((fmt) => (
                  <TableCell key={fmt} align="right">
                    <strong>{fmt}</strong>
                  </TableCell>
                ))}
              </TableRow>
            </TableHead>
            <TableBody>
              {rows.map((s) => (
                <TableRow key={s.playerName} hover>
                  <TableCell>
                    <PlayerLabel name={s.playerName} />
                  </TableCell>
                  {columns.map((fmt) => (
                    <TableCell key={fmt} align="right">
                      {s.gameCounts?.[fmt] ?? 0}
                    </TableCell>
                  ))}
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </TableContainer>
      </Collapse>
    </Box>
  )
}

function PlayerBanner(props: {
  name: string
  counts: { [key: string]: number } | undefined
  totalWins: number
  totalLosses: number
}) {
  const entries = FORMAT_ORDER.filter(
    (k) => props.counts != null && props.counts[k] != null,
  ).map((k) => [k, props.counts![k]] as const)

  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        flexWrap: "wrap",
        gap: 2,
        px: 2,
        py: 1,
        bgcolor: "action.hover",
        borderRadius: 1,
        mb: 1,
      }}
    >
      <Box sx={{ minWidth: 140 }}>
        <PlayerLabel name={props.name} bold variant="h6" />
      </Box>
      {/* Their record across the generals below. This was behind the admin
          flag, which made the page's own subject unreadable to everyone else:
          a W-L record is public (only rating *levels* are not - see the root
          CLAUDE.md), and without it the section is twelve per-general rates
          with nothing to compare them to. */}
      <WinRateChip
        wins={props.totalWins}
        losses={props.totalLosses}
        size="medium"
      />
      <Stack
        direction="row"
        spacing={1}
        sx={{
          flexWrap: "wrap",
        }}
      >
        {entries.map(([format, count]) => (
          <Chip
            key={format}
            label={`${format}: ${count}`}
            size="small"
            variant={format === "total" ? "filled" : "outlined"}
          />
        ))}
      </Stack>
    </Box>
  )
}

/** One general's row: who it is, how much they played it, how it went.
 *
 * The bar length is the sample. A plain win-rate list draws 100% the same
 * whether it came from two games or fifty, and "great with this general" vs
 * "has barely touched this general" is the distinction most worth seeing
 * before the number underneath it means anything. */
function GeneralRecordRow(props: {
  general: General
  winLoss: WinLoss
  max: number
}) {
  const wins = props.winLoss?.wins ?? 0
  const losses = props.winLoss?.losses ?? 0
  return (
    <ListItem disableGutters dense sx={{ gap: 1.5 }}>
      <ListItemAvatar sx={{ minWidth: 0 }}>
        <DisplayGeneral general={props.general} />
      </ListItemAvatar>
      <ListItemText
        primary={toGeneralName(props.general)}
        sx={{ flex: "0 0 5.5rem", m: 0 }}
      />
      <WinLossVolumeBar wins={wins} losses={losses} max={props.max} />
      <Box sx={{ flexShrink: 0 }}>
        <WinRateChip wins={wins} losses={losses} />
      </Box>
    </ListItem>
  )
}

/**
 * One player's per-general record: how much of each, how it went, and the
 * shape of the whole.
 *
 * Two panels, not the three this used to be. The old middle panel was a
 * vertical wins/losses bar chart whose x labels already carried the win rate,
 * so a general's rate appeared in the list, again on a bar label, and again on
 * the radar. What that chart *did* carry alone was sample size, so the rows on
 * the left now carry it instead: one bar per general, length by games played
 * and split by result, which is the same fact in the place you were already
 * reading the number.
 */
function DisplayPlayerStat(props: { stat: PlayerStat }) {
  const { radarData, total_wins, total_losses, maxGames } =
    React.useMemo(() => {
      let total_wins = 0
      let total_losses = 0
      let maxGames = 0
      const radarData = Object.entries(props.stat.stats).map(
        ([general, winLoss]) => {
          const wins = winLoss?.wins ?? 0
          const losses = winLoss?.losses ?? 0
          total_wins += wins
          total_losses += losses
          maxGames = Math.max(maxGames, wins + losses)
          return {
            name: toGeneralName(toGeneral(general)),
            winRate: Math.round(winRate(wins, losses) * 100),
          }
        },
      )
      return { radarData, total_wins, total_losses, maxGames }
    }, [props.stat])
  return (
    <Box id={playerSectionId(props.stat.playerName)} sx={{ flexGrow: 1 }}>
      <PlayerBanner
        name={props.stat.playerName}
        counts={props.stat.gameCounts}
        totalWins={total_wins}
        totalLosses={total_losses}
      />
      <Grid container spacing={3} sx={{ alignItems: "center" }}>
        <Grid size={{ xs: 12, md: 7 }}>
          <List dense>
            {Object.entries(props.stat.stats).map(([general, winLoss]) => (
              <GeneralRecordRow
                key={general}
                general={toGeneral(general)}
                winLoss={winLoss}
                // Scaled to this player's busiest general rather than a scale
                // shared across the page: per-general counts run from 110 games
                // down to 3, so a global max leaves half the roster with
                // slivers. Absolute counts are on every row's chip.
                max={maxGames}
              />
            ))}
          </List>
        </Grid>
        <Grid size={{ xs: 12, md: 5 }}>
          <WinRateRadar data={radarData} />
        </Grid>
      </Grid>
    </Box>
  )
}

const MIN_GAMES_FOR_BEST = 8

type PlayerConsistency = {
  playerName: string
  spread: number
  bestWinRate: number
  bestGeneral: General
  worstWinRate: number
  worstGeneral: General
  qualifyingCount: number
}

function ConsistencyCard(props: {
  player: PlayerConsistency
  label: string
  emoji: string
  accentColor: string
}) {
  return (
    <Paper variant="outlined" sx={{ p: 2, flex: 1, textAlign: "center" }}>
      <Typography
        variant="subtitle2"
        color={props.accentColor}
        sx={{ mb: 0.5 }}
      >
        {props.emoji} {props.label}
      </Typography>
      <Typography
        variant="h6"
        sx={{
          fontWeight: "bold",
          mb: 0.5,
        }}
      >
        {props.player.playerName}
      </Typography>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
          display: "block",
          mb: 1.5,
        }}
      >
        {props.player.spread * 100 < 1
          ? "<1"
          : (props.player.spread * 100).toFixed(0)}
        % spread across {props.player.qualifyingCount} generals
      </Typography>
      <Stack
        direction="row"
        spacing={3}
        sx={{
          justifyContent: "center",
        }}
      >
        <Stack
          spacing={0.5}
          sx={{
            alignItems: "center",
          }}
        >
          <DisplayGeneral general={props.player.bestGeneral} />
          <Typography
            variant="caption"
            sx={{
              color: "success.main",
            }}
          >
            ▲ {toGeneralName(props.player.bestGeneral)}
          </Typography>
        </Stack>
        <Stack
          spacing={0.5}
          sx={{
            alignItems: "center",
          }}
        >
          <DisplayGeneral general={props.player.worstGeneral} />
          <Typography
            variant="caption"
            sx={{
              color: "error.main",
            }}
          >
            ▼ {toGeneralName(props.player.worstGeneral)}
          </Typography>
        </Stack>
      </Stack>
    </Paper>
  )
}

function RankedPlayerCard(props: {
  general: General
  children: React.ReactNode
}) {
  return (
    <Grid size={{ xs: 6, sm: 4, md: 3, lg: 2 }}>
      <Paper
        sx={{ p: 1, textAlign: "center", height: "100%" }}
        variant="outlined"
      >
        <DisplayGeneral general={props.general} />
        <Typography
          variant="subtitle2"
          sx={{
            display: "block",
            mt: 0.5,
            mb: 0.5,
          }}
        >
          {toGeneralName(props.general)}
        </Typography>
        <Divider sx={{ mb: 0.5 }} />
        {props.children}
      </Paper>
    </Grid>
  )
}

const RANK_MEDALS = ["🥇", "🥈", "🥉"]

function BestPlayerPerGeneral(props: { playerStats: PlayerStats }) {
  type BestEntry = {
    playerName: string
    winRate: number
    wins: number
    losses: number
  }

  const entries = React.useMemo(() => {
    const generalMap = new Map<number, BestEntry[]>()
    for (const stat of props.playerStats.playerStats) {
      for (const [generalStr, winLoss] of Object.entries(stat.stats)) {
        const generalNum = parseInt(generalStr)
        if (generalNum < 0) continue
        const wins = winLoss?.wins ?? 0
        const losses = winLoss?.losses ?? 0
        const total = wins + losses
        if (total < MIN_GAMES_FOR_BEST) continue
        const list = generalMap.get(generalNum) ?? []
        list.push({
          playerName: stat.playerName,
          winRate: winRate(wins, losses),
          wins,
          losses,
        })
        generalMap.set(generalNum, list)
      }
    }
    return Array.from(generalMap.entries())
      .sort((a, b) => a[0] - b[0])
      .map(
        ([generalNum, list]) =>
          [
            generalNum,
            list
              .sort(
                (a, b) =>
                  wilsonLowerBound(b.wins, b.losses) -
                  wilsonLowerBound(a.wins, a.losses),
              )
              .slice(0, 3),
          ] as const,
      )
  }, [props.playerStats])

  return (
    <Box sx={{ mb: 2 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          mb: 1,
        }}
      >
        <Typography variant="h5">Best Player Per General</Typography>
        <Tooltip
          title={`Only players with at least ${MIN_GAMES_FOR_BEST} games on a general are shown, ranked by the lower bound of the 95% Wilson confidence interval (so a well-sampled win rate beats a lucky small one)`}
        >
          <InfoOutlinedIcon
            fontSize="small"
            sx={{ color: "text.secondary", cursor: "default" }}
          />
        </Tooltip>
      </Stack>
      <Grid container spacing={1}>
        {entries.map(([generalNum, topPlayers]) => {
          const general = toGeneral(generalNum)
          return (
            <RankedPlayerCard key={generalNum} general={general}>
              {topPlayers.map((player, rank) => (
                <Box key={player.playerName} sx={{ mt: 0.5 }}>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: rank === 0 ? "bold" : "normal",
                    }}
                  >
                    {RANK_MEDALS[rank]} {player.playerName}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      color: "text.secondary",
                    }}
                  >
                    {(player.winRate * 100).toFixed(0)}% ({player.wins}W-
                    {player.losses}L)
                  </Typography>
                </Box>
              ))}
            </RankedPlayerCard>
          )
        })}
      </Grid>
    </Box>
  )
}

function BestRelativePlayerPerGeneral(props: { playerStats: PlayerStats }) {
  type RelativeEntry = {
    playerName: string
    winRate: number
    overallWinRate: number
    relativeDiff: number
    wins: number
    losses: number
  }

  const entries = React.useMemo(() => {
    const playerOverallRate = new Map<string, number>()
    for (const stat of props.playerStats.playerStats) {
      let totalWins = 0
      let totalGames = 0
      for (const winLoss of Object.values(stat.stats)) {
        totalWins += winLoss?.wins ?? 0
        totalGames += (winLoss?.wins ?? 0) + (winLoss?.losses ?? 0)
      }
      if (totalGames > 0) {
        playerOverallRate.set(stat.playerName, totalWins / totalGames)
      }
    }

    const generalMap = new Map<number, RelativeEntry[]>()
    for (const stat of props.playerStats.playerStats) {
      const overallWinRate = playerOverallRate.get(stat.playerName) ?? 0
      for (const [generalStr, winLoss] of Object.entries(stat.stats)) {
        const generalNum = parseInt(generalStr)
        if (generalNum < 0) continue
        const wins = winLoss?.wins ?? 0
        const losses = winLoss?.losses ?? 0
        const total = wins + losses
        if (total < MIN_GAMES_FOR_BEST) continue
        const wr = winRate(wins, losses)
        const relativeDiff = wr - overallWinRate
        const list = generalMap.get(generalNum) ?? []
        list.push({
          playerName: stat.playerName,
          winRate: wr,
          overallWinRate,
          relativeDiff,
          wins,
          losses,
        })
        generalMap.set(generalNum, list)
      }
    }

    return Array.from(generalMap.entries())
      .sort((a, b) => a[0] - b[0])
      .map(
        ([generalNum, list]) =>
          [
            generalNum,
            list.sort((a, b) => b.relativeDiff - a.relativeDiff).slice(0, 3),
          ] as const,
      )
  }, [props.playerStats])

  return (
    <Box sx={{ mb: 2 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          mb: 1,
        }}
      >
        <Typography variant="h5">
          Best Relative Performance Per General
        </Typography>
        <Tooltip
          title={`Shows which player performs best on each general relative to their own overall win rate. Requires at least ${MIN_GAMES_FOR_BEST} games on that general.`}
        >
          <InfoOutlinedIcon
            fontSize="small"
            sx={{ color: "text.secondary", cursor: "default" }}
          />
        </Tooltip>
      </Stack>
      <Grid container spacing={1}>
        {entries.map(([generalNum, topPlayers]) => {
          const general = toGeneral(generalNum)
          return (
            <RankedPlayerCard key={generalNum} general={general}>
              {topPlayers.map((player, rank) => {
                const diffSign = player.relativeDiff >= 0 ? "+" : ""
                return (
                  <Box key={player.playerName} sx={{ mt: 0.5 }}>
                    <Tooltip
                      title={`Overall win rate: ${(player.overallWinRate * 100).toFixed(0)}%`}
                    >
                      <Typography
                        variant="body2"
                        sx={{
                          fontWeight: rank === 0 ? "bold" : "normal",
                        }}
                      >
                        {RANK_MEDALS[rank]} {player.playerName}
                      </Typography>
                    </Tooltip>
                    <Typography
                      variant="caption"
                      sx={{
                        color: "text.secondary",
                      }}
                    >
                      {(player.winRate * 100).toFixed(0)}% ({player.wins}W-
                      {player.losses}L)
                    </Typography>
                    <Typography
                      variant="caption"
                      color={
                        player.relativeDiff >= 0 ? "success.main" : "error.main"
                      }
                      sx={{
                        display: "block",
                      }}
                    >
                      {diffSign}
                      {(player.relativeDiff * 100).toFixed(0)}% vs their avg
                    </Typography>
                  </Box>
                )
              })}
            </RankedPlayerCard>
          )
        })}
      </Grid>
    </Box>
  )
}

function GeneralConsistency(props: { playerStats: PlayerStats }) {
  const ranked = React.useMemo(() => {
    const rows: PlayerConsistency[] = []
    for (const stat of props.playerStats.playerStats) {
      const qualifying: { general: General; winRate: number }[] = []
      for (const [generalStr, winLoss] of Object.entries(stat.stats)) {
        const generalNum = parseInt(generalStr)
        if (generalNum < 0) continue
        const wins = winLoss?.wins ?? 0
        const losses = winLoss?.losses ?? 0
        const total = wins + losses
        if (total < MIN_GAMES_FOR_BEST) continue
        qualifying.push({
          general: toGeneral(generalNum),
          winRate: winRate(wins, losses),
        })
      }
      if (qualifying.length < 2) continue
      const sorted = qualifying.sort((a, b) => b.winRate - a.winRate)
      const best = sorted[0]
      const worst = sorted[sorted.length - 1]
      rows.push({
        playerName: stat.playerName,
        spread: best.winRate - worst.winRate,
        bestWinRate: best.winRate,
        bestGeneral: best.general,
        worstWinRate: worst.winRate,
        worstGeneral: worst.general,
        qualifyingCount: qualifying.length,
      })
    }
    return rows.sort((a, b) => a.spread - b.spread)
  }, [props.playerStats])

  if (ranked.length < 2) return null

  const mostConsistent = ranked[0]
  const mostVariable = ranked[ranked.length - 1]

  return (
    <Box sx={{ mb: 2 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          mb: 1,
        }}
      >
        <Typography variant="h5">General Consistency</Typography>
        <Tooltip
          title={`Spread between a player's best and worst general win rate. Only generals with at least ${MIN_GAMES_FOR_BEST} games qualify. Players need at least 2 qualifying generals.`}
        >
          <InfoOutlinedIcon
            fontSize="small"
            sx={{ color: "text.secondary", cursor: "default" }}
          />
        </Tooltip>
      </Stack>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
        <ConsistencyCard
          player={mostConsistent}
          label="Most Consistent"
          emoji="🎯"
          accentColor="success.main"
        />
        <ConsistencyCard
          player={mostVariable}
          label="Most Variable"
          emoji="🎲"
          accentColor="error.main"
        />
      </Stack>
    </Box>
  )
}

/**
 * Jump straight to a player's section.
 *
 * The page is one tall section per player in fixed order, so finding yourself
 * on it meant scrolling past everyone above you. These are `PlayerChip`s with
 * navigation turned off: the chip is the app's player identity everywhere
 * else, and here it means "that player, on this page" rather than "that
 * player's profile".
 */
function PlayerJumpList(props: { names: string[] }) {
  return (
    <Stack
      direction="row"
      spacing={0.75}
      useFlexGap
      sx={{ flexWrap: "wrap", alignItems: "center" }}
    >
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Jump to
      </Typography>
      {props.names.map((name) => (
        // A real button, not a div with a handler: this is the page's
        // navigation, so it has to be reachable by keyboard. The chip inside
        // has its own nav turned off, which is what keeps it from being an
        // interactive element nested in one.
        <Box
          component="button"
          type="button"
          key={name}
          aria-label={`Jump to ${name}`}
          onClick={() =>
            document
              .getElementById(playerSectionId(name))
              ?.scrollIntoView({ behavior: "smooth", block: "start" })
          }
          sx={{
            border: 0,
            p: 0,
            bgcolor: "transparent",
            font: "inherit",
            cursor: "pointer",
            borderRadius: 4,
            display: "inline-flex",
          }}
        >
          <PlayerChip name={name} disableNav />
        </Box>
      ))}
    </Stack>
  )
}

export default function DisplayPlayerStats() {
  const [format, setFormat] = React.useState<GameFormat>("All")
  const query = useQuery({
    queryKey: ["playerStats", format],
    queryFn: () => fetchPlayerStats(format),
  })

  // The toggle renders in every state on purpose: a failed load is itself a
  // reason to try another format, so the control must not go away with the data.
  return (
    <Page
      title="Player Stats"
      description="How everyone does with each general, across competitive team games."
      actions={
        <FormatToggle
          label="Game format"
          options={FORMAT_OPTIONS}
          value={format}
          onChange={setFormat}
        />
      }
    >
      <QueryState query={query} what="player stats">
        {(playerStats) => (
          <>
            <PlayerJumpList
              names={playerStats.playerStats.map((s) => s.playerName)}
            />
            <Divider sx={{ my: 2 }} />
            <GameCountsTable playerStats={playerStats} />
            <Divider sx={{ mb: 2 }} />
            <BestPlayerPerGeneral playerStats={playerStats} />
            <Divider sx={{ mb: 2 }} />
            <BestRelativePlayerPerGeneral playerStats={playerStats} />
            <Divider sx={{ mb: 2 }} />
            <GeneralConsistency playerStats={playerStats} />
            <Divider sx={{ mb: 2 }} />
            {playerStats.playerStats.map((m) => (
              <React.Fragment key={m.playerName}>
                <DisplayPlayerStat stat={m} />
                <Divider />
              </React.Fragment>
            ))}
          </>
        )}
      </QueryState>
    </Page>
  )
}
