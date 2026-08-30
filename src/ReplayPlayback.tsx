import * as React from "react"
import Box from "@mui/material/Box"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import IconButton from "@mui/material/IconButton"
import Slider from "@mui/material/Slider"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import PlayArrowIcon from "@mui/icons-material/PlayArrow"
import PauseIcon from "@mui/icons-material/Pause"
import ReplayIcon from "@mui/icons-material/Replay"
import GameMap, { type EventDot } from "./Map"
import type { KillEventOutput, MapEventOutput, PlayerSummary } from "./api"
import { buildPlayerColorMap, getColorHex } from "./utils"

// Playback speed as a multiple of real game time: 1x advances the replay at
// the actual pace the match was played (one match-minute per 60 real seconds).
const SPEEDS = [1, 2, 4, 8, 16] as const
const REALTIME_MIN_PER_SEC = 1 / 60
// Kills are momentary: a kill marker is shown for this many match-minutes after
// it happens, then fades out (structures, by contrast, persist).
const KILL_FADE_MIN = 1.2
const TICK_MS = 100

function fmt(minute: number): string {
  const totalSec = Math.max(0, Math.floor(minute * 60))
  const m = Math.floor(totalSec / 60)
  const s = totalSec % 60
  return `${m}:${s.toString().padStart(2, "0")}`
}

// Kill marker size (px) scaled by value destroyed. sqrt keeps cheap units
// readable while letting expensive losses stand out, clamped to a sane range.
function killSize(value: number): number {
  return Math.min(22, Math.max(9, 9 + Math.sqrt(Math.max(0, value)) * 0.26))
}

/**
 * Animated replay of a match on the map image. Structures (builds/captures)
 * appear and persist as the clock advances; kills flash and fade. Driven by a
 * lightweight interval clock with play/pause, speed, and a scrub slider.
 */
export default function ReplayPlayback(props: {
  mapName: string
  mapEvents: MapEventOutput[]
  killEvents: KillEventOutput[]
  playerSummaries: PlayerSummary[]
}) {
  const colors = React.useMemo(
    () => buildPlayerColorMap(props.playerSummaries, getColorHex),
    [props.playerSummaries],
  )

  const maxMinute = React.useMemo(() => {
    let m = 0
    for (const e of props.mapEvents) m = Math.max(m, e.atMinute)
    for (const e of props.killEvents) m = Math.max(m, e.atMinute)
    return m
  }, [props.mapEvents, props.killEvents])

  const [current, setCurrent] = React.useState(0)
  const [playing, setPlaying] = React.useState(false)
  const [speed, setSpeed] = React.useState<number>(4)

  // Advance the clock while playing; stop once we reach the end.
  React.useEffect(() => {
    if (!playing) return
    const id = window.setInterval(() => {
      setCurrent((c) => {
        const next = c + speed * REALTIME_MIN_PER_SEC * (TICK_MS / 1000)
        return next >= maxMinute ? maxMinute : next
      })
    }, TICK_MS)
    return () => window.clearInterval(id)
  }, [playing, speed, maxMinute])

  React.useEffect(() => {
    if (playing && current >= maxMinute) setPlaying(false)
  }, [playing, current, maxMinute])

  const dots: EventDot[] = React.useMemo(() => {
    const out: EventDot[] = []
    // Persistent structures: everything built/captured up to "now".
    for (const e of props.mapEvents) {
      if (e.atMinute > current) continue
      out.push({
        x: e.x,
        y: e.y,
        color: colors[e.playerName] ?? "#888",
        shape: "square",
        size: 6,
        opacity: 0.6,
        // Built structures are subtle (no outline); captures keep a gold border.
        borderColor: e.kind === "capture" ? "#ffd700" : undefined,
        tooltip: `${e.playerName} ${
          e.kind === "capture" ? "captured" : "built"
        } ${e.name} @ ${fmt(e.atMinute)}`,
      })
    }
    // Transient kill flashes within the fade window, dimming with age.
    for (const e of props.killEvents) {
      const age = current - e.atMinute
      if (age < 0 || age > KILL_FADE_MIN) continue
      out.push({
        x: e.x,
        y: e.y,
        color: colors[e.killerPlayer] ?? "#d33",
        shape: "x",
        size: killSize(e.value ?? 0),
        opacity: 0.9 * (1 - age / KILL_FADE_MIN),
        tooltip: `${e.killerPlayer} killed ${e.victimPlayer} (${e.killer} → ${e.victim}${
          e.value ? `, $${e.value}` : ""
        }) @ ${fmt(e.atMinute)}`,
      })
    }
    return out
  }, [props.mapEvents, props.killEvents, colors, current])

  if (maxMinute <= 0) {
    return <Typography>No timed event data for this replay</Typography>
  }

  const structuresShown = props.mapEvents.filter(
    (e) => e.atMinute <= current,
  ).length
  const killsShown = props.killEvents.filter(
    (e) => e.atMinute <= current,
  ).length

  return (
    <Box sx={{ maxWidth: "60%" }}>
      <GameMap mapname={props.mapName} eventDots={dots} />
      <Stack
        direction="row"
        spacing={1.5}
        sx={{
          alignItems: "center",
          mt: 1,
        }}
      >
        <IconButton
          aria-label={playing ? "Pause" : "Play"}
          onClick={() => {
            if (current >= maxMinute) setCurrent(0)
            setPlaying((p) => !p)
          }}
        >
          {playing ? <PauseIcon /> : <PlayArrowIcon />}
        </IconButton>
        <IconButton
          aria-label="Restart"
          onClick={() => {
            setCurrent(0)
            setPlaying(false)
          }}
        >
          <ReplayIcon />
        </IconButton>
        <Slider
          size="small"
          min={0}
          max={maxMinute}
          step={maxMinute / 600}
          value={current}
          valueLabelDisplay="auto"
          valueLabelFormat={(v) => fmt(v)}
          onChange={(_, v) => {
            setPlaying(false)
            setCurrent(v as number)
          }}
          sx={{ flex: 1 }}
        />
        <Typography
          variant="body2"
          sx={{ minWidth: 96, fontVariantNumeric: "tabular-nums" }}
        >
          {fmt(current)} / {fmt(maxMinute)}
        </Typography>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={speed}
          onChange={(_, v) => {
            if (v) setSpeed(v as number)
          }}
        >
          {SPEEDS.map((s) => (
            <ToggleButton key={s} value={s}>
              {s}×
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Stack>
      <Stack direction="row" spacing={2} sx={{ mt: 1, flexWrap: "wrap" }}>
        {props.playerSummaries.map((ps) => (
          <Stack
            key={ps.name}
            direction="row"
            spacing={0.5}
            sx={{
              alignItems: "center",
            }}
          >
            <Box
              sx={{
                width: 12,
                height: 12,
                borderRadius: "2px",
                bgcolor: getColorHex(ps.color),
                flexShrink: 0,
              }}
            />
            <Typography variant="caption">{ps.name}</Typography>
          </Stack>
        ))}
      </Stack>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
        }}
      >
        ■ structures (persist) · ✕ kills (sized by value destroyed) · gold
        border = captured — {structuresShown} structures, {killsShown} kills so
        far
      </Typography>
    </Box>
  )
}
