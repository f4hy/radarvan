import * as React from "react"
import Autocomplete from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import Dialog from "@mui/material/Dialog"
import DialogContent from "@mui/material/DialogContent"
import DialogTitle from "@mui/material/DialogTitle"
import IconButton from "@mui/material/IconButton"
import Paper from "@mui/material/Paper"
import Slider from "@mui/material/Slider"
import Stack from "@mui/material/Stack"
import TextField from "@mui/material/TextField"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Typography from "@mui/material/Typography"
import { alpha } from "@mui/material/styles"
import AddIcon from "@mui/icons-material/Add"
import CloseIcon from "@mui/icons-material/Close"
import DeleteIcon from "@mui/icons-material/Delete"
import EditIcon from "@mui/icons-material/Edit"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import Loading from "./Loading"
import { useErrorSnackbar } from "./useErrorSnackbar"
import { useIsTournamentAdmin } from "./AuthContext"
import {
  BRAND_COLOR,
  CHART_PALETTE,
  LOSS_COLOR,
  NEUTRAL_COLOR,
  WIN_COLOR,
} from "./theme"
import {
  BracketMatchOutput,
  BracketMatchStatus,
  BracketPlayerEntry,
  BracketTournamentOutput,
  MatchSource,
  SetBracketMatchRequest,
  createBracket,
  fetchBracket,
  fetchEligiblePlayers,
  setBracketMatch,
} from "./bracketApi"

// While the tournament is being set up, only tournament admins (Modus/Gorn)
// can see this page at all — everyone else gets a "not open yet" message and
// the nav item is hidden (see Menu.tsx). Flip this to true to open the
// read-only bracket view up to everyone once it's ready to announce.
export const BRACKET_VISIBLE_TO_ALL = false

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

const BEST_OF_OPTIONS = [3, 5, 7, 9] as const

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
    label: `${source.kind === "winner" ? "Winner" : "Loser"} of ${refMatch?.round_name ?? source.match_id}`,
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

function playerLabel(match: BracketMatchOutput, side: "a" | "b"): string {
  const name = side === "a" ? match.player_a : match.player_b
  if (name) return name
  return match.status === "not_applicable" ? "—" : "TBD"
}

function PlayerRow({
  name,
  score,
  isWinner,
  isLoser,
}: {
  name: string
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
      <Typography
        variant="body2"
        sx={{ fontWeight: isWinner ? 700 : 400, color }}
      >
        {name}
      </Typography>
      {score !== null && (
        <Typography
          variant="body2"
          sx={{ fontWeight: isWinner ? 700 : 400, color, ml: 1 }}
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

function MatchEditor({
  match,
  onSave,
}: {
  match: BracketMatchOutput
  onSave: (req: SetBracketMatchRequest) => Promise<void>
}) {
  const [date, setDate] = React.useState(match.scheduled_date ?? "")
  const [bestOf, setBestOf] = React.useState<number | null>(match.best_of)
  const [gamesPlayed, setGamesPlayed] = React.useState<number | null>(
    match.score_a !== null && match.score_b !== null
      ? match.score_a + match.score_b
      : null,
  )
  const [winnerSide, setWinnerSide] = React.useState<Side | null>(
    match.winner === null ? null : match.winner === match.player_a ? "a" : "b",
  )
  const [saving, setSaving] = React.useState(false)

  const threshold = bestOf !== null ? winThreshold(bestOf) : null

  // The winner always needs exactly `threshold` wins, so games played can
  // never be below that (a sweep) or above `bestOf` (every map played) —
  // reclamp whenever the best-of changes (e.g. Bo7 -> Bo3).
  React.useEffect(() => {
    if (threshold === null || bestOf === null) return
    setGamesPlayed((prev) =>
      prev === null ? prev : Math.min(Math.max(prev, threshold), bestOf),
    )
  }, [threshold, bestOf])

  const loserScore =
    threshold !== null && gamesPlayed !== null ? gamesPlayed - threshold : null
  const scoreA =
    threshold === null || winnerSide === null || loserScore === null
      ? null
      : winnerSide === "a"
        ? threshold
        : loserScore
  const scoreB =
    threshold === null || winnerSide === null || loserScore === null
      ? null
      : winnerSide === "b"
        ? threshold
        : loserScore
  const disabled = saving || scoreA === null || scoreB === null

  const handleSave = async () => {
    setSaving(true)
    try {
      await onSave({
        scheduled_date: date || null,
        best_of: (bestOf as 3 | 5 | 7 | 9 | null) ?? null,
        score_a: scoreA,
        score_b: scoreB,
      })
    } finally {
      setSaving(false)
    }
  }

  return (
    <Stack spacing={2} sx={{ mt: 1.5 }}>
      <TextField
        type="date"
        size="small"
        label="Date"
        slotProps={{ inputLabel: { shrink: true } }}
        value={date}
        onChange={(e) => setDate(e.target.value)}
      />
      <ToggleButtonGroup
        size="small"
        exclusive
        value={bestOf}
        onChange={(_e, val: number | null) => {
          if (val !== null) setBestOf(val)
        }}
      >
        {BEST_OF_OPTIONS.map((bo) => (
          <ToggleButton key={bo} value={bo}>
            Bo{bo}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
      {threshold !== null && bestOf !== null && (
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
      )}
      {threshold !== null && gamesPlayed !== null && (
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

function MatchBox({
  match,
  isAdmin,
  onEdit,
}: {
  match: BracketMatchOutput
  isAdmin: boolean
  onEdit: (match: BracketMatchOutput) => void
}) {
  const notApplicable = match.status === "not_applicable"
  const editable = isAdmin && !notApplicable
  const accent = statusAccent(match.status)
  return (
    <Paper
      variant="outlined"
      onClick={editable ? () => onEdit(match) : undefined}
      sx={{
        p: 1.5,
        minWidth: 210,
        opacity: notApplicable ? 0.5 : 1,
        cursor: editable ? "pointer" : "default",
        position: "relative",
        borderLeft: 4,
        borderLeftColor: accent.border,
        bgcolor: accent.bg,
        "&:hover": editable
          ? {
              borderColor: "primary.main",
              borderLeftColor: accent.border,
              boxShadow: 1,
            }
          : undefined,
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
          sx={{
            color: "text.secondary",
          }}
        >
          {match.round_name}
        </Typography>
        {editable && <EditIcon fontSize="inherit" color="disabled" />}
      </Stack>
      <PlayerRow
        name={playerLabel(match, "a")}
        score={match.score_a}
        isWinner={match.winner !== null && match.winner === match.player_a}
        isLoser={match.winner !== null && match.winner !== match.player_a}
      />
      <PlayerRow
        name={playerLabel(match, "b")}
        score={match.score_b}
        isWinner={match.winner !== null && match.winner === match.player_b}
        isLoser={match.winner !== null && match.winner !== match.player_b}
      />
      {match.scheduled_date && (
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
          }}
        >
          {match.scheduled_date}
        </Typography>
      )}
      {notApplicable && (
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
          }}
        >
          Not needed
        </Typography>
      )}
    </Paper>
  )
}

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
          minWidth: 210,
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
        <Typography variant="body2" sx={{ fontWeight: 700, color: BYE_COLOR }}>
          {node.name}
        </Typography>
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
        minWidth: 210,
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
      <Typography variant="body2">{node.playerName ?? "TBD"}</Typography>
    </Paper>
  )
}

const CONNECTOR_GAP = 24

// Renders one bracket node. A "match" node draws its two children stacked in
// a column (each taking half the column's height) to its left, a connector
// line joining their midpoints to its own midpoint, and its own MatchBox to
// the right — recursing outward toward earlier rounds. This is the standard
// CSS-flexbox tournament-bracket technique: because each child wrapper uses
// flex:1 inside a column with no fixed height, the browser's normal flex
// layout naturally centers a parent between its two children with no pixel
// math, even when the two subtrees have different depths (Losers-bracket
// matches mix same-bracket subtrees with single-leaf cross-bracket refs).
function BracketNodeView({
  node,
  isAdmin,
  onEdit,
}: {
  node: BracketNode
  isAdmin: boolean
  onEdit: (match: BracketMatchOutput) => void
}) {
  if (node.kind !== "match") {
    return <LeafBox node={node} />
  }
  if (node.children === null) {
    return <MatchBox match={node.match} isAdmin={isAdmin} onEdit={onEdit} />
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
          />
        </Box>
        <Box sx={childSlotSx}>
          <BracketNodeView
            node={node.children[1]}
            isAdmin={isAdmin}
            onEdit={onEdit}
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
        <MatchBox match={node.match} isAdmin={isAdmin} onEdit={onEdit} />
      </Box>
    </Box>
  )
}

function BracketTreeSection({
  title,
  nodes,
  isAdmin,
  onEdit,
}: {
  title: string
  nodes: BracketNode[]
  isAdmin: boolean
  onEdit: (match: BracketMatchOutput) => void
}) {
  return (
    <Box sx={{ mb: 4 }}>
      <Typography variant="h6" sx={{ mb: 1.5 }}>
        {title}
      </Typography>
      <Box sx={{ overflowX: "auto", pb: 1 }}>
        <Stack spacing={3} sx={{ width: "fit-content" }}>
          {nodes.map((node, idx) => (
            <BracketNodeView
              key={idx}
              node={node}
              isAdmin={isAdmin}
              onEdit={onEdit}
            />
          ))}
        </Stack>
      </Box>
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
}: {
  matches: BracketMatchOutput[]
  isAdmin: boolean
  onEdit: (match: BracketMatchOutput) => void
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
    <Box sx={{ overflowX: "auto", pb: 1 }}>
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
            </Typography>
            {roundMatches.map((m) => (
              <MatchBox
                key={m.match_id}
                match={m}
                isAdmin={isAdmin}
                onEdit={onEdit}
              />
            ))}
          </Stack>
        ))}
      </Stack>
    </Box>
  )
}

export default function DisplayBracket() {
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
  const isTournamentAdmin = useIsTournamentAdmin()
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    setLoading(true)
    fetchBracket()
      .then(setBracketData)
      .catch(showError)
      .finally(() => setLoading(false))
  }, [showError])

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

  React.useEffect(() => {
    if (isTournamentAdmin) {
      fetchEligiblePlayers()
        .then(setEligiblePlayers)
        .catch(() => {})
    }
  }, [isTournamentAdmin])

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

  if (!BRACKET_VISIBLE_TO_ALL && !isTournamentAdmin) {
    return (
      <Paper sx={{ p: 2 }}>
        <Stack
          direction="row"
          spacing={1}
          sx={{
            alignItems: "center",
            mb: 1,
          }}
        >
          <EmojiEventsIcon color="primary" />
          <Typography variant="h4">1v1 Tournament Bracket</Typography>
        </Stack>
        <Typography
          sx={{
            color: "text.secondary",
          }}
        >
          This page isn&apos;t open yet — check back soon.
        </Typography>
      </Paper>
    )
  }

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

  return (
    <Paper sx={{ p: 2 }}>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          mb: 2,
        }}
      >
        <EmojiEventsIcon color="primary" />
        <Typography variant="h4">1v1 Tournament Bracket</Typography>
      </Stack>
      {!bracketData && !isTournamentAdmin && (
        <Typography
          sx={{
            color: "text.secondary",
          }}
        >
          No tournament has been created yet.
        </Typography>
      )}
      {isTournamentAdmin && (
        <Paper variant="outlined" sx={{ p: 2, mb: 3 }}>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
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
            <Button
              variant="contained"
              disabled={creating || !seedNamesValid}
              onClick={handleCreate}
              sx={{ alignSelf: "flex-start" }}
            >
              {bracketData ? "Reset Bracket" : "Create Bracket"}
            </Button>
          </Stack>
        </Paper>
      )}
      {bracketData && winnersTree && losersMatches.length > 0 && (
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

          <BracketTreeSection
            title="Winners Bracket"
            nodes={[winnersTree]}
            isAdmin={isTournamentAdmin}
            onEdit={handleEdit}
          />
          <Box sx={{ mb: 4 }}>
            <Typography variant="h6" sx={{ mb: 1.5 }}>
              Losers Bracket
            </Typography>
            <LosersBracketColumns
              matches={losersMatches}
              isAdmin={isTournamentAdmin}
              onEdit={handleEdit}
            />
          </Box>
          <BracketTreeSection
            title="Grand Final"
            nodes={grandFinalNodes}
            isAdmin={isTournamentAdmin}
            onEdit={handleEdit}
          />
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
                onSave={(req) => handleSaveMatch(editingMatch.match_id, req)}
              />
            </DialogContent>
          </>
        )}
      </Dialog>
      {errorSnackbar}
    </Paper>
  )
}
