import SwapHorizIcon from "@mui/icons-material/SwapHoriz"
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import ListSubheader from "@mui/material/ListSubheader"
import MenuItem from "@mui/material/MenuItem"
import Paper from "@mui/material/Paper"
import Select from "@mui/material/Select"
import Stack from "@mui/material/Stack"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TextField from "@mui/material/TextField"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import { keepPreviousData, useQuery } from "@tanstack/react-query"
import * as React from "react"
import {
  scenarioModelApiScenarioModelGetOptions,
  scenarioPredictApiScenarioPredictGetOptions,
} from "../../api/@tanstack/react-query.gen"
import type {
  ScenarioInterval,
  ScenarioMapEntry,
  ScenarioModelSummary,
  ScenarioPick,
  ScenarioPrediction,
  ScenarioSlotSwaps,
} from "../../api/types.gen"
import FormatToggle from "../../components/FormatToggle"
import { FactionAvatar, GeneralAvatar } from "../../components/Generals"
import Page from "../../components/Page"
import QueryState from "../../components/QueryState"
import WinShareBar from "../../components/WinShareBar"
import { General } from "../../lib/General"
import { FACTIONS, type Faction, toGeneralName } from "../../lib/general_utils"
import {
  BRAND_COLOR,
  CHART_PALETTE,
  LOSS_COLOR,
  NEUTRAL_COLOR,
  WIN_COLOR,
} from "../../lib/theme"
import { useUrlChoice, useUrlParam, useUrlPatch } from "../../lib/useUrlState"

const FORMATS = ["1v1", "2v2", "3v3", "4v4"] as const

const TEAM_A_COLOR = BRAND_COLOR
const TEAM_B_COLOR = CHART_PALETTE[3]

const RANDOM_OF: Record<Faction, ScenarioPick> = {
  USA: "RANDOM_USA",
  CHINA: "RANDOM_CHINA",
  GLA: "RANDOM_GLA",
}
const ALL_PICKS: ScenarioPick[] = [
  "RANDOM",
  ...FACTIONS.flatMap((f) => [
    RANDOM_OF[f.faction],
    ...f.generals.map((g) => toGeneralName(g) as ScenarioPick),
  ]),
]

const GENERALS = FACTIONS.flatMap((f) => f.generals)

const MAP_FEATURE_LABELS: Record<string, string> = {
  log_size: "map size",
  log_money_per_player: "supply objects per start",
  log_oil_per_player: "tech objects per start",
}

const sigmoid = (x: number) => 1 / (1 + Math.exp(-x))
const pct = (p: number) => `${Math.round(p * 100)}%`
const pp = (d: number, digits = 1) =>
  `${d >= 0 ? "+" : "−"}${Math.abs(d * 100).toFixed(digits)}`
const excludesZero = (i: ScenarioInterval) => i.low > 0 || i.high < 0

function pickLabel(pick: ScenarioPick): string {
  if (pick === "RANDOM") return "Random"
  if (pick.startsWith("RANDOM_")) return `Random ${pick.slice(7)}`
  return pick
}

function PickIcon({ pick }: { pick: ScenarioPick }) {
  if (pick === "RANDOM") {
    return (
      <Box
        sx={{
          width: "1.5rem",
          height: "1.5rem",
          borderRadius: "50%",
          bgcolor: "action.selected",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: "0.8rem",
        }}
      >
        ?
      </Box>
    )
  }
  if (pick.startsWith("RANDOM_")) {
    return <FactionAvatar faction={pick.slice(7) as Faction} size="1.5rem" />
  }
  return (
    <GeneralAvatar
      general={General[pick as keyof typeof General]}
      size="1.5rem"
    />
  )
}

function parseTeam(raw: string | null, n: number): ScenarioPick[] {
  const picks = (raw ?? "")
    .split(",")
    .filter((p): p is ScenarioPick => ALL_PICKS.includes(p as ScenarioPick))
  return Array.from({ length: n }, (_, i) => picks[i] ?? "RANDOM")
}

function SlotSelect(props: {
  value: ScenarioPick
  onChange: (pick: ScenarioPick) => void
  label: string
}) {
  const item = (pick: ScenarioPick, indent = false) => (
    <MenuItem key={pick} value={pick} sx={{ pl: indent ? 3 : 2 }}>
      <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
        <PickIcon pick={pick} />
        <span>{pickLabel(pick)}</span>
      </Stack>
    </MenuItem>
  )
  return (
    <Select
      size="small"
      value={props.value}
      onChange={(e) => props.onChange(e.target.value as ScenarioPick)}
      inputProps={{ "aria-label": props.label }}
      renderValue={(pick) => (
        <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
          <PickIcon pick={pick} />
          <span>{pickLabel(pick)}</span>
        </Stack>
      )}
      sx={{ minWidth: 180 }}
    >
      {item("RANDOM")}
      {FACTIONS.flatMap((f) => [
        <ListSubheader key={`h-${f.faction}`}>{f.name}</ListSubheader>,
        item(RANDOM_OF[f.faction], true),
        ...f.generals.map((g) => item(toGeneralName(g) as ScenarioPick, true)),
      ])}
    </Select>
  )
}

function TeamColumn(props: {
  name: string
  color: string
  picks: ScenarioPick[]
  onChange: (index: number, pick: ScenarioPick) => void
}) {
  return (
    <Stack spacing={1} sx={{ flex: "1 1 200px" }}>
      <Typography
        variant="subtitle2"
        sx={{ borderLeft: `4px solid ${props.color}`, pl: 1 }}
      >
        {props.name}
      </Typography>
      {props.picks.map((pick, i) => (
        <SlotSelect
          // biome-ignore lint/suspicious/noArrayIndexKey: slots are positional
          key={i}
          label={`${props.name} slot ${i + 1}`}
          value={pick}
          onChange={(next) => props.onChange(i, next)}
        />
      ))}
    </Stack>
  )
}

const mapFilter = createFilterOptions<ScenarioMapEntry>({ limit: 100 })

function MapPicker(props: {
  maps: ScenarioMapEntry[]
  players: number
  value: string | null
  onChange: (key: string | null) => void
}) {
  const options = React.useMemo(
    () =>
      props.maps.filter((m) => m.knownGeometry && m.players === props.players),
    [props.maps, props.players],
  )
  const selected = options.find((m) => m.key === props.value) ?? null
  return (
    <Autocomplete
      size="small"
      options={options}
      value={selected}
      filterOptions={mapFilter}
      getOptionLabel={(m) => m.key}
      isOptionEqualToValue={(a, b) => a.key === b.key}
      onChange={(_, m) => props.onChange(m?.key ?? null)}
      renderOption={(liProps, m) => {
        const { key, ...rest } = liProps
        return (
          <li key={key} {...rest}>
            <Stack
              direction="row"
              sx={{ width: "100%", justifyContent: "space-between" }}
            >
              <span>{m.key}</span>
              <Typography variant="caption" sx={{ color: "text.secondary" }}>
                {m.trainingGames} games
              </Typography>
            </Stack>
          </li>
        )
      }}
      renderInput={(params) => (
        <TextField {...params} label="Map" placeholder="Average map" />
      )}
      sx={{ minWidth: 280, maxWidth: 420 }}
    />
  )
}

/** A point with its interval on a symmetric axis around zero. */
function IntervalBar(props: {
  interval: ScenarioInterval
  scale: number
  width?: number
}) {
  const w = props.width ?? 160
  const h = 14
  const x = (v: number) =>
    w / 2 +
    (Math.max(-props.scale, Math.min(props.scale, v)) / props.scale) *
      (w / 2 - 4)
  const { value, low, high } = props.interval
  const color = excludesZero(props.interval)
    ? value > 0
      ? WIN_COLOR
      : LOSS_COLOR
    : NEUTRAL_COLOR
  return (
    <svg width={w} height={h} role="img" aria-hidden>
      <line
        x1={w / 2}
        x2={w / 2}
        y1={0}
        y2={h}
        stroke={NEUTRAL_COLOR}
        strokeOpacity={0.6}
      />
      <line
        x1={x(low)}
        x2={x(high)}
        y1={h / 2}
        y2={h / 2}
        stroke={color}
        strokeWidth={2}
        strokeLinecap="round"
      />
      <circle cx={x(value)} cy={h / 2} r={4} fill={color} />
    </svg>
  )
}

function Headline({ prediction }: { prediction: ScenarioPrediction }) {
  const p = prediction.probTeamA
  const settled = excludesZero({
    value: 0,
    low: p.low - 0.5,
    high: p.high - 0.5,
  })
  const leader = p.value >= 0.5 ? "Team A" : "Team B"
  const share = Math.max(p.value, 1 - p.value)
  const c = prediction.contributions
  const pieces: [string, number][] = [
    ["Generals", c.generals],
    ["Teammate pairings", c.teammates],
    ["Head-to-head matchups", c.matchups],
    ["Map", c.map],
  ]
  return (
    <Stack spacing={1.5}>
      <Stack
        direction="row"
        sx={{ justifyContent: "space-between", alignItems: "baseline" }}
      >
        <Typography variant="h5" sx={{ color: TEAM_A_COLOR }}>
          Team A {pct(p.value)}
        </Typography>
        <Typography variant="h5" sx={{ color: TEAM_B_COLOR }}>
          {pct(1 - p.value)} Team B
        </Typography>
      </Stack>
      <WinShareBar
        fraction={p.value}
        leftColor={TEAM_A_COLOR}
        rightColor={TEAM_B_COLOR}
      />
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Equal skill · 90%: {pct(p.low)}–{pct(p.high)}
      </Typography>
      <Typography variant="body1">
        {settled
          ? `${leader} is favored (${pct(share)}).`
          : "Too close to call."}
        {!prediction.combinationsExact &&
          ` Random slots: ${prediction.combinations} sampled lineups.`}
        {prediction.combinationsExact &&
          prediction.combinations > 1 &&
          ` Random slots: all ${prediction.combinations} lineups.`}
      </Typography>
      <Stack direction="row" sx={{ flexWrap: "wrap", gap: 1 }}>
        {pieces.map(([label, logit]) => (
          <Paper
            key={label}
            variant="outlined"
            sx={{ p: 1, flex: "1 1 140px" }}
          >
            <Typography variant="caption" sx={{ color: "text.secondary" }}>
              {label}
            </Typography>
            <Typography variant="subtitle1">
              {pp(sigmoid(logit) - 0.5)} pts
            </Typography>
          </Paper>
        ))}
      </Stack>
      <Typography variant="caption" sx={{ color: "text.secondary" }}>
        Points toward Team A.
        {prediction.support &&
          (prediction.support.exactGames > 0
            ? ` This exact lineup: ${prediction.support.exactTeamAWins}–${prediction.support.exactGames - prediction.support.exactTeamAWins} in ${prediction.support.exactGames} real games.`
            : " This exact lineup has never been played.")}
        {prediction.map &&
          ` ${prediction.map.key}: ${prediction.map.trainingGames} games${prediction.map.knownGeometry ? "" : ", no geometry"}.`}
      </Typography>
    </Stack>
  )
}

function SwapGrid(props: {
  swaps: ScenarioSlotSwaps[]
  picks: { a: ScenarioPick[]; b: ScenarioPick[] }
  onPick: (team: "A" | "B", index: number, general: General) => void
}) {
  const scale = Math.max(
    0.01,
    ...props.swaps.flatMap((s) =>
      s.options.map((o) => Math.abs(o.delta.value)),
    ),
  )
  return (
    <TableContainer>
      <Table
        size="small"
        sx={{ "& td, & th": { px: 0.5, textAlign: "center" } }}
      >
        <TableHead>
          <TableRow>
            <TableCell />
            {GENERALS.map((g) => (
              <TableCell key={g}>
                <Stack sx={{ alignItems: "center" }}>
                  <GeneralAvatar general={g} size="1.25rem" />
                  <Typography variant="caption" sx={{ fontSize: "0.65rem" }}>
                    {toGeneralName(g).slice(0, 4)}
                  </Typography>
                </Stack>
              </TableCell>
            ))}
          </TableRow>
        </TableHead>
        <TableBody>
          {props.swaps.map((slot) => {
            const team = slot.team as "A" | "B"
            const current = (team === "A" ? props.picks.a : props.picks.b)[
              slot.index
            ]
            // From the slot's own team's point of view.
            const sign = team === "A" ? 1 : -1
            return (
              <TableRow key={`${team}${slot.index}`}>
                <TableCell
                  sx={{ whiteSpace: "nowrap", textAlign: "left !important" }}
                >
                  <Typography
                    variant="caption"
                    sx={{
                      borderLeft: `3px solid ${team === "A" ? TEAM_A_COLOR : TEAM_B_COLOR}`,
                      pl: 0.5,
                    }}
                  >
                    {team}
                    {slot.index + 1} · {pickLabel(current)}
                  </Typography>
                </TableCell>
                {slot.options.map((o) => {
                  const d = sign * o.delta.value
                  const lo = sign === 1 ? o.delta.low : -o.delta.high
                  const hi = sign === 1 ? o.delta.high : -o.delta.low
                  const clear = excludesZero(o.delta)
                  const isCurrent = toGeneralName(o.general) === current
                  const alpha = Math.round(
                    (Math.abs(d) / scale) * (clear ? 200 : 70),
                  )
                    .toString(16)
                    .padStart(2, "0")
                  return (
                    <Tooltip
                      key={o.general}
                      title={`${team}${slot.index + 1} → ${toGeneralName(o.general)}: ${pp(d)} pts for Team ${team} (90%: ${pp(lo)} to ${pp(hi)})${clear ? "" : " — not clear"}`}
                    >
                      <TableCell
                        onClick={() =>
                          props.onPick(team, slot.index, o.general)
                        }
                        sx={{
                          cursor: "pointer",
                          bgcolor: isCurrent
                            ? "transparent"
                            : `${d >= 0 ? WIN_COLOR : LOSS_COLOR}${alpha}`,
                          outline: isCurrent
                            ? `2px solid ${NEUTRAL_COLOR}`
                            : "none",
                          outlineOffset: -2,
                          fontWeight: clear ? 600 : 400,
                          color: clear ? "text.primary" : "text.secondary",
                          fontSize: "0.75rem",
                        }}
                      >
                        {isCurrent ? "·" : pp(d, 0)}
                      </TableCell>
                    </Tooltip>
                  )
                })}
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function MapComparison(props: {
  prediction: ScenarioPrediction
  selected: string | null
  onPick: (key: string) => void
}) {
  const scale = Math.max(
    0.01,
    ...props.prediction.maps.map((m) =>
      Math.max(Math.abs(m.delta.low), Math.abs(m.delta.high)),
    ),
  )
  return (
    <Table size="small">
      <TableHead>
        <TableRow>
          <TableCell>Map</TableCell>
          <TableCell align="right">Games</TableCell>
          <TableCell align="right">Team A</TableCell>
          <TableCell>vs average map</TableCell>
        </TableRow>
      </TableHead>
      <TableBody>
        {props.prediction.maps.map((m) => (
          <TableRow
            key={m.key}
            hover
            selected={m.key === props.selected}
            onClick={() => props.onPick(m.key)}
            sx={{ cursor: "pointer" }}
          >
            <TableCell>{m.key}</TableCell>
            <TableCell align="right">{m.trainingGames}</TableCell>
            <TableCell align="right">{pct(m.probTeamA)}</TableCell>
            <TableCell>
              <Tooltip
                title={`${pp(m.delta.value)} pts for Team A (90%: ${pp(m.delta.low)} to ${pp(m.delta.high)})`}
              >
                <Box component="span">
                  <IntervalBar interval={m.delta} scale={scale} />
                </Box>
              </Tooltip>
            </TableCell>
          </TableRow>
        ))}
      </TableBody>
    </Table>
  )
}

function Section(props: {
  title: string
  caption?: string
  children: React.ReactNode
}) {
  return (
    <Paper variant="outlined" sx={{ p: { xs: 1.5, sm: 2 } }}>
      <Typography variant="h6">{props.title}</Typography>
      {props.caption && (
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 1 }}>
          {props.caption}
        </Typography>
      )}
      {props.children}
    </Paper>
  )
}

function EffectRow(props: {
  label: React.ReactNode
  interval: ScenarioInterval
  toPoints: (logit: number) => number
  scale: number
  extra?: string
}) {
  const { value, low, high } = props.interval
  const asPoints = {
    value: props.toPoints(value),
    low: props.toPoints(low),
    high: props.toPoints(high),
  }
  return (
    <TableRow>
      <TableCell>{props.label}</TableCell>
      <TableCell
        align="right"
        sx={{ fontWeight: excludesZero(props.interval) ? 600 : 400 }}
      >
        {pp(asPoints.value)}
      </TableCell>
      <TableCell>
        <Tooltip title={`90%: ${pp(asPoints.low)} to ${pp(asPoints.high)} pts`}>
          <Box component="span">
            <IntervalBar interval={asPoints} scale={props.scale} />
          </Box>
        </Tooltip>
      </TableCell>
      {props.extra !== undefined && (
        <TableCell align="right" sx={{ color: "text.secondary" }}>
          {props.extra}
        </TableCell>
      )}
    </TableRow>
  )
}

function GeneralPair({ a, b, sep }: { a: General; b: General; sep: string }) {
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
      <GeneralAvatar general={a} size="1.25rem" />
      <span>{toGeneralName(a)}</span>
      <Typography variant="caption" sx={{ color: "text.secondary" }}>
        {sep}
      </Typography>
      <GeneralAvatar general={b} size="1.25rem" />
      <span>{toGeneralName(b)}</span>
    </Stack>
  )
}

function FactionPair({ a, b }: { a: number; b: number }) {
  const [fa, fb] = [FACTIONS[a], FACTIONS[b]]
  return (
    <Stack direction="row" spacing={0.5} sx={{ alignItems: "center" }}>
      <FactionAvatar faction={fa.faction} size="1.25rem" />
      <span>{fa.name}</span>
      <Typography variant="caption" sx={{ color: "text.secondary" }}>
        +
      </Typography>
      <FactionAvatar faction={fb.faction} size="1.25rem" />
      <span>{fb.name}</span>
    </Stack>
  )
}

function WhatMatters({
  summary,
  n,
}: {
  summary: ScenarioModelSummary
  n: number
}) {
  const slot = (logit: number) => sigmoid(logit / n) - 0.5
  const pair =
    n >= 2
      ? (logit: number) => sigmoid(logit / ((n * (n - 1)) / 2)) - 0.5
      : null
  const versus = (logit: number) => sigmoid(logit / (n * n)) - 0.5
  const span = (rows: ScenarioInterval[], f: (x: number) => number) =>
    Math.max(
      0.005,
      ...rows.flatMap((r) => [Math.abs(f(r.low)), Math.abs(f(r.high))]),
    )
  const generalScale = span(
    summary.generals.map((g) => g.effect),
    slot,
  )
  return (
    <Stack spacing={2}>
      <Section
        title="General strength"
        caption={`From ${summary.model.nGames} games, ${summary.model.dateMin} to ${summary.model.dateMax}. Points per slot in a ${n}v${n}, vs an average general; bold = clear effect. Who's playing matters far more than which general.`}
      >
        <Table size="small">
          <TableBody>
            {summary.generals.map((g) => (
              <EffectRow
                key={g.general}
                label={
                  <Stack
                    direction="row"
                    spacing={1}
                    sx={{ alignItems: "center" }}
                  >
                    <GeneralAvatar general={g.general} size="1.25rem" />
                    <span>{toGeneralName(g.general)}</span>
                  </Stack>
                }
                interval={g.effect}
                toPoints={slot}
                scale={generalScale}
                extra={`${g.games} games`}
              />
            ))}
          </TableBody>
        </Table>
      </Section>
      <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
        <Section
          title="Largest matchups"
          caption={"First general facing the second."}
        >
          <Table size="small">
            <TableBody>
              {summary.matchups.map((m) => (
                <EffectRow
                  key={`${m.generalA}-${m.generalB}`}
                  label={<GeneralPair a={m.generalA} b={m.generalB} sep="vs" />}
                  interval={m.effect}
                  toPoints={versus}
                  scale={span(
                    summary.matchups.map((x) => x.effect),
                    versus,
                  )}
                />
              ))}
            </TableBody>
          </Table>
        </Section>
        <Section
          title="Teammate factions"
          caption={
            pair
              ? "By faction; general pairs add nothing detectable."
              : "No teammates in a 1v1."
          }
        >
          {pair && (
            <Table size="small">
              <TableBody>
                {summary.teammates.map((m) => (
                  <EffectRow
                    key={`${m.factionA}-${m.factionB}`}
                    label={<FactionPair a={m.factionA} b={m.factionB} />}
                    interval={m.effect}
                    toPoints={pair}
                    scale={span(
                      summary.teammates.map((x) => x.effect),
                      pair,
                    )}
                  />
                ))}
              </TableBody>
            </Table>
          )}
        </Section>
      </Stack>
      <Section
        title="Largest map effects"
        caption="How generals do as maps get bigger or have more supply and tech."
      >
        <Table size="small">
          <TableBody>
            {summary.mapEffects.map((m) => (
              <EffectRow
                key={`${m.general}-${m.feature}`}
                label={`${toGeneralName(m.general)} on larger ${MAP_FEATURE_LABELS[m.feature] ?? m.feature}`}
                interval={m.effect}
                toPoints={slot}
                scale={span(
                  summary.mapEffects.map((x) => x.effect),
                  slot,
                )}
              />
            ))}
          </TableBody>
        </Table>
      </Section>
    </Stack>
  )
}

function Results(props: {
  team: { a: ScenarioPick[]; b: ScenarioPick[] }
  map: string | null
  setSlot: (team: "A" | "B", index: number, pick: ScenarioPick) => void
  setMap: (key: string | null) => void
}) {
  const query = useQuery({
    ...scenarioPredictApiScenarioPredictGetOptions({
      query: {
        team_a: props.team.a,
        team_b: props.team.b,
        map_name: props.map,
      },
    }),
    placeholderData: keepPreviousData,
  })
  return (
    <QueryState query={query} what="prediction">
      {(prediction) => (
        <Stack spacing={2} sx={{ opacity: query.isPlaceholderData ? 0.6 : 1 }}>
          <Section title="Prediction">
            <Headline prediction={prediction} />
          </Section>
          <Section
            title="Change one slot"
            caption="Points for that slot's team if it switched. Faded = no clear change. Click to swap."
          >
            <SwapGrid
              swaps={prediction.swaps}
              picks={props.team}
              onPick={(team, index, general) =>
                props.setSlot(
                  team,
                  index,
                  toGeneralName(general) as ScenarioPick,
                )
              }
            />
          </Section>
          <Section
            title="Same lineups on other maps"
            caption="Vs an average map. Click to select."
          >
            <MapComparison
              prediction={prediction}
              selected={props.map}
              onPick={props.setMap}
            />
          </Section>
        </Stack>
      )}
    </QueryState>
  )
}

export default function CompositionPredictor() {
  const [format, setFormat] = useUrlChoice("format", FORMATS, "3v3")
  const n = FORMATS.indexOf(format) + 1
  const [rawA] = useUrlParam("a")
  const [rawB] = useUrlParam("b")
  const [map, setMap] = useUrlParam("map")
  const patch = useUrlPatch()
  const team = React.useMemo(
    () => ({ a: parseTeam(rawA, n), b: parseTeam(rawB, n) }),
    [rawA, rawB, n],
  )
  const summary = useQuery(scenarioModelApiScenarioModelGetOptions())
  // A ?map= left over from another format doesn't fit this player count.
  const mapPlayers = summary.data?.maps.find((m) => m.key === map)?.players
  const activeMap = mapPlayers != null && mapPlayers !== 2 * n ? null : map

  const setSlot = (side: "A" | "B", index: number, pick: ScenarioPick) => {
    const picks = [...(side === "A" ? team.a : team.b)]
    picks[index] = pick
    patch({ [side === "A" ? "a" : "b"]: picks.join(",") })
  }

  return (
    <Page
      title="Composition Predictor"
      surface={false}
      description="Who's favored between equally skilled players, from generals and map alone."
      actions={
        <FormatToggle
          options={FORMATS}
          value={format}
          onChange={setFormat}
          label="Format"
        />
      }
    >
      <Stack spacing={2}>
        <Paper variant="outlined" sx={{ p: { xs: 1.5, sm: 2 } }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={2}
            sx={{ alignItems: "flex-start" }}
          >
            <TeamColumn
              name="Team A"
              color={TEAM_A_COLOR}
              picks={team.a}
              onChange={(i, p) => setSlot("A", i, p)}
            />
            <Button
              variant="outlined"
              startIcon={<SwapHorizIcon />}
              onClick={() =>
                patch({ a: team.b.join(","), b: team.a.join(",") })
              }
              sx={{ alignSelf: { sm: "center" } }}
            >
              Swap
            </Button>
            <TeamColumn
              name="Team B"
              color={TEAM_B_COLOR}
              picks={team.b}
              onChange={(i, p) => setSlot("B", i, p)}
            />
          </Stack>
          <Box sx={{ mt: 2 }}>
            <MapPicker
              maps={summary.data?.maps ?? []}
              players={2 * n}
              value={activeMap}
              onChange={setMap}
            />
          </Box>
        </Paper>
        <Results
          // A placeholder from another format has the wrong number of slots.
          key={format}
          team={team}
          map={activeMap}
          setSlot={setSlot}
          setMap={setMap}
        />
        <QueryState query={summary} what="general stats">
          {(s) => <WhatMatters summary={s} n={n} />}
        </QueryState>
      </Stack>
    </Page>
  )
}
