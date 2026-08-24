import AccountTreeIcon from "@mui/icons-material/AccountTree"
import AddIcon from "@mui/icons-material/Add"
import CloseIcon from "@mui/icons-material/Close"
import CompareArrowsIcon from "@mui/icons-material/CompareArrows"
import DeleteIcon from "@mui/icons-material/Delete"
import EditIcon from "@mui/icons-material/Edit"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import EventNoteIcon from "@mui/icons-material/EventNote"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import GavelIcon from "@mui/icons-material/Gavel"
import MapIcon from "@mui/icons-material/Map"
import PersonIcon from "@mui/icons-material/Person"
import SettingsIcon from "@mui/icons-material/Settings"
import VisibilityIcon from "@mui/icons-material/Visibility"
import WhatshotIcon from "@mui/icons-material/Whatshot"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Autocomplete from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import Dialog from "@mui/material/Dialog"
import DialogActions from "@mui/material/DialogActions"
import DialogContent from "@mui/material/DialogContent"
import DialogTitle from "@mui/material/DialogTitle"
import Divider from "@mui/material/Divider"
import IconButton from "@mui/material/IconButton"
import List from "@mui/material/List"
import ListItem from "@mui/material/ListItem"
import ListItemText from "@mui/material/ListItemText"
import Paper from "@mui/material/Paper"
import Slider from "@mui/material/Slider"
import Stack from "@mui/material/Stack"
import { alpha } from "@mui/material/styles"
import Tab from "@mui/material/Tab"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import Tabs from "@mui/material/Tabs"
import TextField from "@mui/material/TextField"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Typography from "@mui/material/Typography"
import DateTimeField from "./DateTimeField"
import dayjs, { Dayjs } from "dayjs"
import * as React from "react"
import AgendaPanel, { AgendaCountdown, agendaMatches } from "./Agenda"
import { renderAiText, renderBoldSegments } from "./aiText"
import { useIsTournamentAdmin } from "./AuthContext"
import { BracketMatchGames, FactionMatchupOption } from "./api"
import {
  BracketMatchOutput,
  BracketMatchStatus,
  BracketPlayerEntry,
  BracketTournamentOutput,
  createBracket,
  fetchBracket,
  fetchBracketMapRecords,
  fetchEligiblePlayers,
  mapKey,
  MapPlayerRecords,
  MatchSource,
  SetBracketMatchRequest,
  setBracketGames,
  setBracketMatch,
  setBracketRevealAt,
} from "./bracketApi"
import {
  formatCountdown,
  formatScheduledAt,
  playerLabel,
  shortMatchLabel,
  sourceMatchLabel,
  useCountdownMs,
} from "./bracketFormat"
import { BracketClient, Client, CommentaryClient } from "./Client"
import { toGeneralName } from "./general_utils"
import Loading from "./Loading"
import GameMap from "./Map"
import { DisplayMatchInfo } from "./Matches"
import { PlayerChip } from "./PlayerChip"
import { usePlayerAccentColor } from "./PlayerColorsContext"
import {
  BRAND_COLOR,
  CHART_PALETTE,
  LOSS_COLOR,
  NEUTRAL_COLOR,
  WIN_COLOR,
} from "./theme"
import Page from "./Page"
import { useErrorSnackbar } from "./useErrorSnackbar"

const DEFAULT_SEEDS = [
  "Modus",
  "Tytan",
  "WildCard",
  "Gorn",
  "pcap",
  "OneThree111",
  "CoreDawg",
  "Neo",
  "Pancake",
  "Syn",
  "Skip",
  "STM",
]

// The bracket is always a fixed 16-slot shape (more byes for smaller
// fields) — mirrors radarvan/bracket.py's MIN_PLAYERS/MAX_PLAYERS.
const MIN_PLAYERS = 9
const MAX_PLAYERS = 16

const BEST_OF_OPTIONS = [5, 7, 9] as const

// Banner title for the Rules tab — distinct from the (also from
// 1v1_tournament_rules.txt) rule text below it, which is the actual content.
const TOURNAMENT_BANNER_TITLE = "The Third Gamerz Rule 1v1 Tournament"

// Copied verbatim from 1v1_tournament_rules.txt, with **bold** markers added
// around each rule's key point (see renderBoldSegments) so the emphasis
// matches what actually matters when skimming, not just reading top-to-bottom.
const TOURNAMENT_RULES: string[] = [
  "**Random reverse for armies.** Coin flip for who picks map first. Whoever loses the flip **bans one map** from the map pool, map is chosen from remaining options.",
  "**No map may be played on twice in one set.**",
  "**No limit on superweapons.**",
  "**Best of 5**, then **best of 7** for winners semis, winners finals, losers semis, losers finals, then **best of 9** for grand finals.",
  "**Double elimination.**",
  "If set count is even going into final match of the set, the redo coin flip for final map pick, mirror faction based on the person who is higher up in the lobby screen. **Whatever general they get is the one both players will play as for the final game.** The person higher up in the lobby is also the one who calls the coin flip in the air.",
  "If the randomizer gives you a mirror match, play two matches of it that way you don’t mess up the tie breaker system. If both players agree to a gentlemen’s agreement you can reroll generals and get a different matchup.",
  "Tournament admin: **Scottagorn**. Any disputes or rule clarifications go to him.",
]

// Approved map pool for the tournament (also from 1v1_tournament_rules.txt).
const TOURNAMENT_MAP_LIST: string[] = [
  "Dust Devil",
  "[RANK] Barren Badlands Balanced ZH v2",
  "[RANK] TD NoBugsCars ZH v1",
  "[RANK] Arctic Lagoon ZH v2",
  "[RANK] Liquid Gold ZH v2",
  "[RANK] Snowy Drought ZH v5",
  "[RANK] Natural Threats ZH v4",
  "[RANK] Vendetta ZH v1",
  "[RANK] Egyptian Oasis ZH v1",
  "[RANK] Canyon of the Dead ZH v2",
  "Oxygen 1",
]

// A distinct title banner for the Rules tab, separate from the rule content
// below it — was previously just the organizer's plain announcement text.
function TournamentBanner() {
  return (
    <Box
      sx={{
        textAlign: "center",
        py: 2.5,
        mb: 2,
        borderRadius: 1,
        bgcolor: alpha(BRAND_COLOR, 0.08),
        border: "1px solid",
        borderColor: alpha(BRAND_COLOR, 0.3),
      }}
    >
      <Stack
        direction="row"
        spacing={1}
        sx={{ alignItems: "center", justifyContent: "center" }}
      >
        <EmojiEventsIcon sx={{ color: BRAND_COLOR }} />
        <Typography variant="h5" sx={{ fontWeight: 700, color: BRAND_COLOR }}>
          {TOURNAMENT_BANNER_TITLE}
        </Typography>
      </Stack>
    </Box>
  )
}

// The Rules tab content — a title banner plus the numbered rule set, laid
// out as a proper list rather than the plain-text block it started as.
function TournamentRulesPanel() {
  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <TournamentBanner />
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Rules
      </Typography>
      <List sx={{ listStyleType: "decimal", pl: 3 }}>
        {TOURNAMENT_RULES.map((rule, idx) => (
          <ListItem
            key={idx}
            sx={{ display: "list-item", py: 0.5, pl: 0.5 }}
            disableGutters
          >
            <ListItemText primary={renderBoldSegments(rule)} />
          </ListItem>
        ))}
      </List>
    </Paper>
  )
}

// Pool map names by their normalized key, so a record coming back keyed on
// the (lowercased, path-stripped) name stored on a match lines up with the
// pool entry — and is shown with the pool's proper capitalization.
const POOL_NAME_BY_KEY = new Map(
  TOURNAMENT_MAP_LIST.map((name) => [mapKey(name), name]),
)

function recordColor(wins: number, losses: number): string {
  if (wins > losses) return WIN_COLOR
  if (losses > wins) return LOSS_COLOR
  return NEUTRAL_COLOR
}

// Every pool map is listed whether or not it's been played, in the same order
// as the cards above; a map played but not in the pool (shouldn't happen under
// the rules) is appended under whatever name the match recorded.
function mapSections(
  records: MapPlayerRecords[],
): { key: string; name: string; record: MapPlayerRecords | undefined }[] {
  const byKey = new Map(records.map((r) => [r.map_key, r]))
  return [
    ...TOURNAMENT_MAP_LIST.map((name) => ({
      key: mapKey(name),
      name,
      record: byKey.get(mapKey(name)),
    })),
    ...records
      .filter((r) => !POOL_NAME_BY_KEY.has(r.map_key))
      .map((r) => ({ key: r.map_key, name: r.map_name, record: r })),
  ]
}

// Per-map breakdown of who has played it and how they did — e.g. Vendetta:
// Gorn 2–0, Skip 1–1. Driven by the games linked to each bracket match, so it
// tracks whatever an admin has linked/unlinked rather than re-deriving
// membership.
function MapPlayerRecordList() {
  const [records, setRecords] = React.useState<MapPlayerRecords[] | null>(null)
  const [failed, setFailed] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false
    fetchBracketMapRecords()
      .then((res) => {
        if (!cancelled) setRecords(res)
      })
      .catch(() => {
        if (!cancelled) setFailed(true)
      })
    return () => {
      cancelled = true
    }
  }, [])

  if (failed) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Couldn't load map history.
      </Typography>
    )
  }
  if (records === null) return <Loading />
  if (records.length === 0) {
    return (
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        No tournament games have been played yet.
      </Typography>
    )
  }

  return (
    <Stack spacing={1.5} divider={<Divider flexItem />}>
      {mapSections(records).map(({ key, name, record }) => (
        <Box key={key}>
          <Stack direction="row" spacing={1} sx={{ alignItems: "baseline" }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 600 }}>
              {name}
            </Typography>
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {record
                ? `${record.total_games} game${record.total_games === 1 ? "" : "s"}`
                : "not played yet"}
            </Typography>
          </Stack>
          {record && (
            <Stack
              direction="row"
              spacing={1.5}
              useFlexGap
              sx={{ flexWrap: "wrap", alignItems: "center", mt: 0.75 }}
            >
              {record.players.map((p) => (
                <Stack
                  key={p.player}
                  direction="row"
                  spacing={0.5}
                  sx={{ alignItems: "center" }}
                >
                  <PlayerChip name={p.player} />
                  <Typography
                    variant="body2"
                    sx={{
                      color: recordColor(p.wins, p.losses),
                      fontWeight: 600,
                    }}
                  >
                    {p.wins}–{p.losses}
                  </Typography>
                </Stack>
              ))}
            </Stack>
          )}
        </Box>
      ))}
    </Stack>
  )
}

// The Map List tab content — one GameMap card per map in the approved pool,
// plus a collapsed per-map record of who has played each one so far.
function TournamentMapListPanel() {
  return (
    <Stack spacing={2}>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
          gap: 2,
        }}
      >
        {TOURNAMENT_MAP_LIST.map((mapName) => (
          <Stack key={mapName} spacing={1}>
            <GameMap mapname={mapName} />
            <Typography variant="subtitle1" noWrap title={mapName}>
              {mapName}
            </Typography>
          </Stack>
        ))}
      </Box>
      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography sx={{ fontWeight: 600 }}>
            Who's played each map so far
          </Typography>
        </AccordionSummary>
        {/* unmountOnExit (the default) keeps the fetch lazy: the list only
            mounts — and only then hits the API — once someone opens this. */}
        <AccordionDetails>
          <MapPlayerRecordList />
        </AccordionDetails>
      </Accordion>
    </Stack>
  )
}

// Amber accent reserved for bye slots specifically, so they read as visually
// distinct from both "TBD" reference leaves and played/pending real matches.
const BYE_COLOR = CHART_PALETTE[3]

// Left-edge accent + tinted background per match status, so played vs.
// pending vs. ready-to-report is legible at a glance across the whole tree.
function statusAccent(status: BracketMatchStatus): {
  border: string
  bg: string
} {
  switch (status) {
    case "completed":
      return { border: WIN_COLOR, bg: alpha(WIN_COLOR, 0.07) }
    case "ready":
      return { border: BRAND_COLOR, bg: alpha(BRAND_COLOR, 0.06) }
    case "pending":
    case "not_applicable":
      return { border: NEUTRAL_COLOR, bg: "transparent" }
  }
}

// Thicker track/thumb so the sliders read clearly in a compact dialog, with
// a per-slider color so the two controls are visually distinct from each other.
function sliderSx(color: string) {
  return {
    color,
    // Extra top margin clears the always-on value-label bubble so it doesn't
    // overlap the caption above the slider.
    mt: 3,
    "& .MuiSlider-rail": { height: 8, opacity: 0.25 },
    "& .MuiSlider-track": { height: 8 },
    "& .MuiSlider-thumb": { height: 22, width: 22 },
    "& .MuiSlider-mark": { height: 8 },
  } as const
}

type BracketNode =
  | {
      kind: "match"
      match: BracketMatchOutput
      // null for a match whose two slots are both raw seeds (Winners Round 1)
      // — there's no earlier round to draw, it's the tree's leaf level.
      children: [BracketNode, BracketNode] | null
    }
  | { kind: "seed"; seed: number; name: string | undefined }
  | { kind: "ref"; label: string; playerName: string | null }

function loserOf(match: BracketMatchOutput): string | null {
  if (match.winner === null) return null
  return match.winner === match.player_a ? match.player_b : match.player_a
}

// Maps a match's full round_name (as produced by radarvan/bracket.py) to a
// short prefix for card captions / "Winner of ..." references, plus whether
// that round is always exactly one match under the fixed 16-slot bracket
// shape (see bracket.py's build_topology) - those skip the "-a"/"-b" suffix.
function buildChild(
  source: MatchSource,
  matchesById: Map<string, BracketMatchOutput>,
  seedToName: Map<number, string>,
  ownBracket: string,
): BracketNode {
  if (source.kind === "seed") {
    return {
      kind: "seed",
      seed: source.seed,
      name: seedToName.get(source.seed),
    }
  }
  const refMatch = matchesById.get(source.match_id)
  if (refMatch && refMatch.bracket === ownBracket) {
    return buildNode(source.match_id, matchesById, seedToName, ownBracket)
  }
  const playerName = refMatch
    ? source.kind === "winner"
      ? refMatch.winner
      : loserOf(refMatch)
    : null
  return {
    kind: "ref",
    label: `${source.kind === "winner" ? "Winner" : "Loser"} of ${sourceMatchLabel(source.match_id, matchesById)}`,
    playerName,
  }
}

function buildNode(
  matchId: string,
  matchesById: Map<string, BracketMatchOutput>,
  seedToName: Map<number, string>,
  ownBracket: string,
): BracketNode {
  const match = matchesById.get(matchId)
  if (!match) {
    return {
      kind: "ref",
      label: matchId,
      playerName: null,
    }
  }
  const { source_a: sourceA, source_b: sourceB } = match
  if (match.bracket === "W" && match.round_number === 1) {
    // Winners Round 1 is always the tree's true leaf level — nothing
    // earlier to draw. (Can't tell this from "both slots are raw seeds":
    // with enough byes, two bye seeds can also meet directly in a LATER
    // round, e.g. Winners Round 2 at low player counts — that's still a
    // real round with a column of its own, not a leaf.)
    return { kind: "match", match, children: null }
  }
  return {
    kind: "match",
    match,
    children: [
      buildChild(sourceA, matchesById, seedToName, ownBracket),
      buildChild(sourceB, matchesById, seedToName, ownBracket),
    ],
  }
}

// The player's most-played in-game color (via usePlayerAccentColor, backed
// by /api/player_colors/) as a small identity dot — same data PlayerChip
// uses for its avatar fill, just without the avatar's initial-letter chrome
// (too cramped for a dense bracket row).
function ColorDot({ name }: { name: string }) {
  const color = usePlayerAccentColor(name)
  return (
    <Box
      sx={{
        width: 10,
        height: 10,
        borderRadius: "50%",
        bgcolor: color,
        flexShrink: 0,
      }}
    />
  )
}

function PlayerRow({
  name,
  realName,
  score,
  isWinner,
  isLoser,
}: {
  name: string
  // The underlying resolved player name (null for "TBD"/"—" placeholders) -
  // only a real name gets a color dot.
  realName: string | null
  score: number | null
  isWinner: boolean
  isLoser: boolean
}) {
  const color = isWinner ? WIN_COLOR : isLoser ? LOSS_COLOR : "text.primary"
  return (
    <Stack
      direction="row"
      sx={{
        justifyContent: "space-between",
        alignItems: "center",
      }}
    >
      <Stack
        direction="row"
        spacing={0.75}
        sx={{ alignItems: "center", minWidth: 0 }}
      >
        {realName && <ColorDot name={realName} />}
        <Typography
          variant="body2"
          noWrap
          sx={{ fontWeight: isWinner ? 700 : 400, color }}
        >
          {name}
        </Typography>
      </Stack>
      {score !== null && (
        <Typography
          variant="body2"
          sx={{ fontWeight: isWinner ? 700 : 400, color, ml: 1, flexShrink: 0 }}
        >
          {score}
        </Typography>
      )}
    </Stack>
  )
}

// Wins needed to take a best-of-N match — mirrors radarvan/bracket.py's
// win_threshold(). Under standard "stop at clinch" scoring the winner's
// score is always exactly this; only the loser's game count varies.
function winThreshold(bestOf: number): number {
  return Math.floor(bestOf / 2) + 1
}

// Best-of is fixed by the tournament rules per round, not an admin's free
// choice: Bo5 by default, Bo7 for the semis/finals, Bo9 for the grand final.
// The Winners bracket always has exactly these 4 round names (fixed 16-slot
// shape, see bracketApi's DEFAULT_SEEDS comment), so those can be matched by
// name directly. The Losers bracket's round *count* varies with entrant/bye
// count though (5-7 rounds - see bracket.py's build_topology), so "losers
// semis" is derived as whichever round comes immediately before "Losers
// Final" in THIS bracket, not a hardcoded round number.
function expectedBestOf(
  match: BracketMatchOutput,
  allMatches: BracketMatchOutput[],
): 5 | 7 | 9 {
  if (match.bracket === "GF") return 9
  if (match.bracket === "W") {
    return match.round_name === "Winners Semifinal" ||
      match.round_name === "Winners Final"
      ? 7
      : 5
  }
  if (match.round_name === "Losers Final") return 7
  const maxLosersRound = Math.max(
    ...allMatches.filter((m) => m.bracket === "L").map((m) => m.round_number),
  )
  return match.round_number === maxLosersRound - 1 ? 7 : 5
}

type Side = "a" | "b"

function SliderField({
  label,
  children,
}: {
  label: string
  children: React.ReactNode
}) {
  return (
    <Box sx={{ px: 1 }}>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
        }}
      >
        {label}
      </Typography>
      {children}
    </Box>
  )
}

type RankedDraw = {
  playerAGeneral: number
  playerBGeneral: number
  favors: "a" | "b"
  deltaAboveMedian: number
  std: number
}

// The top `count` draws (by probPlayer1Wins) favoring player A, plus the top
// `count` favoring player B (lowest probPlayer1Wins, since player B's win
// prob is 1 - probPlayer1Wins) - four rows total, each expressed as distance
// above the median draw rather than an absolute win probability, so a
// stronger player's generally-higher probabilities don't just fill every
// slot: the median is the same field of 144 draws either perspective ranks
// against, so "above median" isolates what the draw itself is worth.
function topDraws(
  options: FactionMatchupOption[],
  count: number,
): RankedDraw[] {
  if (options.length === 0) return []
  const probs = options.map((o) => o.probPlayer1Wins).sort((a, b) => a - b)
  const mid = Math.floor(probs.length / 2)
  const median =
    probs.length % 2 === 0 ? (probs[mid - 1] + probs[mid]) / 2 : probs[mid]

  const favorsA = [...options]
    .sort((a, b) => b.probPlayer1Wins - a.probPlayer1Wins)
    .slice(0, count)
    .map((o) => ({
      playerAGeneral: o.player1General,
      playerBGeneral: o.player2General,
      favors: "a" as const,
      deltaAboveMedian: o.probPlayer1Wins - median,
      std: o.probPlayer1WinsStd ?? 0,
    }))
  const favorsB = [...options]
    .sort((a, b) => a.probPlayer1Wins - b.probPlayer1Wins)
    .slice(0, count)
    .map((o) => ({
      playerAGeneral: o.player1General,
      playerBGeneral: o.player2General,
      favors: "b" as const,
      deltaAboveMedian: median - o.probPlayer1Wins,
      std: o.probPlayer1WinsStd ?? 0,
    }))
  return [...favorsA, ...favorsB]
}

function BestDrawsList(props: {
  playerA: string
  playerB: string
  draws: RankedDraw[]
}) {
  if (props.draws.length === 0) return null
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>{props.playerA} general</TableCell>
          <TableCell>{props.playerB} general</TableCell>
          <TableCell>Favors</TableCell>
          <TableCell>Confidence</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {props.draws.map((d, i) => {
          const favoredPlayer = d.favors === "a" ? props.playerA : props.playerB
          return (
            <TableRow key={i}>
              <TableCell>{toGeneralName(d.playerAGeneral)}</TableCell>
              <TableCell>{toGeneralName(d.playerBGeneral)}</TableCell>
              <TableCell sx={{ color: "success.main", fontWeight: 600 }}>
                favors {favoredPlayer} +{(d.deltaAboveMedian * 100).toFixed(1)}
                pp
              </TableCell>
              <TableCell sx={{ color: "text.secondary" }}>
                ±{(d.std * 100).toFixed(1)}pp
              </TableCell>
            </TableRow>
          )
        })}
      </TableBody>
    </Table>
  )
}

// Admin-only tail of the matchup popup: link or unlink the games that count
// for this bracket match. `candidates` are games the backend's detector
// recognized but nothing has confirmed - normally empty, non-empty when a
// series was played on a night other than the scheduled one, or when a game
// needs excluding (a warmup between the same two players).
function UnlinkedGames({
  data,
  saving,
  onSetGames,
}: {
  data: BracketMatchGames
  saving: boolean
  onSetGames: (matchIds: number[]) => void
}) {
  const games = data.linked ?? []
  const candidates = data.candidates ?? []
  const linkedIds = games.map((g) => g.id)
  const rows = [
    ...games.map((m) => ({ match: m, linked: true })),
    ...candidates.map((m) => ({ match: m, linked: false })),
  ]
  if (rows.length === 0) return null

  return (
    <Box sx={{ mt: 2, pt: 2, borderTop: "1px solid", borderColor: "divider" }}>
      <Typography
        variant="caption"
        sx={{ color: "text.secondary", display: "block", mb: 1 }}
      >
        🔧 Admin: which games count for this match
      </Typography>
      <Stack spacing={1}>
        {rows.map(({ match: m, linked }) => (
          <Stack
            key={m.id}
            direction="row"
            spacing={1}
            sx={{ alignItems: "center" }}
          >
            <Chip
              size="small"
              color={linked ? "success" : "default"}
              variant={linked ? "filled" : "outlined"}
              label={`#${m.id}`}
            />
            <Typography
              variant="body2"
              sx={{ flexGrow: 1, color: linked ? undefined : "text.secondary" }}
            >
              {new Date(m.timestamp).toLocaleTimeString()} ·{" "}
              {m.durationMinutes.toFixed(0)} min{linked ? "" : " · not linked"}
            </Typography>
            <Button
              size="small"
              disabled={saving}
              onClick={() =>
                onSetGames(
                  linked
                    ? linkedIds.filter((id) => id !== m.id)
                    : [...linkedIds, m.id],
                )
              }
            >
              {linked ? "Remove" : "Add"}
            </Button>
          </Stack>
        ))}
      </Stack>
    </Box>
  )
}

// The tinted panel both AI blurbs render in - the pre-game hype and, once
// the set has been played, the post-game recap. Same shape either way so the
// two read as the same feature at different times.
function CommentaryPanel({ label, text }: { label: string; text: string }) {
  return (
    <Box
      sx={{
        mb: 2,
        p: 1.5,
        borderRadius: 1,
        backgroundColor: (theme) => alpha(theme.palette.secondary.main, 0.08),
        border: "1px solid",
        borderColor: (theme) => alpha(theme.palette.secondary.main, 0.3),
      }}
    >
      <Typography
        variant="caption"
        sx={{ color: "text.secondary", display: "block", mb: 0.5 }}
      >
        {label}
      </Typography>
      {renderAiText(text)}
    </Box>
  )
}

// The everyone-gets-this popup a match card click opens (admins reach the
// score editor via the edit icon instead - see MatchBox). Links to each
// player's profile and their head-to-head record, the AI-generated pre-game
// hype blurb and - once the set is over and every game of it is on record -
// the post-game recap (see radarvan/commentary/), plus whatever 1v1 games
// were actually played between them on the match's scheduled date.
function MatchupPopup({
  match,
  onClose,
  goToPlayerProfile,
  goToHeadToHead,
}: {
  match: BracketMatchOutput
  onClose: () => void
  goToPlayerProfile: (playerName: string) => void
  goToHeadToHead: (player1: string, player2: string) => void
}) {
  const playerA = match.player_a
  const playerB = match.player_b
  const scheduledAt = match.scheduled_at

  const [gamesData, setGamesData] = React.useState<BracketMatchGames | null>(
    null,
  )
  const [saving, setSaving] = React.useState(false)
  const [loading, setLoading] = React.useState(false)
  const games = gamesData?.linked ?? []
  const [commentary, setCommentary] = React.useState<string | null>(null)
  const [commentaryLoading, setCommentaryLoading] = React.useState(false)
  const [summary, setSummary] = React.useState<string | null>(null)
  const [summaryLoading, setSummaryLoading] = React.useState(false)
  const [factionMatchup, setFactionMatchup] = React.useState<
    FactionMatchupOption[] | null
  >(null)
  const { showError, errorSnackbar } = useErrorSnackbar()
  const isTournamentAdmin = useIsTournamentAdmin()

  // No map is known this far ahead of the draw - the endpoint defaults to an
  // "unknown map" placeholder the model handles gracefully - so this is a
  // draw-only signal, not a map-aware one.
  React.useEffect(() => {
    if (!playerA || !playerB) {
      setFactionMatchup(null)
      return
    }
    let cancelled = false
    Client.predictFactionMatchupApiPredictFactionMatchupGet({
      player1: playerA,
      player2: playerB,
    })
      .then((res) => {
        if (!cancelled) setFactionMatchup(res.options)
      })
      .catch(() => {
        // Best-effort like the AI hype below: model unavailable (503) or any
        // other failure just hides the section rather than erroring the popup.
        if (!cancelled) setFactionMatchup(null)
      })
    return () => {
      cancelled = true
    }
  }, [playerA, playerB])

  const bestDraws = React.useMemo(
    () => topDraws(factionMatchup ?? [], 2),
    [factionMatchup],
  )

  React.useEffect(() => {
    if (!playerA || !playerB) {
      setCommentary(null)
      return
    }
    let cancelled = false
    setCommentaryLoading(true)
    CommentaryClient.getMatchupCommentaryApiMatchupCommentaryGet({
      player1: playerA,
      player2: playerB,
      roundName: match.round_name,
    })
      .then((res) => {
        if (!cancelled) setCommentary(res.commentary)
      })
      .catch(() => {
        // Best-effort flavor text: a disabled provider (503) or a
        // generation failure (502) shouldn't break the rest of the popup -
        // just skip showing this section rather than surfacing an error.
        if (!cancelled) setCommentary(null)
      })
      .finally(() => !cancelled && setCommentaryLoading(false))
    return () => {
      cancelled = true
    }
  }, [playerA, playerB, match.round_name])

  // The recap only exists once the set is finished AND every game of it is
  // linked; the backend decides that and answers `ready: false` (free, no
  // model call) until then, so this just asks whenever the set is scored.
  // Re-asks on a score edit, since that changes what "all the games" means.
  const isCompleted = match.status === "completed"
  React.useEffect(() => {
    if (!isCompleted) {
      setSummary(null)
      return
    }
    let cancelled = false
    setSummaryLoading(true)
    CommentaryClient.getBracketSummaryApiBracketSummaryMatchIdGet({
      matchId: match.match_id,
    })
      .then((res) => {
        if (!cancelled) setSummary(res.summary ?? null)
      })
      .catch(() => {
        // Best-effort like the hype above - a 502/503 hides the section
        // rather than erroring the popup.
        if (!cancelled) setSummary(null)
      })
      .finally(() => !cancelled && setSummaryLoading(false))
    return () => {
      cancelled = true
    }
  }, [isCompleted, match.match_id, match.score_a, match.score_b])

  // The games played are a stored fact (the tournament_games link table), not
  // something the client re-derives. The previous version guessed by fetching
  // the night's matches and comparing player names directly, which silently
  // found nothing for anyone whose in-game alias differs from their bracket
  // name (`Grn` vs `Gorn`). The backend resolves aliases and also hands back
  // unconfirmed `candidates` for admins to link.
  React.useEffect(() => {
    let cancelled = false
    setLoading(true)
    BracketClient.getBracketGamesApiBracketGamesMatchIdGet({
      matchId: match.match_id,
    })
      .then((res) => {
        if (!cancelled) setGamesData(res)
      })
      .catch((e) => !cancelled && showError(e))
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
    // scheduledAt/playerA/playerB are inputs to what the backend links, so an
    // in-popup reschedule or score edit (which re-routes players through this
    // slot) has to refetch rather than keep showing the old pairing's games.
  }, [match.match_id, scheduledAt, playerA, playerB, showError])

  const handleLinkGames = React.useCallback(
    (matchIds: number[]) => {
      setSaving(true)
      setBracketGames(match.match_id, matchIds)
        .then(setGamesData)
        .catch(showError)
        .finally(() => setSaving(false))
    },
    [match.match_id, showError],
  )

  const handleGoToPlayer = (playerName: string) => {
    onClose()
    goToPlayerProfile(playerName)
  }
  const handleGoToHeadToHead = () => {
    if (!playerA || !playerB) return
    onClose()
    goToHeadToHead(playerA, playerB)
  }

  return (
    <>
      <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
        <Box sx={{ flexGrow: 1 }}>
          <Typography variant="subtitle2" sx={{ color: "text.secondary" }}>
            {match.round_name}
          </Typography>
          <Typography variant="h6">
            {playerLabel(match, "a")} vs {playerLabel(match, "b")}
          </Typography>
        </Box>
        <IconButton onClick={onClose} size="small">
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent>
        <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", mb: 2 }}>
          {playerA && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<PersonIcon />}
              onClick={() => handleGoToPlayer(playerA)}
            >
              {playerA}&apos;s profile
            </Button>
          )}
          {playerB && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<PersonIcon />}
              onClick={() => handleGoToPlayer(playerB)}
            >
              {playerB}&apos;s profile
            </Button>
          )}
          {playerA && playerB && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<CompareArrowsIcon />}
              onClick={handleGoToHeadToHead}
            >
              Head to Head
            </Button>
          )}
        </Stack>
        {playerA && playerB && bestDraws.length > 0 && (
          <Box sx={{ mb: 2 }}>
            <Typography
              variant="caption"
              sx={{ color: "text.secondary", display: "block", mb: 0.5 }}
            >
              🎲 Best possible draws (model, vs. the field of all general
              pairings)
            </Typography>
            <BestDrawsList
              playerA={playerA}
              playerB={playerB}
              draws={bestDraws}
            />
          </Box>
        )}
        {summaryLoading && (
          <Typography
            variant="caption"
            sx={{ color: "text.secondary", display: "block", mb: 2 }}
          >
            📝 Writing the recap…
          </Typography>
        )}
        {!summaryLoading && summary && (
          <CommentaryPanel label="📝 AI-generated recap" text={summary} />
        )}
        {commentaryLoading && (
          <Typography
            variant="caption"
            sx={{ color: "text.secondary", display: "block", mb: 2 }}
          >
            ✨ Generating hype…
          </Typography>
        )}
        {/* Once the recap exists the hype is history - still worth keeping
            (it's what everyone read beforehand), but folded away so the
            popup leads with what actually happened. */}
        {!commentaryLoading && commentary && summary && (
          <Accordion disableGutters sx={{ mb: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                ✨ The pre-game hype
              </Typography>
            </AccordionSummary>
            <AccordionDetails>{renderAiText(commentary)}</AccordionDetails>
          </Accordion>
        )}
        {!commentaryLoading && commentary && !summary && (
          <CommentaryPanel label="✨ AI-generated hype" text={commentary} />
        )}
        {loading && <Loading />}
        {!loading && games.length === 0 && (
          <Typography sx={{ color: "text.secondary" }}>
            {scheduledAt
              ? `No games recorded for this match on ${new Date(
                  scheduledAt,
                ).toLocaleDateString()}.`
              : "No games played yet."}
          </Typography>
        )}
        {!loading && games.length > 0 && (
          <Stack>
            {games.map((g, idx) => (
              <DisplayMatchInfo key={g.id} match={g} idx={idx} />
            ))}
          </Stack>
        )}
        {!loading && isTournamentAdmin && gamesData && (
          <UnlinkedGames
            data={gamesData}
            saving={saving}
            onSetGames={handleLinkGames}
          />
        )}
        {errorSnackbar}
      </DialogContent>
    </>
  )
}

function MatchEditor({
  match,
  allMatches,
  onSave,
}: {
  match: BracketMatchOutput
  allMatches: BracketMatchOutput[]
  onSave: (req: SetBracketMatchRequest) => Promise<void>
}) {
  // Locked, not admin-editable - see expectedBestOf.
  const bestOf = expectedBestOf(match, allMatches)
  const [gamesPlayed, setGamesPlayed] = React.useState<number | null>(
    match.score_a !== null && match.score_b !== null
      ? match.score_a + match.score_b
      : null,
  )
  const [winnerSide, setWinnerSide] = React.useState<Side | null>(
    match.winner === null ? null : match.winner === match.player_a ? "a" : "b",
  )
  const [saving, setSaving] = React.useState(false)

  const threshold = winThreshold(bestOf)

  // The winner always needs exactly `threshold` wins, so games played can
  // never be below that (a sweep) or above `bestOf` (every map played).
  React.useEffect(() => {
    setGamesPlayed((prev) =>
      prev === null ? prev : Math.min(Math.max(prev, threshold), bestOf),
    )
  }, [threshold, bestOf])

  const loserScore = gamesPlayed !== null ? gamesPlayed - threshold : null
  const scoreA =
    winnerSide === null || loserScore === null
      ? null
      : winnerSide === "a"
        ? threshold
        : loserScore
  const scoreB =
    winnerSide === null || loserScore === null
      ? null
      : winnerSide === "b"
        ? threshold
        : loserScore
  // A score only blocks saving once it's been started but not finished
  // (winner picked with no games-played count yet, or vice versa) - an
  // incomplete score can't be saved, but nothing here forces a score to be
  // entered at all (scheduling now lives on the Agenda tab instead).
  const scoreStarted = winnerSide !== null || gamesPlayed !== null
  const scoreComplete = scoreA !== null && scoreB !== null
  const disabled = saving || (scoreStarted && !scoreComplete)

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave({
        best_of: bestOf,
        score_a: scoreA,
        score_b: scoreB,
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Stack spacing={2} sx={{ mt: 1.5 }}>
      <SliderField label="Best of (fixed by tournament rules for this round)">
        <ToggleButtonGroup size="small" exclusive value={bestOf} disabled>
          {BEST_OF_OPTIONS.map((bo) => (
            <ToggleButton key={bo} value={bo}>
              Bo{bo}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </SliderField>
      <SliderField label="Games played">
        <Slider
          min={threshold}
          max={bestOf}
          step={1}
          marks
          valueLabelDisplay="on"
          value={gamesPlayed ?? threshold}
          onChange={(_e, val) => setGamesPlayed(val as number)}
          sx={sliderSx(BRAND_COLOR)}
        />
      </SliderField>
      {gamesPlayed !== null && (
        <SliderField label="Winner">
          <Slider
            min={0}
            max={gamesPlayed}
            step={null}
            valueLabelDisplay={winnerSide === null ? "off" : "on"}
            marks={[
              {
                value: gamesPlayed - threshold,
                label: `${playerLabel(match, "b")} ${gamesPlayed - threshold}`,
              },
              {
                value: threshold,
                label: `${playerLabel(match, "a")} ${threshold}`,
              },
            ]}
            value={
              winnerSide === "a"
                ? threshold
                : winnerSide === "b"
                  ? gamesPlayed - threshold
                  : (threshold + (gamesPlayed - threshold)) / 2
            }
            sx={sliderSx(WIN_COLOR)}
            onChange={(_e, val) => {
              setWinnerSide(val === threshold ? "a" : "b")
            }}
          />
        </SliderField>
      )}
      {scoreA !== null && scoreB !== null && (
        <Typography variant="body2" sx={{ textAlign: "center" }}>
          {playerLabel(match, "a")} {scoreA} — {scoreB}{" "}
          {playerLabel(match, "b")}
        </Typography>
      )}
      <Button
        size="small"
        variant="contained"
        disabled={disabled}
        onClick={handleSave}
      >
        Save
      </Button>
    </Stack>
  )
}

// Shared by MatchBox/LeafBox (so every card in the tree has the same
// footprint, keeping row heights aligned) and by TreeColumnHeaders, which
// derives its per-round pixel offsets from these same two constants.
const MATCH_BOX_WIDTH = 210
const CONNECTOR_GAP = 24

// Read-only, rarely-changing data every MatchBox needs regardless of its
// depth in the tree - carried via context (like usePlayerAccentColor's
// PlayerColorsContext elsewhere in this file) instead of threaded as props
// through BracketNodeView/BracketTreeSection/LosersBracketColumns, none of
// which otherwise have a reason to know about either field.
type BracketDataValue = {
  matchesById: Map<string, BracketMatchOutput>
  onHoverMatch: (matchId: string | null) => void
  onShowDetails: (match: BracketMatchOutput) => void
}
const BracketDataContext = React.createContext<BracketDataValue | null>(null)
function useBracketData(): BracketDataValue {
  const ctx = React.useContext(BracketDataContext)
  if (!ctx) {
    throw new Error(
      "useBracketData must be used within BracketDataContext.Provider",
    )
  }
  return ctx
}

// Memoized because every hover anywhere in the tree re-renders DisplayBracket
// (hoveredMatchId state) - matchesById/onEdit/onHoverMatch/registerBox are
// all referentially stable across a hover-only update, so without this every
// one of the ~30 match cards would re-render on every mouse movement.
const MatchBox = React.memo(function MatchBox({
  match,
  isAdmin,
  onEdit,
  registerBox,
}: {
  match: BracketMatchOutput
  isAdmin: boolean
  onEdit: (match: BracketMatchOutput) => void
  registerBox?: (matchId: string, el: HTMLElement | null) => void
}) {
  const { matchesById, onHoverMatch, onShowDetails } = useBracketData()
  // "not_applicable" is only ever produced for GF-2 (Grand Final Reset) —
  // resolve_bracket in bracket.py marks it that way whenever GF-1's winner
  // wasn't the Losers Bracket finalist, i.e. no reset is required.
  const notApplicable = match.status === "not_applicable"
  const editable = isAdmin && !notApplicable
  const accent = statusAccent(match.status)
  return (
    <Paper
      ref={(el: HTMLElement | null) => registerBox?.(match.match_id, el)}
      variant="outlined"
      onClick={notApplicable ? undefined : () => onShowDetails(match)}
      onMouseEnter={() => onHoverMatch(match.match_id)}
      onMouseLeave={() => onHoverMatch(null)}
      sx={{
        p: 1.5,
        minWidth: MATCH_BOX_WIDTH,
        opacity: notApplicable ? 0.5 : 1,
        cursor: notApplicable ? "default" : "pointer",
        position: "relative",
        borderLeft: 4,
        borderLeftColor: accent.border,
        bgcolor: accent.bg,
        "&:hover": {
          boxShadow: 1,
          ...(!notApplicable && {
            borderColor: "primary.main",
            borderLeftColor: accent.border,
          }),
        },
      }}
    >
      <Stack
        direction="row"
        sx={{
          alignItems: "center",
          justifyContent: "space-between",
        }}
      >
        <Typography
          variant="caption"
          noWrap
          sx={{
            color: "text.secondary",
            minWidth: 0,
          }}
        >
          <Box component="span" sx={{ fontWeight: 700 }}>
            {shortMatchLabel(match)}
          </Box>
          {match.scheduled_at && ` [${formatScheduledAt(match.scheduled_at)}]`}
        </Typography>
        {editable && (
          <IconButton
            size="small"
            aria-label="Edit match"
            onClick={(e) => {
              e.stopPropagation()
              onEdit(match)
            }}
            sx={{ p: 0.25, ml: 0.5 }}
          >
            <EditIcon fontSize="inherit" />
          </IconButton>
        )}
      </Stack>
      <PlayerRow
        name={playerLabel(match, "a", matchesById)}
        realName={match.player_a}
        score={match.score_a}
        isWinner={match.winner !== null && match.winner === match.player_a}
        isLoser={match.winner !== null && match.winner !== match.player_a}
      />
      <PlayerRow
        name={playerLabel(match, "b", matchesById)}
        realName={match.player_b}
        score={match.score_b}
        isWinner={match.winner !== null && match.winner === match.player_b}
        isLoser={match.winner !== null && match.winner !== match.player_b}
      />
      {notApplicable && (
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
          }}
        >
          Only needed if the Losers Bracket finalist wins the Grand Final
        </Typography>
      )}
    </Paper>
  )
})

// A leaf that isn't a live match — either a bye seed (Winners Round 1) or a
// cross-bracket reference to a match rendered elsewhere (a Losers-bracket
// match citing a Winners-bracket loser, or the Grand Final citing each
// bracket's champion).
function LeafBox({
  node,
}: {
  node: Extract<BracketNode, { kind: "seed" | "ref" }>
}) {
  if (node.kind === "seed") {
    // Bye — same footprint as a real MatchBox (p:1.5, caption + two content
    // rows) so the tree's row heights line up, with the player's name front
    // and center and "Bye" called out underneath.
    return (
      <Paper
        variant="outlined"
        sx={{
          p: 1.5,
          minWidth: MATCH_BOX_WIDTH,
          borderLeft: 4,
          borderLeftColor: BYE_COLOR,
          bgcolor: alpha(BYE_COLOR, 0.08),
        }}
      >
        <Typography
          variant="caption"
          sx={{ display: "block", color: BYE_COLOR }}
        >
          Seed {node.seed}
        </Typography>
        <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
          {node.name && <ColorDot name={node.name} />}
          <Typography
            variant="body2"
            sx={{ fontWeight: 700, color: BYE_COLOR }}
          >
            {node.name}
          </Typography>
        </Stack>
        <Typography variant="body2" sx={{ color: BYE_COLOR }}>
          Bye
        </Typography>
      </Paper>
    )
  }
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1,
        minWidth: MATCH_BOX_WIDTH,
        opacity: 0.6,
        borderLeft: 4,
        borderLeftColor: NEUTRAL_COLOR,
      }}
    >
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
          display: "block",
        }}
      >
        {node.label}
      </Typography>
      <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
        {node.playerName && <ColorDot name={node.playerName} />}
        <Typography variant="body2">{node.playerName ?? "TBD"}</Typography>
      </Stack>
    </Paper>
  )
}

// Renders one bracket node. A "match" node draws its two children stacked in
// a column (each taking half the column's height) to its left, a connector
// line joining their midpoints to its own midpoint, and its own MatchBox to
// the right — recursing outward toward earlier rounds. This is the standard
// CSS-flexbox tournament-bracket technique: because each child wrapper uses
// flex:1 inside a column with no fixed height, the browser's normal flex
// layout naturally centers a parent between its two children with no pixel
// math, even when the two subtrees have different depths (Losers-bracket
// matches mix same-bracket subtrees with single-leaf cross-bracket refs).
const BracketNodeView = React.memo(function BracketNodeView({
  node,
  isAdmin,
  onEdit,
  registerBox,
}: {
  node: BracketNode
  isAdmin: boolean
  onEdit: (match: BracketMatchOutput) => void
  registerBox?: (matchId: string, el: HTMLElement | null) => void
}) {
  if (node.kind !== "match") {
    return <LeafBox node={node} />
  }
  if (node.children === null) {
    return (
      <MatchBox
        match={node.match}
        isAdmin={isAdmin}
        onEdit={onEdit}
        registerBox={registerBox}
      />
    )
  }
  const childSlotSx = {
    flex: 1,
    display: "flex",
    alignItems: "center",
    position: "relative",
    pr: `${CONNECTOR_GAP}px`,
    "&::after": {
      content: '""',
      position: "absolute",
      top: "50%",
      right: 0,
      width: `${CONNECTOR_GAP}px`,
      height: "2px",
      bgcolor: "divider",
    },
  } as const
  return (
    <Box sx={{ display: "flex", alignItems: "stretch" }}>
      <Box
        sx={{ display: "flex", flexDirection: "column", position: "relative" }}
      >
        <Box sx={childSlotSx}>
          <BracketNodeView
            node={node.children[0]}
            isAdmin={isAdmin}
            onEdit={onEdit}
            registerBox={registerBox}
          />
        </Box>
        <Box sx={childSlotSx}>
          <BracketNodeView
            node={node.children[1]}
            isAdmin={isAdmin}
            onEdit={onEdit}
            registerBox={registerBox}
          />
        </Box>
        <Box
          sx={{
            position: "absolute",
            top: "25%",
            bottom: "25%",
            right: 0,
            width: "2px",
            bgcolor: "divider",
          }}
        />
      </Box>
      <Box sx={{ width: `${CONNECTOR_GAP}px` }} />
      <Box sx={{ display: "flex", alignItems: "center" }}>
        <MatchBox
          match={node.match}
          isAdmin={isAdmin}
          onEdit={onEdit}
          registerBox={registerBox}
        />
      </Box>
    </Box>
  )
})

// A section title pinned to the left edge while its bracket area scrolls
// horizontally underneath — the whole bracket (Winners + Losers + Grand
// Final) shares one scroll container so drop/advance connector lines can be
// drawn across sections, so each title needs its own sticky offset rather
// than relying on sitting outside a per-section scrollbox.
function SectionTitle({ children }: { children: React.ReactNode }) {
  return (
    <Typography
      variant="h6"
      sx={{
        mb: 1.5,
        position: "sticky",
        left: 0,
        width: "fit-content",
        bgcolor: "background.paper",
        pr: 2,
      }}
    >
      {children}
    </Typography>
  )
}

// One label per round, left (earliest) to right (latest), positioned above
// a BracketNodeView tree at the same x-offsets the tree itself produces.
// BracketNodeView always nests a match's two children one MATCH_BOX_WIDTH +
// 2*CONNECTOR_GAP to the left of the match's own box (see its width algebra:
// each recursion level adds exactly that stride) — as long as every leaf of
// the tree sits at the same depth (true for the Winners bracket: every
// Winners Round 1 slot, whether a real match or a bye, is a depth-0 leaf),
// that stride is constant across the whole tree, so plain absolute
// positioning lines headers up without measuring the rendered DOM.
const TREE_COLUMN_STRIDE = MATCH_BOX_WIDTH + 2 * CONNECTOR_GAP

function TreeColumnHeaders({ titles }: { titles: string[] }) {
  return (
    <Box sx={{ position: "relative", height: 28, mb: 1 }}>
      {titles.map((title, i) => (
        <Typography
          key={title}
          variant="subtitle2"
          sx={{
            position: "absolute",
            left: i * TREE_COLUMN_STRIDE,
            width: MATCH_BOX_WIDTH,
            color: "text.secondary",
            textAlign: "center",
          }}
        >
          {title}
        </Typography>
      ))}
    </Box>
  )
}

function BracketTreeSection({
  title,
  nodes,
  columnTitles,
  isAdmin,
  onEdit,
  registerBox,
}: {
  title: string
  nodes: BracketNode[]
  // Rendered as a header row above the tree, earliest round first — only
  // meaningful when every node's leaves share one depth (see
  // TREE_COLUMN_STRIDE); omit for trees that mix depths (Grand Final).
  columnTitles?: string[]
  isAdmin: boolean
  onEdit: (match: BracketMatchOutput) => void
  registerBox?: (matchId: string, el: HTMLElement | null) => void
}) {
  return (
    <Box sx={{ mb: 4 }}>
      <SectionTitle>{title}</SectionTitle>
      {columnTitles && <TreeColumnHeaders titles={columnTitles} />}
      <Stack spacing={3} sx={{ width: "fit-content" }}>
        {nodes.map((node, idx) => (
          <BracketNodeView
            key={idx}
            node={node}
            isAdmin={isAdmin}
            onEdit={onEdit}
            registerBox={registerBox}
          />
        ))}
      </Stack>
    </Box>
  )
}

// The Losers bracket isn't a clean power-of-two tree like the Winners
// bracket — reconciliation rounds (`_reduce_to`/`_merge_wave` in bracket.py)
// mean recursion depth from the final doesn't line up with actual round
// number, so the mirrored-tree layout used for Winners/Grand Final puts
// same-round matches at different horizontal positions. Instead, lay the
// Losers bracket out as one column per `round_number` (round 1 leftmost),
// each column stacking that round's matches top to bottom — less compact
// (no connector lines) but the rounds line up left-to-right as expected.
function LosersBracketColumns({
  matches,
  isAdmin,
  onEdit,
  registerBox,
}: {
  matches: BracketMatchOutput[]
  isAdmin: boolean
  onEdit: (match: BracketMatchOutput) => void
  registerBox?: (matchId: string, el: HTMLElement | null) => void
}) {
  const rounds = React.useMemo(() => {
    const byRound = new Map<number, BracketMatchOutput[]>()
    for (const m of matches) {
      const list = byRound.get(m.round_number) ?? []
      list.push(m)
      byRound.set(m.round_number, list)
    }
    return [...byRound.entries()]
      .sort(([a], [b]) => a - b)
      .map(([roundNumber, roundMatches]) => ({
        roundNumber,
        matches: [...roundMatches].sort((a, b) =>
          a.match_id.localeCompare(b.match_id, undefined, { numeric: true }),
        ),
      }))
  }, [matches])

  return (
    <Stack
      direction="row"
      spacing={4}
      sx={{ width: "fit-content", alignItems: "flex-start" }}
    >
      {rounds.map(({ roundNumber, matches: roundMatches }) => (
        <Stack key={roundNumber} spacing={3}>
          <Typography
            variant="subtitle2"
            sx={{ color: "text.secondary", textAlign: "center" }}
          >
            {roundMatches[0]?.round_name ?? `Losers Round ${roundNumber}`}
            {roundMatches[0] &&
              ` (Bo${expectedBestOf(roundMatches[0], matches)})`}
          </Typography>
          {roundMatches.map((m) => (
            <MatchBox
              key={m.match_id}
              match={m}
              isAdmin={isAdmin}
              onEdit={onEdit}
              registerBox={registerBox}
            />
          ))}
        </Stack>
      ))}
    </Stack>
  )
}

// Alphabetical roster (name + the player's usual in-game color, via
// PlayerChip) - replaces the old admin-only seed-picking panel as the thing
// everyone sees on this page. Who's *in* the tournament isn't a spoiler;
// where they land in the bracket is (that's gated by reveal_at instead).
function TournamentRoster({
  names,
  onSelectPlayer,
}: {
  names: string[]
  onSelectPlayer: (playerName: string) => void
}) {
  const sorted = React.useMemo(
    () => [...names].sort((a, b) => a.localeCompare(b)),
    [names],
  )
  return (
    <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
      <Typography variant="subtitle1" sx={{ mb: 1.5 }}>
        Tournament Players
      </Typography>
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
        {sorted.map((name) => (
          <PlayerChip
            key={name}
            name={name}
            onClick={() => onSelectPlayer(name)}
          />
        ))}
      </Stack>
    </Paper>
  )
}

// Uses the shared per-second countdown ticker (own interval, so this tick
// only re-renders this small Paper, not the whole bracket tree above it).
// The actual reveal transition is driven by the backend's `revealed` flag on
// the next poll; this is purely the visible countdown text.
function RevealCountdown({ revealAt }: { revealAt: string }) {
  const remaining = useCountdownMs(revealAt)
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 2,
        mb: 3,
        textAlign: "center",
        borderColor: BRAND_COLOR,
      }}
    >
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Bracket placements reveal in
      </Typography>
      <Typography
        variant="h4"
        sx={{ fontFamily: "monospace", color: BRAND_COLOR }}
      >
        {remaining > 0 ? formatCountdown(remaining) : "any moment now…"}
      </Typography>
    </Paper>
  )
}

// Hero banner for the soonest scheduled match, shown above the tabs so it's
// visible regardless of which tab a visitor lands on (the same escalating
// countdown otherwise only lives inside the Agenda tab, which a casual
// visitor to the Bracket tab would never see). Renders nothing once there's
// no scheduled match to promote - a bare "nothing scheduled yet" banner
// would just be noise, not hype.
function NextMatchBanner({
  bracketData,
  onClick,
}: {
  bracketData: BracketTournamentOutput | null
  onClick: () => void
}) {
  const upcoming = agendaMatches(bracketData)
  const nextMatch = upcoming[0]?.scheduled_at ? upcoming[0] : null
  if (!nextMatch) return null

  return (
    <Paper
      variant="outlined"
      onClick={onClick}
      sx={{
        p: 2,
        mb: 2,
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        flexWrap: "wrap",
        gap: 1.5,
        cursor: "pointer",
        borderColor: BRAND_COLOR,
        bgcolor: (theme) =>
          alpha(BRAND_COLOR, theme.palette.mode === "dark" ? 0.12 : 0.06),
      }}
    >
      <Stack direction="row" spacing={1.5} sx={{ alignItems: "center" }}>
        <WhatshotIcon sx={{ color: BRAND_COLOR }} />
        <Stack spacing={0}>
          <Typography
            variant="overline"
            sx={{ color: "text.secondary", lineHeight: 1.4 }}
          >
            Next match — {nextMatch.round_name}
          </Typography>
          <Typography variant="h6" sx={{ lineHeight: 1.2 }}>
            {playerLabel(nextMatch, "a")} vs {playerLabel(nextMatch, "b")}
          </Typography>
        </Stack>
      </Stack>
      {/* scheduled_at is narrowed non-null by the nextMatch guard above */}
      <AgendaCountdown scheduledAt={nextMatch.scheduled_at as string} />
    </Paper>
  )
}

export default function DisplayBracket({
  goToPlayerProfile,
  goToHeadToHead,
}: {
  goToPlayerProfile: (playerName: string) => void
  goToHeadToHead: (player1: string, player2: string) => void
}) {
  const [bracketData, setBracketData] =
    React.useState<BracketTournamentOutput | null>(null)
  const [eligiblePlayers, setEligiblePlayers] = React.useState<string[]>([])
  const [loading, setLoading] = React.useState(true)
  const [seedNames, setSeedNames] =
    React.useState<(string | null)[]>(DEFAULT_SEEDS)
  const [creating, setCreating] = React.useState(false)
  const [editingMatchId, setEditingMatchId] = React.useState<string | null>(
    null,
  )
  const [detailsMatchId, setDetailsMatchId] = React.useState<string | null>(
    null,
  )
  // Drop/advance lines are only ever drawn for the match currently hovered
  // (both its incoming sources and where its result feeds forward) — showing
  // every line at once was a lot of visual noise on a full bracket.
  const [hoveredMatchId, setHoveredMatchId] = React.useState<string | null>(
    null,
  )
  const isTournamentAdmin = useIsTournamentAdmin()
  const { showError, errorSnackbar } = useErrorSnackbar()
  const [pageTab, setPageTab] = React.useState<
    "bracket" | "rules" | "maps" | "agenda"
  >("bracket")

  // Admin-only "peek early" toggle (see RevealCountdown / the button below).
  // Purely a per-session request flag: it re-fetches /api/bracket with
  // preview=true, which the backend only honors for an authenticated
  // tournament admin — it doesn't move the real reveal_at, so everyone
  // else's view is unaffected.
  const [previewActive, setPreviewActive] = React.useState(false)
  const [adminDialogOpen, setAdminDialogOpen] = React.useState(false)
  const [revealAtInput, setRevealAtInput] = React.useState<Dayjs | null>(null)
  const [savingRevealAt, setSavingRevealAt] = React.useState(false)

  React.useEffect(() => {
    setLoading(true)
    fetchBracket()
      .then(setBracketData)
      .catch(showError)
      .finally(() => setLoading(false))
  }, [showError])

  // Single source of truth for "there's an unrevealed countdown in play" -
  // both the poll effect below and the render gate at the bottom key off
  // this instead of each re-deriving the same condition independently.
  const revealPending =
    bracketData != null &&
    !bracketData.revealed &&
    bracketData.reveal_at != null

  // Once placements are revealed, everyone (not just admins editing scores)
  // needs `bracketData.revealed` to flip from false to true without a manual
  // refresh — the backend is the only clock that matters here, so this
  // schedules a re-fetch at the target time (plus a little slack). If the
  // server still disagrees afterward (clock skew), it falls back to a slow
  // 5s poll rather than retrying every second indefinitely.
  React.useEffect(() => {
    if (!revealPending || !bracketData?.reveal_at) return
    const msUntilTarget = new Date(bracketData.reveal_at).getTime() - Date.now()
    const delay = msUntilTarget > 0 ? msUntilTarget + 1000 : 5000
    const timer = setTimeout(() => {
      fetchBracket(previewActive).then(setBracketData).catch(showError)
    }, delay)
    return () => clearTimeout(timer)
  }, [revealPending, bracketData, previewActive, showError])

  // Keep the create/reset form in sync with whichever tournament is
  // actually active — otherwise editing (e.g. removing a player) operates on
  // the hardcoded defaults instead of the real current roster, so the
  // change doesn't appear to "take" when you reset.
  React.useEffect(() => {
    if (bracketData) {
      setSeedNames(
        [...bracketData.players]
          .sort((a, b) => a.seed - b.seed)
          .map((p) => p.player_name),
      )
    }
  }, [bracketData])

  // Same idea for the reveal-time field, from whatever's actually stored.
  React.useEffect(() => {
    setRevealAtInput(
      bracketData?.reveal_at ? dayjs(bracketData.reveal_at) : null,
    )
  }, [bracketData?.reveal_at])

  React.useEffect(() => {
    if (isTournamentAdmin) {
      fetchEligiblePlayers()
        .then(setEligiblePlayers)
        .catch(() => {})
    }
  }, [isTournamentAdmin])

  // Opening the admin tools implies wanting to see/edit the real roster and
  // seeding, even before the public reveal - so it also switches on preview
  // (same request the "Preview bracket" button makes).
  const handleOpenAdminTools = async () => {
    setAdminDialogOpen(true)
    if (!previewActive) {
      try {
        setBracketData(await fetchBracket(true))
        setPreviewActive(true)
      } catch (e) {
        showError(e)
      }
    }
  }

  const handleTogglePreview = async () => {
    const next = !previewActive
    try {
      setBracketData(await fetchBracket(next))
      setPreviewActive(next)
    } catch (e) {
      showError(e)
    }
  }

  const handleSaveRevealAt = async () => {
    setSavingRevealAt(true)
    try {
      const iso = revealAtInput ? revealAtInput.toISOString() : null
      setBracketData(await setBracketRevealAt({ reveal_at: iso }))
      setPreviewActive(true)
    } catch (e) {
      showError(e)
    } finally {
      setSavingRevealAt(false)
    }
  }

  const seedNamesValid =
    seedNames.length >= MIN_PLAYERS &&
    seedNames.length <= MAX_PLAYERS &&
    seedNames.every((n) => n !== null && n !== "") &&
    new Set(seedNames).size === seedNames.length

  const handleCreate = async () => {
    if (!seedNamesValid) return
    setCreating(true)
    try {
      const players: BracketPlayerEntry[] = seedNames.map((name, idx) => ({
        seed: idx + 1,
        player_name: name as string,
      }))
      setBracketData(await createBracket(players))
      setPreviewActive(true)
    } catch (e) {
      showError(e)
    } finally {
      setCreating(false)
    }
  }

  const handleSaveMatch = React.useCallback(
    async (matchId: string, req: SetBracketMatchRequest) => {
      try {
        setBracketData(await setBracketMatch(matchId, req))
        setEditingMatchId(null)
      } catch (e) {
        showError(e)
      }
    },
    [showError],
  )

  // Shared by every BracketNodeView so opening the edit dialog doesn't need
  // a fresh closure per section (Winners/Losers/Grand Final).
  const handleEdit = React.useCallback(
    (match: BracketMatchOutput) => setEditingMatchId(match.match_id),
    [],
  )

  const handleHoverMatch = React.useCallback(
    (matchId: string | null) => setHoveredMatchId(matchId),
    [],
  )

  // Opens the per-matchup popup (player profile / head-to-head links + that
  // day's games) - this is what a card click does for everyone, admin or
  // not; only the edit icon itself opens the score editor.
  const handleShowDetails = React.useCallback(
    (match: BracketMatchOutput) => setDetailsMatchId(match.match_id),
    [],
  )

  // The recursive tree-building (Winners descent plus the grand-final
  // leaves) only ever depends on bracketData — memoized so it doesn't redo
  // that work on every unrelated re-render (e.g. typing in the seed form).
  // The Losers bracket is laid out separately (see LosersBracketColumns) so
  // it doesn't need a tree at all — just its matches, grouped by round.
  const { matchesById, winnersTree, losersMatches, grandFinalNodes } =
    React.useMemo(() => {
      const matchesById = new Map(
        (bracketData?.matches ?? []).map((m) => [m.match_id, m]),
      )
      const seedToName = new Map(
        (bracketData?.players ?? []).map((p) => [p.seed, p.player_name]),
      )
      // WB4-1/GF-1/GF-2 are safe to hardcode: the bracket is always a fixed
      // 16-slot shape, so the winners bracket always has exactly 4 rounds
      // and the grand final always has exactly these two match ids,
      // regardless of player count or bye count.
      const winnersTree = bracketData
        ? buildNode("WB4-1", matchesById, seedToName, "W")
        : null
      const losersMatches = (bracketData?.matches ?? []).filter(
        (m) => m.bracket === "L",
      )
      const grandFinalNodes = bracketData
        ? [
            buildNode("GF-1", matchesById, seedToName, "GF"),
            buildNode("GF-2", matchesById, seedToName, "GF"),
          ]
        : []
      return { matchesById, winnersTree, losersMatches, grandFinalNodes }
    }, [bracketData])

  // Memoized so BracketDataContext's value stays referentially stable across
  // hover-only re-renders (matchesById/handleHoverMatch/handleShowDetails
  // are all already stable themselves).
  const bracketDataValue = React.useMemo(
    () => ({
      matchesById,
      onHoverMatch: handleHoverMatch,
      onShowDetails: handleShowDetails,
    }),
    [matchesById, handleHoverMatch, handleShowDetails],
  )

  // Dashed connector lines drawn across sections for edges the tree/column
  // layouts above can't show themselves: a loser dropping out of the Winners
  // bracket into the Losers bracket (LOSS_COLOR), and a winner advancing
  // round-to-round within the flat Losers-bracket columns or on into the
  // Grand Final (BRAND_COLOR). Winners-bracket-internal advancement already
  // has its own connector via BracketNodeView's recursion, so this only
  // covers edges where either end touches the Losers bracket.
  const dropConnections = React.useMemo(() => {
    const conns: { id: string; from: string; to: string; color: string }[] = []
    for (const m of bracketData?.matches ?? []) {
      if (m.status === "not_applicable") continue
      for (const source of [m.source_a, m.source_b]) {
        if (source.kind === "seed") continue
        const src = matchesById.get(source.match_id)
        if (!src || (m.bracket !== "L" && src.bracket !== "L")) continue
        conns.push({
          id: `${source.match_id}->${m.match_id}`,
          from: source.match_id,
          to: m.match_id,
          color: source.kind === "loser" ? LOSS_COLOR : BRAND_COLOR,
        })
      }
    }
    return conns
  }, [bracketData, matchesById])

  // ids of the dropConnections touching the currently-hovered match (in
  // either direction) - connectorLines below reuses dropConnections' ids
  // rather than duplicating from/to onto its own geometry entries.
  const hoveredConnectionIds = React.useMemo(
    () =>
      new Set(
        dropConnections
          .filter((c) => c.from === hoveredMatchId || c.to === hoveredMatchId)
          .map((c) => c.id),
      ),
    [dropConnections, hoveredMatchId],
  )

  const boxRefs = React.useRef(new Map<string, HTMLElement>())
  const registerBox = React.useCallback(
    (matchId: string, el: HTMLElement | null) => {
      if (el) boxRefs.current.set(matchId, el)
      else boxRefs.current.delete(matchId)
    },
    [],
  )
  const bracketAreaRef = React.useRef<HTMLDivElement>(null)
  const [connectorLines, setConnectorLines] = React.useState<
    {
      id: string
      x1: number
      y1: number
      x2: number
      y2: number
      color: string
    }[]
  >([])

  // Recompute connector pixel coordinates whenever the bracket's DOM layout
  // changes. ResizeObserver delivers an initial callback as soon as observe()
  // is called (even if size is unchanged), so re-subscribing on every
  // bracketData change also covers "same size, different matches" edits —
  // not just actual resizes.
  React.useEffect(() => {
    const container = bracketAreaRef.current
    if (!container) return
    const recompute = () => {
      const containerRect = container.getBoundingClientRect()
      const next: typeof connectorLines = []
      for (const conn of dropConnections) {
        const fromEl = boxRefs.current.get(conn.from)
        const toEl = boxRefs.current.get(conn.to)
        if (!fromEl || !toEl) continue
        const fromRect = fromEl.getBoundingClientRect()
        const toRect = toEl.getBoundingClientRect()
        next.push({
          id: conn.id,
          x1: fromRect.right - containerRect.left,
          y1: fromRect.top + fromRect.height / 2 - containerRect.top,
          x2: toRect.left - containerRect.left,
          y2: toRect.top + toRect.height / 2 - containerRect.top,
          color: conn.color,
        })
      }
      setConnectorLines(next)
    }
    const observer = new ResizeObserver(recompute)
    observer.observe(container)
    return () => observer.disconnect()
  }, [dropConnections])

  if (loading) {
    return (
      <>
        <Loading />
        {errorSnackbar}
      </>
    )
  }

  const editingMatch = editingMatchId
    ? (matchesById.get(editingMatchId) ?? null)
    : null
  const detailsMatch = detailsMatchId
    ? (matchesById.get(detailsMatchId) ?? null)
    : null

  const bracketAdminView = isTournamentAdmin && (bracketData?.revealed ?? false)

  return (
    <Page
      title="1v1 Bracket"
      description="Who plays who next, what has already been decided, and the rules."
      actions={
        <>
          {isTournamentAdmin && bracketData && !bracketData.revealed && (
            <Button
              size="small"
              variant={previewActive ? "contained" : "outlined"}
              startIcon={<VisibilityIcon />}
              onClick={handleTogglePreview}
            >
              {previewActive
                ? "Previewing (admin only)"
                : "Preview bracket (admin only)"}
            </Button>
          )}
          {isTournamentAdmin && (
            <IconButton
              size="small"
              aria-label="Tournament admin tools"
              onClick={handleOpenAdminTools}
            >
              <SettingsIcon fontSize="small" />
            </IconButton>
          )}
        </>
      }
    >
      <NextMatchBanner
        bracketData={bracketData}
        onClick={() => setPageTab("agenda")}
      />
      <Tabs value={pageTab} onChange={(_e, v) => setPageTab(v)} sx={{ mb: 2 }}>
        <Tab
          value="bracket"
          label="Bracket"
          icon={<AccountTreeIcon />}
          iconPosition="start"
        />
        <Tab
          value="agenda"
          label="Agenda"
          icon={<EventNoteIcon />}
          iconPosition="start"
        />
        <Tab
          value="rules"
          label="Rules"
          icon={<GavelIcon />}
          iconPosition="start"
        />
        <Tab
          value="maps"
          label="Map List"
          icon={<MapIcon />}
          iconPosition="start"
        />
      </Tabs>
      {pageTab === "rules" && <TournamentRulesPanel />}
      {pageTab === "maps" && <TournamentMapListPanel />}
      {pageTab === "agenda" && (
        <AgendaPanel
          bracketData={bracketData}
          onSchedule={(matchId, scheduledAt) =>
            handleSaveMatch(matchId, { scheduled_at: scheduledAt })
          }
        />
      )}
      {pageTab === "bracket" && !bracketData && (
        <Typography
          sx={{
            color: "text.secondary",
          }}
        >
          No tournament has been created yet.
          {isTournamentAdmin && " Use the settings icon above to create one."}
        </Typography>
      )}
      {pageTab === "bracket" && bracketData && (
        <TournamentRoster
          names={bracketData.participant_names}
          onSelectPlayer={goToPlayerProfile}
        />
      )}
      {pageTab === "bracket" &&
        revealPending &&
        bracketData &&
        bracketData.reveal_at && (
          <RevealCountdown revealAt={bracketData.reveal_at} />
        )}
      <Dialog
        open={adminDialogOpen}
        onClose={() => setAdminDialogOpen(false)}
        maxWidth="xs"
        fullWidth
      >
        <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
          <Box sx={{ flexGrow: 1 }}>Tournament admin</Box>
          <IconButton onClick={() => setAdminDialogOpen(false)} size="small">
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent>
          <Stack spacing={1}>
            <Typography variant="subtitle2">Reveal time</Typography>
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              Player placements stay hidden from everyone until this time
              (server clock). Leave blank to show the bracket immediately.
            </Typography>
            <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
              <DateTimeField
                value={revealAtInput}
                onChange={(newValue) => setRevealAtInput(newValue)}
                slotProps={{ textField: { size: "small" } }}
              />
              <Button
                size="small"
                variant="contained"
                disabled={savingRevealAt}
                onClick={handleSaveRevealAt}
              >
                Save
              </Button>
            </Stack>
          </Stack>
          <Typography variant="subtitle1" sx={{ mt: 3, mb: 1 }}>
            {bracketData ? "Reset Tournament" : "Create Tournament"}
          </Typography>
          <Stack spacing={1}>
            {seedNames.map((name, idx) => (
              <Stack
                key={idx}
                direction="row"
                spacing={1}
                sx={{
                  alignItems: "center",
                }}
              >
                <Chip
                  label={`Seed ${idx + 1}`}
                  size="small"
                  sx={{ width: 80 }}
                />
                <Autocomplete
                  options={eligiblePlayers}
                  value={name}
                  onChange={(_e, val) => {
                    setSeedNames((prev) => {
                      const next = [...prev]
                      next[idx] = val
                      return next
                    })
                  }}
                  renderInput={(params) => (
                    <TextField {...params} size="small" label="Player" />
                  )}
                  sx={{ width: 220 }}
                />
                <IconButton
                  size="small"
                  disabled={seedNames.length <= MIN_PLAYERS}
                  onClick={() =>
                    setSeedNames((prev) => prev.filter((_, i) => i !== idx))
                  }
                >
                  <DeleteIcon fontSize="small" />
                </IconButton>
              </Stack>
            ))}
            <Button
              startIcon={<AddIcon />}
              disabled={seedNames.length >= MAX_PLAYERS}
              onClick={() => setSeedNames((prev) => [...prev, null])}
              sx={{ alignSelf: "flex-start" }}
            >
              Add player
            </Button>
          </Stack>
        </DialogContent>
        <DialogActions>
          <Button
            variant="contained"
            disabled={creating || !seedNamesValid}
            onClick={handleCreate}
          >
            {bracketData ? "Reset Bracket" : "Create Bracket"}
          </Button>
        </DialogActions>
      </Dialog>
      {pageTab === "bracket" &&
        bracketData &&
        winnersTree &&
        losersMatches.length > 0 && (
          <>
            {bracketData.champion && (
              <Paper
                variant="outlined"
                sx={{ p: 2, mb: 3, borderColor: WIN_COLOR }}
              >
                <Typography variant="h6" sx={{ color: WIN_COLOR }}>
                  Champion: {bracketData.champion}
                </Typography>
                {bracketData.runner_up && (
                  <Typography
                    variant="body2"
                    sx={{
                      color: "text.secondary",
                    }}
                  >
                    Runner-up: {bracketData.runner_up}
                  </Typography>
                )}
              </Paper>
            )}

            <Box sx={{ overflowX: "auto", pb: 1 }}>
              <Box
                ref={bracketAreaRef}
                sx={{ position: "relative", width: "fit-content" }}
              >
                <Box
                  component="svg"
                  sx={{
                    position: "absolute",
                    inset: 0,
                    width: "100%",
                    height: "100%",
                    overflow: "visible",
                    pointerEvents: "none",
                  }}
                >
                  {connectorLines
                    .filter((line) => hoveredConnectionIds.has(line.id))
                    .map((line) => {
                      // Smooth S-curve (cubic Bezier) instead of a straight
                      // diagonal or an elbow — both control points sit on the
                      // horizontal midline so the curve leaves/arrives roughly
                      // level at each end regardless of how far apart the rows are.
                      const midX = (line.x1 + line.x2) / 2
                      const d = `M ${line.x1} ${line.y1} C ${midX} ${line.y1}, ${midX} ${line.y2}, ${line.x2} ${line.y2}`
                      return (
                        <path
                          key={line.id}
                          d={d}
                          fill="none"
                          stroke={line.color}
                          strokeWidth={1.5}
                          strokeDasharray="5 4"
                          opacity={0.7}
                        />
                      )
                    })}
                </Box>
                <Box sx={{ position: "relative" }}>
                  <BracketDataContext.Provider value={bracketDataValue}>
                    <BracketTreeSection
                      title="Winners Bracket"
                      nodes={[winnersTree]}
                      columnTitles={[
                        "Winners Round 1 (Bo5)",
                        "Winners Round 2 (Bo5)",
                        "Winners Semifinal (Bo7)",
                        "Winners Final (Bo7)",
                      ]}
                      isAdmin={bracketAdminView}
                      onEdit={handleEdit}
                      registerBox={registerBox}
                    />
                    <Box sx={{ mb: 4 }}>
                      <SectionTitle>Losers Bracket</SectionTitle>
                      <LosersBracketColumns
                        matches={losersMatches}
                        isAdmin={bracketAdminView}
                        onEdit={handleEdit}
                        registerBox={registerBox}
                      />
                    </Box>
                    <BracketTreeSection
                      title="👑 Grand Final (Bo9)"
                      nodes={grandFinalNodes}
                      isAdmin={bracketAdminView}
                      onEdit={handleEdit}
                      registerBox={registerBox}
                    />
                  </BracketDataContext.Provider>
                </Box>
              </Box>
            </Box>
          </>
        )}
      <Dialog
        open={editingMatch !== null}
        onClose={() => setEditingMatchId(null)}
        maxWidth="xs"
        fullWidth
      >
        {editingMatch && (
          <>
            <DialogTitle sx={{ display: "flex", alignItems: "center", gap: 1 }}>
              <Box sx={{ flexGrow: 1 }}>
                <Typography
                  variant="subtitle2"
                  sx={{
                    color: "text.secondary",
                  }}
                >
                  {editingMatch.round_name}
                </Typography>
                <Typography variant="h6">
                  {playerLabel(editingMatch, "a")} vs{" "}
                  {playerLabel(editingMatch, "b")}
                </Typography>
              </Box>
              <IconButton onClick={() => setEditingMatchId(null)} size="small">
                <CloseIcon />
              </IconButton>
            </DialogTitle>
            <DialogContent>
              <MatchEditor
                match={editingMatch}
                allMatches={bracketData?.matches ?? []}
                onSave={(req) => handleSaveMatch(editingMatch.match_id, req)}
              />
            </DialogContent>
          </>
        )}
      </Dialog>
      <Dialog
        open={detailsMatch !== null}
        onClose={() => setDetailsMatchId(null)}
        maxWidth="lg"
        fullWidth
      >
        {detailsMatch && (
          <MatchupPopup
            match={detailsMatch}
            onClose={() => setDetailsMatchId(null)}
            goToPlayerProfile={goToPlayerProfile}
            goToHeadToHead={goToHeadToHead}
          />
        )}
      </Dialog>
      {errorSnackbar}
    </Page>
  )
}
