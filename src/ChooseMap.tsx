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
import PlayerCountPicker from "./PlayerCountPicker"
import { displayMapName } from "./utils"
import {
  ChooseMapCandidate,
  ChooseMapResult,
  chooseMap,
  fetchPlayerCounts,
  fetchVotingPlayers,
} from "./voting"

type Phase = "pick" | "ready" | "reveal" | "spin" | "done"

// Reveal cadence (ms) and spin timing — tuned for a slow, dramatic build-up.
const REVEAL_STEP_MS = 550
const REVEAL_TO_SPIN_MS = 900
const SPIN_MIN_LOOPS = 4

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
        {displayMapName(candidate.map_name)}
      </Typography>
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
  const [counts, setCounts] = React.useState<number[] | null>(null)
  const [selected, setSelected] = React.useState<number | null>(null)
  const [players, setPlayers] = React.useState<string[]>([])
  const [participants, setParticipants] = React.useState<Set<string>>(new Set())
  const [result, setResult] = React.useState<ChooseMapResult | null>(null)
  const [phase, setPhase] = React.useState<Phase>("pick")
  const [revealCount, setRevealCount] = React.useState(0)
  const [spinIndex, setSpinIndex] = React.useState(0)
  const [error, setError] = React.useState<string | null>(null)

  React.useEffect(() => {
    fetchPlayerCounts()
      .then(setCounts)
      .catch(() => setError("Could not load player counts"))
    // Default to everyone selected; the host deselects whoever isn't playing.
    fetchVotingPlayers()
      .then((p) => {
        setPlayers(p)
        setParticipants(new Set(p))
      })
      .catch(() => setError("Could not load players"))
  }, [])

  const toggleParticipant = (name: string) => {
    setParticipants((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next
    })
  }

  const eligible = React.useMemo(
    () => result?.candidates.filter((c) => c.eligible) ?? [],
    [result],
  )

  // Progressive reveal of each candidate's votes/vetoes, then hand off to spin.
  React.useEffect(() => {
    if (phase !== "reveal" || !result) return
    if (revealCount < result.candidates.length) {
      const t = setTimeout(() => setRevealCount((n) => n + 1), REVEAL_STEP_MS)
      return () => clearTimeout(t)
    }
    const t = setTimeout(
      () => setPhase(eligible.length ? "spin" : "done"),
      REVEAL_TO_SPIN_MS,
    )
    return () => clearTimeout(t)
  }, [phase, revealCount, result, eligible.length])

  // Slot-machine spin that decelerates and lands on the backend's chosen map.
  React.useEffect(() => {
    if (phase !== "spin" || !result) return
    if (!eligible.length) {
      setPhase("done")
      return
    }
    const target = Math.max(
      0,
      eligible.findIndex((c) => c.map_name === result.chosen_map),
    )
    const totalSteps = eligible.length * SPIN_MIN_LOOPS + target
    let step = 0
    let timer = 0
    const tick = () => {
      setSpinIndex(step % eligible.length)
      if (step >= totalSteps) {
        setPhase("done")
        return
      }
      step++
      timer = window.setTimeout(tick, Math.min(70 + step * 9, 460))
    }
    tick()
    return () => window.clearTimeout(timer)
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
    return <Alert severity="error">{error}</Alert>
  }

  if (phase === "pick" || selected === null) {
    return (
      <PlayerCountPicker
        title="Choose a map — how many players?"
        counts={counts ?? []}
        onPick={(c) => {
          setSelected(c)
          setPhase("ready")
        }}
      />
    )
  }

  const revealed =
    phase === "reveal"
      ? (result?.candidates.slice(0, revealCount) ?? [])
      : (result?.candidates ?? [])
  const spinning = phase === "spin"
  const spotlightName = spinning
    ? eligible[spinIndex]?.map_name
    : (result?.chosen_map ?? undefined)

  return (
    <Stack spacing={2}>
      <Stack direction="row" spacing={1} alignItems="center" flexWrap="wrap">
        <Button
          size="small"
          startIcon={<ArrowBackIcon />}
          onClick={() => reset(true)}
        >
          Player count
        </Button>
        <Typography variant="h6" sx={{ flexGrow: 1 }}>
          {selected}-player map draw
        </Typography>
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
      </Stack>

      {phase === "ready" && (
        <Stack spacing={1.5}>
          <Alert severity="info">
            Pick who’s playing — only their votes count. Then hit “Reveal votes
            &amp; draw” to spin for a winner (weighted by votes; any veto knocks
            a map out).
          </Alert>
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            flexWrap="wrap"
            useFlexGap
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
              No players have signed in and claimed a name yet, so there are no
              votes to draw from.
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
          <Typography variant="overline" color="text.secondary">
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
          <Typography variant="subtitle2" color="text.secondary">
            {phase === "reveal" ? "Revealing votes…" : "Votes & vetoes"}
          </Typography>
          {revealed.map((c) => (
            <CandidateRow
              key={c.map_name}
              candidate={c}
              highlighted={
                spinning && eligible[spinIndex]?.map_name === c.map_name
              }
              winner={phase === "done" && result?.chosen_map === c.map_name}
            />
          ))}
        </Stack>
      )}
    </Stack>
  )
}
