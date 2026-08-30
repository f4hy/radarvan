import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import Alert from "@mui/material/Alert"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import CasinoIcon from "@mui/icons-material/Casino"
import ThumbUpIcon from "@mui/icons-material/ThumbUp"
import BlockIcon from "@mui/icons-material/Block"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import ArrowBackIcon from "@mui/icons-material/ArrowBack"
import GameMap from "./Map"
import Page from "./Page"
import PlayerCountPicker from "./PlayerCountPicker"
import { displayMapName } from "./utils"
import {
  type ChooseMapCandidate,
  type ChooseMapResult,
  chooseMap,
  fetchPlayerCounts,
  fetchVotingPlayers,
} from "./voting"

type Phase = "pick" | "ready" | "reveal" | "spin" | "done"

// Animation timing. Both phases are bounded to a fixed total time so they don't
// balloon when there are lots of maps.
const REVEAL_TOTAL_MS = 1000 // whole vote/veto reveal, regardless of map count
const REVEAL_TO_SPIN_MS = 600
const SPIN_DURATION_MS = 2000 // the spin always lasts this long
const SPIN_LOOPS = 4 // full passes through the maps before landing

// Easing strength (higher = more pronounced acceleration/deceleration).
const REVEAL_EASE_POWER = 3 // reveal starts slow, speeds up
const SPIN_EASE_POWER = 3 // spin starts fast, slows down

// Cumulative reveal progress at item `i` of `count`. Concave so the gaps between
// items shrink as it goes — the reveal starts slow and speeds up.
function revealProgress(i: number, count: number): number {
  return 1 - (1 - i / count) ** REVEAL_EASE_POWER
}

function CandidateRow({
  candidate,
  highlighted,
  winner,
}: {
  candidate: ChooseMapCandidate
  highlighted: boolean
  winner: boolean
}) {
  return (
    <Paper
      variant="outlined"
      sx={{
        p: 1,
        display: "flex",
        alignItems: "center",
        gap: 1,
        opacity: candidate.eligible ? 1 : 0.5,
        transition: "all 120ms",
        borderColor: winner
          ? "warning.main"
          : highlighted
            ? "primary.main"
            : undefined,
        borderWidth: winner || highlighted ? 2 : 1,
        bgcolor: winner
          ? "warning.light"
          : highlighted
            ? "action.selected"
            : undefined,
      }}
    >
      {winner && <EmojiEventsIcon color="warning" />}
      <Typography
        sx={{
          flexGrow: 1,
          fontWeight: winner || highlighted ? 700 : 400,
          // Strike through only maps knocked out of the draw (net score <= 0),
          // not every vetoed map — a veto is -3 votes, not an instant removal.
          textDecoration: candidate.eligible ? undefined : "line-through",
        }}
        noWrap
      >
        {displayMapName(candidate.mapName)}
      </Typography>
      {candidate.recentlyPlayed && (
        <Chip
          size="small"
          color="warning"
          variant="outlined"
          label="played <24h (−8)"
        />
      )}
      <Chip
        size="small"
        color="success"
        variant="outlined"
        icon={<ThumbUpIcon />}
        label={candidate.votes}
      />
      <Chip
        size="small"
        color="error"
        variant={candidate.vetoes > 0 ? "filled" : "outlined"}
        icon={<BlockIcon />}
        label={candidate.vetoes}
      />
    </Paper>
  )
}

export default function ChooseMap() {
  const [selected, setSelected] = React.useState<number | null>(null)
  const [participants, setParticipants] = React.useState<Set<string>>(new Set())
  const [result, setResult] = React.useState<ChooseMapResult | null>(null)
  const [phase, setPhase] = React.useState<Phase>("pick")
  const [revealCount, setRevealCount] = React.useState(0)
  const [spinIndex, setSpinIndex] = React.useState(0)
  const [error, setError] = React.useState<string | null>(null)

  const { data: counts = null } = useQuery({
    queryKey: ["mapVotePlayerCounts"],
    queryFn: fetchPlayerCounts,
  })
  const { data: players = [] } = useQuery({
    queryKey: ["votingPlayers"],
    queryFn: fetchVotingPlayers,
  })

  // Default to everyone selected; the host deselects whoever isn't playing.
  // Seeded once the roster arrives rather than on every render, so a host who
  // has already deselected someone doesn't have it undone underneath them.
  const seeded = React.useRef(false)
  React.useEffect(() => {
    if (!seeded.current && players.length > 0) {
      seeded.current = true
      setParticipants(new Set(players))
    }
  }, [players])

  const toggleParticipant = (name: string) => {
    setParticipants((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const eligible = React.useMemo(
    () => (result?.candidates ?? []).filter((c) => c.eligible) ?? [],
    [result],
  )

  // Progressive reveal of each candidate's votes/vetoes, then hand off to spin.
  // Total reveal is ~REVEAL_TOTAL_MS regardless of map count, and the gap before
  // each item shrinks as it goes (starts slow, speeds up toward the end).
  React.useEffect(() => {
    if (phase !== "reveal" || !result) return
    const count = (result.candidates ?? []).length
    if (revealCount < count) {
      const gap =
        REVEAL_TOTAL_MS *
        (revealProgress(revealCount + 1, count) -
          revealProgress(revealCount, count))
      const t = setTimeout(() => setRevealCount((n) => n + 1), gap)
      return () => clearTimeout(t)
    }
    const t = setTimeout(
      () => setPhase(eligible.length ? "spin" : "done"),
      REVEAL_TO_SPIN_MS,
    )
    return () => clearTimeout(t)
  }, [phase, revealCount, result, eligible.length])

  // Slot-machine spin: a fixed SPIN_DURATION_MS regardless of map count, eased
  // out (fast then slow) so it decelerates onto the backend's chosen map.
  React.useEffect(() => {
    if (phase !== "spin" || !result) return
    if (!eligible.length) {
      setPhase("done")
      return
    }
    const target = Math.max(
      0,
      eligible.findIndex((c) => c.mapName === result.chosenMap),
    )
    // Total index advances; lands on `target` at t=1 (advance % len === target).
    const totalAdvance = eligible.length * SPIN_LOOPS + target
    const start = performance.now()
    let raf = 0
    const frame = (now: number) => {
      const t = Math.min(1, (now - start) / SPIN_DURATION_MS)
      const eased = 1 - (1 - t) ** SPIN_EASE_POWER
      const advance = Math.min(totalAdvance, Math.floor(eased * totalAdvance))
      setSpinIndex(advance % eligible.length)
      if (t >= 1) {
        setPhase("done")
        return
      }
      raf = requestAnimationFrame(frame)
    }
    raf = requestAnimationFrame(frame)
    return () => cancelAnimationFrame(raf)
  }, [phase, result, eligible])

  const draw = async () => {
    if (selected === null || participants.size === 0) return
    setError(null)
    setRevealCount(0)
    setSpinIndex(0)
    try {
      setResult(await chooseMap(selected, [...participants]))
      setPhase("reveal")
    } catch (e) {
      setError(e instanceof Error ? e.message : "Draw failed")
    }
  }

  const reset = (toPick: boolean) => {
    setResult(null)
    setRevealCount(0)
    setSpinIndex(0)
    setPhase(toPick ? "pick" : "ready")
    if (toPick) setSelected(null)
  }

  if (error && counts === null) {
    return (
      <Page title="Choose Map" width="narrow">
        <Alert severity="error">{error}</Alert>
      </Page>
    )
  }

  if (phase === "pick" || selected === null) {
    return (
      <Page
        surface={false}
        title="Choose Map"
        description="Draw tonight's map from what everyone voted for."
      >
        <PlayerCountPicker
          title="How many players?"
          counts={counts ?? []}
          onPick={(c) => {
            setSelected(c)
            setPhase("ready")
          }}
        />
      </Page>
    )
  }

  const revealed =
    phase === "reveal"
      ? ((result?.candidates ?? []).slice(0, revealCount) ?? [])
      : (result?.candidates ?? [])
  const spinning = phase === "spin"
  const spotlightName = spinning
    ? eligible[spinIndex]?.mapName
    : (result?.chosenMap ?? undefined)

  return (
    <Page
      surface={false}
      title={`Choose Map — ${selected} players`}
      description="More votes means better odds. A single veto takes a map out of the draw entirely."
      actions={
        <>
          <Button
            size="small"
            startIcon={<ArrowBackIcon />}
            onClick={() => reset(true)}
          >
            Player count
          </Button>
          {phase === "ready" && (
            <Button
              variant="contained"
              size="large"
              startIcon={<CasinoIcon />}
              onClick={draw}
              disabled={participants.size === 0}
            >
              Reveal votes &amp; draw
            </Button>
          )}
          {phase === "done" && (
            <Button
              variant="outlined"
              startIcon={<CasinoIcon />}
              onClick={() => reset(false)}
            >
              Draw again
            </Button>
          )}
        </>
      }
    >
      <Stack spacing={2}>
        {phase === "ready" && (
          <Stack spacing={1.5}>
            <Alert severity="info">
              Pick who’s playing — only their votes count. Then hit “Reveal
              votes &amp; draw” to spin for a winner (weighted by votes; any
              veto knocks a map out).
            </Alert>
            <Stack
              direction="row"
              spacing={1}
              useFlexGap
              sx={{
                alignItems: "center",
                flexWrap: "wrap",
              }}
            >
              <Typography variant="subtitle2" sx={{ mr: 1 }}>
                Players ({participants.size}/{players.length})
              </Typography>
              <Button
                size="small"
                onClick={() => setParticipants(new Set(players))}
              >
                All
              </Button>
              <Button size="small" onClick={() => setParticipants(new Set())}>
                None
              </Button>
            </Stack>
            {players.length === 0 ? (
              <Alert severity="warning">
                No players have signed in and claimed a name yet, so there are
                no votes to draw from.
              </Alert>
            ) : (
              <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
                {players.map((name) => {
                  const on = participants.has(name)
                  return (
                    <Chip
                      key={name}
                      label={name}
                      color={on ? "primary" : "default"}
                      variant={on ? "filled" : "outlined"}
                      onClick={() => toggleParticipant(name)}
                    />
                  )
                })}
              </Box>
            )}
          </Stack>
        )}
        {error && <Alert severity="error">{error}</Alert>}
        {(spinning || phase === "done") && spotlightName && (
          <Paper
            variant="outlined"
            sx={{
              p: 2,
              textAlign: "center",
              borderColor: phase === "done" ? "warning.main" : "primary.main",
              borderWidth: 2,
            }}
          >
            <Typography
              variant="overline"
              sx={{
                color: "text.secondary",
              }}
            >
              {phase === "done" ? "Winner" : "Drawing…"}
            </Typography>
            <Typography variant="h4" sx={{ fontWeight: 700, mb: 1 }}>
              {displayMapName(spotlightName)}
            </Typography>
            {phase === "done" && (
              <Box sx={{ display: "flex", justifyContent: "center" }}>
                <Box sx={{ maxWidth: 460, width: "100%" }}>
                  <GameMap mapname={spotlightName} />
                </Box>
              </Box>
            )}
          </Paper>
        )}
        {phase === "done" && eligible.length === 0 && (
          <Alert severity="warning">
            No maps were eligible — every voted map was vetoed, or nobody has
            voted yet for {selected} players.
          </Alert>
        )}
        {revealed.length > 0 && (
          <Stack spacing={1}>
            <Typography
              variant="subtitle2"
              sx={{
                color: "text.secondary",
              }}
            >
              {phase === "reveal" ? "Revealing votes…" : "Votes & vetoes"}
            </Typography>
            {revealed.map((c) => (
              <CandidateRow
                key={c.mapName}
                candidate={c}
                highlighted={
                  spinning && eligible[spinIndex]?.mapName === c.mapName
                }
                winner={phase === "done" && result?.chosenMap === c.mapName}
              />
            ))}
          </Stack>
        )}
      </Stack>
    </Page>
  )
}
