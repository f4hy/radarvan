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
import CloseIcon from "@mui/icons-material/Close"
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

// Static shape of the fixed 12-entrant double-elimination bracket, mirroring
// the TOPOLOGY in radarvan/bracket.py. This never changes (the bracket is
// always exactly 12 seeded entrants) — it's only used here to lay the tree
// out visually; every actual game result comes from the API response.
type Source =
  | { kind: "seed"; seed: number }
  | { kind: "winner"; matchId: string }
  | { kind: "loser"; matchId: string }

const MATCH_SOURCES: Record<string, [Source, Source]> = {
  "WB1-1": [
    { kind: "seed", seed: 8 },
    { kind: "seed", seed: 9 },
  ],
  "WB1-2": [
    { kind: "seed", seed: 5 },
    { kind: "seed", seed: 12 },
  ],
  "WB1-3": [
    { kind: "seed", seed: 7 },
    { kind: "seed", seed: 10 },
  ],
  "WB1-4": [
    { kind: "seed", seed: 6 },
    { kind: "seed", seed: 11 },
  ],
  "WB2-1": [
    { kind: "seed", seed: 1 },
    { kind: "winner", matchId: "WB1-1" },
  ],
  "WB2-2": [
    { kind: "seed", seed: 4 },
    { kind: "winner", matchId: "WB1-2" },
  ],
  "WB2-3": [
    { kind: "seed", seed: 2 },
    { kind: "winner", matchId: "WB1-3" },
  ],
  "WB2-4": [
    { kind: "seed", seed: 3 },
    { kind: "winner", matchId: "WB1-4" },
  ],
  "WB3-1": [
    { kind: "winner", matchId: "WB2-1" },
    { kind: "winner", matchId: "WB2-2" },
  ],
  "WB3-2": [
    { kind: "winner", matchId: "WB2-3" },
    { kind: "winner", matchId: "WB2-4" },
  ],
  "WB4-1": [
    { kind: "winner", matchId: "WB3-1" },
    { kind: "winner", matchId: "WB3-2" },
  ],
  "LB1-1": [
    { kind: "loser", matchId: "WB1-1" },
    { kind: "loser", matchId: "WB1-2" },
  ],
  "LB1-2": [
    { kind: "loser", matchId: "WB1-3" },
    { kind: "loser", matchId: "WB1-4" },
  ],
  "LB2a-1": [
    { kind: "loser", matchId: "WB2-1" },
    { kind: "loser", matchId: "WB2-2" },
  ],
  "LB2a-2": [
    { kind: "loser", matchId: "WB2-3" },
    { kind: "loser", matchId: "WB2-4" },
  ],
  "LB2b-1": [
    { kind: "winner", matchId: "LB1-1" },
    { kind: "winner", matchId: "LB2a-1" },
  ],
  "LB2b-2": [
    { kind: "winner", matchId: "LB1-2" },
    { kind: "winner", matchId: "LB2a-2" },
  ],
  "LB3-1": [
    { kind: "winner", matchId: "LB2b-1" },
    { kind: "loser", matchId: "WB3-1" },
  ],
  "LB3-2": [
    { kind: "winner", matchId: "LB2b-2" },
    { kind: "loser", matchId: "WB3-2" },
  ],
  "LB4-1": [
    { kind: "winner", matchId: "LB3-1" },
    { kind: "winner", matchId: "LB3-2" },
  ],
  "LB5-1": [
    { kind: "winner", matchId: "LB4-1" },
    { kind: "loser", matchId: "WB4-1" },
  ],
  "GF-1": [
    { kind: "winner", matchId: "WB4-1" },
    { kind: "winner", matchId: "LB5-1" },
  ],
  "GF-2": [
    { kind: "winner", matchId: "WB4-1" },
    { kind: "winner", matchId: "LB5-1" },
  ],
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
  source: Source,
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
  const refMatch = matchesById.get(source.matchId)
  if (refMatch && refMatch.bracket === ownBracket) {
    return buildNode(source.matchId, matchesById, seedToName, ownBracket)
  }
  const playerName = refMatch
    ? source.kind === "winner"
      ? refMatch.winner
      : loserOf(refMatch)
    : null
  return {
    kind: "ref",
    label: `${source.kind === "winner" ? "Winner" : "Loser"} of ${refMatch?.round_name ?? source.matchId}`,
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
  const [sourceA, sourceB] = MATCH_SOURCES[matchId]
  if (!match) {
    return {
      kind: "ref",
      label: matchId,
      playerName: null,
    }
  }
  if (sourceA.kind === "seed" && sourceB.kind === "seed") {
    // Both entrants are raw seeds playing each other directly (Winners
    // Round 1) — nothing earlier to draw, so this is a leaf in the tree.
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
    <Stack direction="row" justifyContent="space-between" alignItems="center">
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
        <Box sx={{ px: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Games played
          </Typography>
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
        </Box>
      )}
      {threshold !== null && gamesPlayed !== null && (
        <Box sx={{ px: 1 }}>
          <Typography variant="caption" color="text.secondary">
            Winner
          </Typography>
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
        </Box>
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
      <Stack direction="row" alignItems="center" justifyContent="space-between">
        <Typography variant="caption" color="text.secondary">
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
        <Typography variant="caption" color="text.secondary">
          {match.scheduled_date}
        </Typography>
      )}
      {notApplicable && (
        <Typography variant="caption" color="text.secondary">
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
        color="text.secondary"
        sx={{ display: "block" }}
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

export default function DisplayBracket() {
  const [bracketData, setBracketData] =
    React.useState<BracketTournamentOutput | null>(null)
  const [eligiblePlayers, setEligiblePlayers] = React.useState<string[]>([])
  const [loading, setLoading] = React.useState(true)
  const [seedNames, setSeedNames] = React.useState<string[]>(DEFAULT_SEEDS)
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

  React.useEffect(() => {
    if (isTournamentAdmin) {
      fetchEligiblePlayers()
        .then(setEligiblePlayers)
        .catch(() => {})
    }
  }, [isTournamentAdmin])

  const handleCreate = async () => {
    setCreating(true)
    try {
      const players: BracketPlayerEntry[] = seedNames.map((name, idx) => ({
        seed: idx + 1,
        player_name: name,
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

  if (!BRACKET_VISIBLE_TO_ALL && !isTournamentAdmin) {
    return (
      <Paper sx={{ p: 2 }}>
        <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 1 }}>
          <EmojiEventsIcon color="primary" />
          <Typography variant="h4">1v1 Tournament Bracket</Typography>
        </Stack>
        <Typography color="text.secondary">
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

  const matchesById = new Map(
    (bracketData?.matches ?? []).map((m) => [m.match_id, m]),
  )
  const seedToName = new Map(
    (bracketData?.players ?? []).map((p) => [p.seed, p.player_name]),
  )
  const winnersTree = bracketData
    ? buildNode("WB4-1", matchesById, seedToName, "W")
    : null
  const losersTree = bracketData
    ? buildNode("LB5-1", matchesById, seedToName, "L")
    : null
  const grandFinalNodes = bracketData
    ? [
        buildNode("GF-1", matchesById, seedToName, "GF"),
        buildNode("GF-2", matchesById, seedToName, "GF"),
      ]
    : []
  const editingMatch = editingMatchId
    ? (matchesById.get(editingMatchId) ?? null)
    : null

  return (
    <Paper sx={{ p: 2 }}>
      <Stack direction="row" alignItems="center" spacing={1} sx={{ mb: 2 }}>
        <EmojiEventsIcon color="primary" />
        <Typography variant="h4">1v1 Tournament Bracket</Typography>
      </Stack>

      {!bracketData && !isTournamentAdmin && (
        <Typography color="text.secondary">
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
              <Stack key={idx} direction="row" spacing={1} alignItems="center">
                <Chip
                  label={`Seed ${idx + 1}`}
                  size="small"
                  sx={{ width: 80 }}
                />
                <Autocomplete
                  options={eligiblePlayers}
                  value={name}
                  onChange={(_e, val) => {
                    if (val !== null) {
                      setSeedNames((prev) => {
                        const next = [...prev]
                        next[idx] = val
                        return next
                      })
                    }
                  }}
                  renderInput={(params) => (
                    <TextField {...params} size="small" label="Player" />
                  )}
                  sx={{ width: 220 }}
                />
              </Stack>
            ))}
            <Button
              variant="contained"
              disabled={creating || new Set(seedNames).size !== 12}
              onClick={handleCreate}
              sx={{ alignSelf: "flex-start" }}
            >
              {bracketData ? "Reset Bracket" : "Create Bracket"}
            </Button>
          </Stack>
        </Paper>
      )}

      {bracketData && winnersTree && losersTree && (
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
                <Typography variant="body2" color="text.secondary">
                  Runner-up: {bracketData.runner_up}
                </Typography>
              )}
            </Paper>
          )}

          <BracketTreeSection
            title="Winners Bracket"
            nodes={[winnersTree]}
            isAdmin={isTournamentAdmin}
            onEdit={(match) => setEditingMatchId(match.match_id)}
          />
          <BracketTreeSection
            title="Losers Bracket"
            nodes={[losersTree]}
            isAdmin={isTournamentAdmin}
            onEdit={(match) => setEditingMatchId(match.match_id)}
          />
          <BracketTreeSection
            title="Grand Final"
            nodes={grandFinalNodes}
            isAdmin={isTournamentAdmin}
            onEdit={(match) => setEditingMatchId(match.match_id)}
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
                <Typography variant="subtitle2" color="text.secondary">
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
