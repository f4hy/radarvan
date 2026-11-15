import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import Stack from "@mui/material/Stack"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TextField from "@mui/material/TextField"
import Typography from "@mui/material/Typography"
import { useTheme } from "@mui/material/styles"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Scatter,
  ScatterChart,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts"
import { matchNetstatsApiAdminMatchMatchIdNetstatsGetOptions } from "../../api/@tanstack/react-query.gen"
import type { MatchNetstats, PlayerNetstats } from "../../api/types.gen"
import Page from "../../components/Page"
import { queryFallback } from "../../components/QueryState"
import { useUrlParam } from "../../lib/useUrlState"

// Eight categorical hues, ordered so neighbours stay apart under colour-blind
// simulation; one set per colour mode since recharts can't read the theme.
const SLOT_COLORS = {
  light: [
    "#2a78d6",
    "#eb6834",
    "#1baf7a",
    "#eda100",
    "#e87ba4",
    "#008300",
    "#6250d6",
    "#e34948",
  ],
  dark: [
    "#3987e5",
    "#d95926",
    "#199e70",
    "#c98500",
    "#d55181",
    "#0ca30c",
    "#9085e9",
    "#e66767",
  ],
}
const FPS = 60
const FRAME_BUDGET_MS = 1000 / FPS
const WINDOW_SECONDS = 10

const mmss = (s: number) =>
  `${Math.floor(s / 60)}:${String(Math.round(s % 60)).padStart(2, "0")}`

type Row = { t: number } & Record<string, number>

// One row per 10 s window, one column per player, so a single tooltip can list
// everyone. Each client logs on its own clock, so windows are matched by rounding.
function mergeSeries(
  players: PlayerNetstats[],
  pick: (p: PlayerNetstats) => { t: number; v: number }[],
): Row[] {
  const rows = new Map<number, Row>()
  for (const p of players) {
    for (const { t, v } of pick(p)) {
      const bucket = Math.round(t / WINDOW_SECONDS) * WINDOW_SECONDS
      const row = rows.get(bucket) ?? ({ t: bucket } as Row)
      row[p.name] = v
      rows.set(bucket, row)
    }
  }
  return [...rows.values()].sort((a, b) => a.t - b.t)
}

function SeriesChart(props: {
  title: string
  note: string
  unit: string
  data: Row[]
  players: PlayerNetstats[]
  colors: Record<string, string>
  hidden: Set<string>
  reference?: { y: number; label: string }
}) {
  return (
    <Box>
      <Typography variant="h6" component="h2">
        {props.title}
      </Typography>
      <Typography
        variant="body2"
        sx={{ color: "text.secondary", mb: 1, maxWidth: "80ch" }}
      >
        {props.note}
      </Typography>
      <ResponsiveContainer width="99%" height={300}>
        <LineChart
          data={props.data}
          margin={{ top: 8, right: 12, left: 0, bottom: 4 }}
        >
          <CartesianGrid strokeDasharray="5 5" vertical={false} />
          <XAxis
            dataKey="t"
            type="number"
            domain={["dataMin", "dataMax"]}
            tickFormatter={mmss}
            tick={{ fontSize: 11 }}
          />
          <YAxis tick={{ fontSize: 11 }} width={44} />
          <Tooltip
            labelFormatter={(t) => `${mmss(Number(t))} into the match`}
            formatter={(v) => `${Number(v).toFixed(1)}${props.unit}`}
            itemSorter={(item) => -Number(item.value ?? 0)}
          />
          {props.reference && (
            <ReferenceLine
              y={props.reference.y}
              stroke="#c0392b"
              strokeDasharray="5 4"
              label={{
                value: props.reference.label,
                fontSize: 11,
                position: "insideTopRight",
              }}
            />
          )}
          {props.players
            .filter((p) => !props.hidden.has(p.name))
            .map((p) => (
              <Line
                key={p.name}
                dataKey={p.name}
                stroke={props.colors[p.name]}
                strokeWidth={2}
                dot={false}
                isAnimationActive={false}
                connectNulls
              />
            ))}
        </LineChart>
      </ResponsiveContainer>
    </Box>
  )
}

function Scoreboard(props: {
  players: PlayerNetstats[]
  colors: Record<string, string>
}) {
  const num = (v: number | null | undefined, digits = 1) =>
    v == null ? "–" : v.toFixed(digits)
  return (
    <TableContainer>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Player</TableCell>
            <TableCell align="right">Frame ms avg</TableCell>
            <TableCell align="right">Sim ms avg</TableCell>
            <TableCell align="right">Peak objects</TableCell>
            <TableCell align="right">Median ping ms</TableCell>
            <TableCell align="right">Freezes caused</TableCell>
            <TableCell align="right">Freeze time</TableCell>
            <TableCell align="right">Lowest fps</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {props.players.map((p) => (
            <TableRow key={p.name}>
              <TableCell>
                <Stack
                  direction="row"
                  spacing={1}
                  sx={{ alignItems: "center" }}
                >
                  <Box
                    sx={{
                      width: 10,
                      height: 10,
                      borderRadius: "50%",
                      bgcolor: props.colors[p.name],
                    }}
                  />
                  <span>{p.name}</span>
                  {p.team != null && (
                    <Chip size="small" label={`Team ${p.team + 1}`} />
                  )}
                </Stack>
              </TableCell>
              <TableCell align="right">{num(p.clientMsAvg)}</TableCell>
              <TableCell align="right">{num(p.logicMsAvg)}</TableCell>
              <TableCell align="right">{p.peakObjects ?? "–"}</TableCell>
              <TableCell align="right">{num(p.medianPingMs, 0)}</TableCell>
              <TableCell align="right">{p.freezesCaused}</TableCell>
              <TableCell align="right">
                {(p.freezeMsCaused / 1000).toFixed(1)} s
              </TableCell>
              <TableCell align="right">{p.minFps ?? "–"}</TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function Freezes(props: {
  report: MatchNetstats
  colors: Record<string, string>
  hidden: Set<string>
}) {
  const { report } = props
  const byslot = new Map(report.players.map((p) => [p.slot, p]))
  const visible = report.players.filter((p) => !props.hidden.has(p.name))
  return (
    <ResponsiveContainer width="99%" height={60 + 34 * visible.length}>
      <ScatterChart margin={{ top: 8, right: 12, left: 0, bottom: 4 }}>
        <CartesianGrid strokeDasharray="5 5" />
        <XAxis
          dataKey="t"
          type="number"
          domain={[0, (report.frames ?? 0) / FPS]}
          tickFormatter={mmss}
          tick={{ fontSize: 11 }}
          name="time"
        />
        <YAxis
          dataKey="slot"
          type="number"
          domain={[-0.5, 7.5]}
          ticks={visible.map((p) => p.slot)}
          tickFormatter={(s) => byslot.get(Number(s))?.name ?? ""}
          width={96}
          tick={{ fontSize: 12 }}
          interval={0}
          reversed
        />
        <ZAxis dataKey="ms" range={[30, 260]} name="waited" unit=" ms" />
        <Tooltip
          cursor={{ strokeDasharray: "3 3" }}
          formatter={(v, name) => (name === "time" ? mmss(Number(v)) : v)}
        />
        {visible.map((p) => (
          <Scatter
            key={p.name}
            name={p.name}
            fill={props.colors[p.name]}
            isAnimationActive={false}
            data={report.freezes
              .filter((f) => f.slots.includes(p.slot))
              .map((f) => ({ t: f.frame / FPS, slot: p.slot, ms: f.waitedMs }))}
          />
        ))}
      </ScatterChart>
    </ResponsiveContainer>
  )
}

function samples(
  p: PlayerNetstats,
  v: (s: PlayerNetstats["samples"][number]) => number,
) {
  return p.samples.map((s) => ({ t: s.frame / FPS, v: v(s) }))
}

function Report(props: { report: MatchNetstats }) {
  const { report } = props
  const theme = useTheme()
  const palette = SLOT_COLORS[theme.palette.mode]
  const colors = React.useMemo(
    () =>
      Object.fromEntries(
        report.players.map((p) => [p.name, palette[p.slot % palette.length]]),
      ),
    [report.players, palette],
  )
  const [hidden, setHidden] = React.useState<Set<string>>(new Set())
  const toggle = (name: string) =>
    setHidden((prev) => {
      const next = new Set(prev)
      if (next.has(name)) next.delete(name)
      else next.add(name)
      return next.size === report.players.length ? new Set() : next
    })
  const series = React.useMemo(
    () => ({
      client: mergeSeries(report.players, (p) =>
        samples(p, (s) => s.clientMsAvg),
      ),
      logic: mergeSeries(report.players, (p) =>
        samples(p, (s) => s.logicMsAvg),
      ),
      objects: mergeSeries(report.players, (p) => samples(p, (s) => s.objects)),
      ping: mergeSeries(report.players, (p) =>
        p.pings.map((q) => ({ t: q.seconds, v: q.medianMs })),
      ),
    }),
    [report.players],
  )
  const shared = { players: report.players, colors, hidden }
  return (
    <Stack spacing={4}>
      <Stack
        direction="row"
        spacing={1}
        useFlexGap
        sx={{ flexWrap: "wrap" }}
        aria-label="Show or hide players"
      >
        {report.players.map((p) => (
          <Chip
            key={p.name}
            label={p.name}
            onClick={() => toggle(p.name)}
            variant={hidden.has(p.name) ? "outlined" : "filled"}
            sx={{
              bgcolor: hidden.has(p.name) ? undefined : colors[p.name],
              color: hidden.has(p.name) ? undefined : "#fff",
              "&:hover": {
                bgcolor: hidden.has(p.name) ? undefined : colors[p.name],
              },
            }}
          />
        ))}
      </Stack>
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        {report.frames != null
          ? `${mmss(report.frames / FPS)} · ${report.frames.toLocaleString()} frames`
          : "Match did not log an end"}
        {report.desync ? " · desync" : ""} · {report.freezes.length} freezes
      </Typography>
      <Scoreboard players={report.players} colors={colors} />
      <SeriesChart
        title="Frame time per PC"
        note="Average client frame time per 10 second window, with the first window (map load) left out. The dashed line is the 60 fps budget."
        unit=" ms"
        data={series.client}
        reference={{ y: FRAME_BUDGET_MS, label: "60 fps budget" }}
        {...shared}
      />
      <SeriesChart
        title="Simulation time per PC"
        note="Average game logic time per frame. It rises with unit count on every PC; a PC far above the rest is slower at the same work."
        unit=" ms"
        data={series.logic}
        {...shared}
      />
      <SeriesChart
        title="Objects on the map"
        note="Every PC simulates the same game, so these lines should overlap."
        unit=""
        data={series.objects}
        {...shared}
      />
      <Box>
        <Typography variant="h6" component="h2">
          Freezes
        </Typography>
        <Typography
          variant="body2"
          sx={{ color: "text.secondary", mb: 1, maxWidth: "80ch" }}
        >
          Each dot is a stall of the whole game, in{" "}
          {report.players.find((p) => p.slot === report.freezesViewSlot)
            ?.name ?? "one player"}
          's view. The row is the player the game was waiting for; a bigger dot
          is a longer wait.
        </Typography>
        <Freezes report={report} colors={colors} hidden={hidden} />
      </Box>
      <SeriesChart
        title="Ping per PC"
        note="Median round trip time from each player's PC to the others, sampled every 30 seconds on the wall clock, so this axis runs longer than the game-time charts when the game ran slower than real time. The log names links by lobby id, not player slot, so this isn't broken down by pair."
        unit=" ms"
        data={series.ping}
        {...shared}
      />
    </Stack>
  )
}

export default function MatchNetstatsPage() {
  const [param, setParam] = useUrlParam("matchId")
  const [draft, setDraft] = React.useState(param ?? "")
  const seed = param && /^\d+$/.test(param) ? Number(param) : null
  // On demand: nothing is fetched until a match id is submitted.
  const query = useQuery({
    ...matchNetstatsApiAdminMatchMatchIdNetstatsGetOptions({
      path: { match_id: seed ?? 0 },
    }),
    enabled: seed != null,
    retry: false,
  })
  const submit = (e: React.FormEvent) => {
    e.preventDefault()
    setParam(draft.trim() || null)
  }
  const fallback = seed != null ? queryFallback(query, "match netstats") : null
  return (
    <Page
      title="Match Netstats"
      description="PC and network stats from the players' own game logs, fetched from cncstats by match id. Older matches may have no logs."
      actions={
        <form onSubmit={submit}>
          <Stack direction="row" spacing={1}>
            <TextField
              id="netstats-match-id"
              size="small"
              label="Match id"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              slotProps={{ htmlInput: { inputMode: "numeric" } }}
            />
            <Button
              type="submit"
              variant="contained"
              disabled={!/^\d+$/.test(draft.trim())}
            >
              Load
            </Button>
          </Stack>
        </form>
      }
    >
      {seed == null ? (
        <Typography color="text.secondary">
          Enter a match id to load its logs.
        </Typography>
      ) : (
        (fallback ?? <Report report={query.data as MatchNetstats} />)
      )}
    </Page>
  )
}
