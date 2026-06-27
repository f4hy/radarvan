import * as React from "react"
import Box from "@mui/material/Box"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import FormControlLabel from "@mui/material/FormControlLabel"
import Switch from "@mui/material/Switch"
import Slider from "@mui/material/Slider"
import Typography from "@mui/material/Typography"
import { Tooltip as MuiTooltip } from "@mui/material"

import { PlayerSynergy } from "./api"
import { Client } from "./Client"
import Loading from "./Loading"
import { PlayerLabel } from "./PlayerChip"
import { WIN_COLOR, LOSS_COLOR } from "./theme"
import { useErrorSnackbar } from "./useErrorSnackbar"

const FORMAT_OPTIONS = ["All", "2v2", "3v3", "4v4"] as const
type GameFormat = (typeof FORMAT_OPTIONS)[number]

const MIN_GAMES_OPTIONS = [3, 5, 10] as const
const SIGNIFICANT_Z = 2

// Must match the backend defaults (radarvan/player_synergy.py).
const DEFAULT_PAIR_REG = 10
const DEFAULT_MAIN_REG = 25

// One regularization slider. Dragging updates only the label (`draft`); the
// committed value (which triggers the refetch) changes on release, so a drag
// doesn't fire a heavy backend recompute on every step.
function RegSlider(props: {
  label: string
  tooltip: string
  draft: number
  min: number
  max: number
  onDraft: (v: number) => void
  onCommit: (v: number) => void
}) {
  return (
    <Box sx={{ minWidth: 170 }}>
      <MuiTooltip title={props.tooltip}>
        <Typography variant="caption" color="text.secondary">
          {props.label}: {props.draft}
        </Typography>
      </MuiTooltip>
      <Slider
        size="small"
        value={props.draft}
        min={props.min}
        max={props.max}
        step={1}
        valueLabelDisplay="auto"
        onChange={(_, v) => props.onDraft(v as number)}
        onChangeCommitted={(_, v) => props.onCommit(v as number)}
      />
    </Box>
  )
}

function signedPct(x: number): string {
  return `${x >= 0 ? "+" : ""}${(x * 100).toFixed(1)}%`
}

function pct(x: number): string {
  return `${(x * 100).toFixed(0)}%`
}

// The "Pair" table cell: two player chips joined by a "+". Shared by both the
// full and simplified synergy tables so pair rendering can't drift between them.
function PairCell(props: { a: string; b: string }) {
  return (
    <TableCell>
      <Stack
        direction="row"
        spacing={1}
        alignItems="center"
        sx={{ flexWrap: "wrap" }}
      >
        <PlayerLabel name={props.a} />
        <Typography component="span" color="text.secondary">
          +
        </Typography>
        <PlayerLabel name={props.b} />
      </Stack>
    </TableCell>
  )
}

export default function DisplayPlayerSynergy() {
  const [pairs, setPairs] = React.useState<PlayerSynergy[] | null>(null)
  const [format, setFormat] = React.useState<GameFormat>("All")
  const [minGames, setMinGames] = React.useState<number>(3)
  const [significantOnly, setSignificantOnly] = React.useState(false)
  const [pairReg, setPairReg] = React.useState(DEFAULT_PAIR_REG)
  const [pairRegDraft, setPairRegDraft] = React.useState(DEFAULT_PAIR_REG)
  const [mainReg, setMainReg] = React.useState(DEFAULT_MAIN_REG)
  const [mainRegDraft, setMainRegDraft] = React.useState(DEFAULT_MAIN_REG)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    setPairs(null)
    const params = format === "All" ? {} : { gameFormat: format }
    Client.getPlayerSynergyApiPlayerRatingsSynergyGet({
      minGamesTogether: minGames,
      regularization: pairReg,
      mainRegularization: mainReg,
      ...params,
    })
      .then(setPairs)
      .catch(showError)
  }, [format, minGames, pairReg, mainReg, showError])

  const visible = React.useMemo(() => {
    if (!pairs) return []
    return significantOnly
      ? pairs.filter((p) => Math.abs(p.zScore) >= SIGNIFICANT_Z)
      : pairs
  }, [pairs, significantOnly])

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h5" gutterBottom>
          Player Synergy
        </Typography>
        <Typography variant="body2" color="text.secondary">
          Do two players win more (or less) often as teammates than their
          individual ratings predict? <b>Synergy</b> is the shift in win
          probability attributable to the pair, on top of what the rating model
          already expects from their matchup. Positive (green) = chemistry,
          negative (red) = anti-synergy. Pairs with little shared history are
          shrunk toward zero, so trust rows with a high |z| and a meaningful
          game count.
        </Typography>
      </Box>

      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        alignItems={{ xs: "flex-start", sm: "center" }}
      >
        <ToggleButtonGroup
          size="small"
          exclusive
          value={format}
          onChange={(_, v) => v && setFormat(v)}
        >
          {FORMAT_OPTIONS.map((f) => (
            <ToggleButton key={f} value={f}>
              {f}
            </ToggleButton>
          ))}
        </ToggleButtonGroup>

        <Stack direction="row" spacing={1} alignItems="center">
          <Typography variant="body2" color="text.secondary">
            Min games together
          </Typography>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={minGames}
            onChange={(_, v) => v && setMinGames(v)}
          >
            {MIN_GAMES_OPTIONS.map((m) => (
              <ToggleButton key={m} value={m}>
                {m}
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Stack>

        <FormControlLabel
          control={
            <Switch
              size="small"
              checked={significantOnly}
              onChange={(e) => setSignificantOnly(e.target.checked)}
            />
          }
          label={`Significant only (|z| ≥ ${SIGNIFICANT_Z})`}
        />

        <RegSlider
          label="Pair shrinkage"
          tooltip="L2 penalty on pair synergy. Higher = more conservative (pulls synergies toward 0)."
          draft={pairRegDraft}
          min={1}
          max={50}
          onDraft={setPairRegDraft}
          onCommit={setPairReg}
        />
        <RegSlider
          label="Main-effect shrinkage"
          tooltip="L2 penalty on per-player main effects. Raise this if Main A·B shows huge values — it stops strong players' main effects running away and saturating the synergy."
          draft={mainRegDraft}
          min={1}
          max={100}
          onDraft={setMainRegDraft}
          onCommit={setMainReg}
        />
      </Stack>

      {!pairs ? (
        <Loading />
      ) : visible.length === 0 ? (
        <Typography variant="body2" color="text.secondary">
          No pairs match the current filters.
        </Typography>
      ) : (
        <SynergyTable pairs={visible} />
      )}
      {errorSnackbar}
    </Stack>
  )
}

// Public, no-controls synergy view for the (non-admin) Rating Trend page: only
// pairs with a strong, well-established effect — at least SIMPLE_MIN_GAMES games
// together and |z| above SIMPLE_MIN_Z — shown as just games + synergy.
const SIMPLE_MIN_GAMES = 10
const SIMPLE_MIN_Z = 1

export function SimplePlayerSynergy() {
  const [pairs, setPairs] = React.useState<PlayerSynergy[] | null>(null)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    Client.getPlayerSynergyApiPlayerRatingsSynergyGet({
      minGamesTogether: SIMPLE_MIN_GAMES,
    })
      .then(setPairs)
      .catch(showError)
  }, [showError])

  if (!pairs) return <Loading />
  const strong = pairs.filter((p) => Math.abs(p.zScore) > SIMPLE_MIN_Z)
  if (strong.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary">
        No pairs yet have enough shared games to show a confident synergy.
      </Typography>
    )
  }

  return (
    <>
      <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
        Pairs who win more (green) or less (red) together than their individual
        ratings predict, with enough shared games to be confident.
      </Typography>
      <TableContainer component={Paper} variant="outlined">
        <Table size="small">
          <TableHead>
            <TableRow>
              <TableCell>Pair</TableCell>
              <TableCell align="right">Games Together</TableCell>
              <TableCell align="right">Synergy</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {strong.map((p) => (
              <TableRow key={`${p.playerA}|${p.playerB}`} hover>
                <PairCell a={p.playerA} b={p.playerB} />
                <TableCell
                  align="right"
                  sx={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {p.gamesTogether}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    fontWeight: "bold",
                    color: p.synergy >= 0 ? WIN_COLOR : LOSS_COLOR,
                  }}
                >
                  {signedPct(p.winProbDelta)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      {errorSnackbar}
    </>
  )
}

function SynergyTable(props: { pairs: PlayerSynergy[] }) {
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>#</TableCell>
            <TableCell>Pair</TableCell>
            <TableCell align="right">
              <MuiTooltip title="Games this pair played on the same team">
                <span>Games</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Games where the two were on opposing teams. A pair that rarely plays apart is the hard-to-identify case — treat its synergy with caution.">
                <span>Apart</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Wins–losses while teamed up">
                <span>W–L</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Actual win rate together vs. the rating model's expected win rate">
                <span>Actual / Exp.</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Baseline the synergy is measured against: expected win rate from rating + each player's individual main effect, with no pair term. The gap between Actual and this is what the synergy explains.">
                <span>Adj. Exp.</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Win-probability shift from the pairing, at an even matchup">
                <span>Synergy</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Each player's individual main effect (log-odds), in pair order. Strongly negative mains cancelled by a large positive synergy = 'much better together than apart'.">
                <span>Main A·B</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Synergy / standard error. |z| ≥ 2 ≈ statistically meaningful">
                <span>z</span>
              </MuiTooltip>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {props.pairs.map((p, i) => {
            const losses = p.gamesTogether - p.winsTogether
            const actualRate = p.winsTogether / p.gamesTogether
            const expectedRate = p.expectedWins / p.gamesTogether
            const adjustedRate = p.adjustedExpectedWins / p.gamesTogether
            const color = p.synergy >= 0 ? WIN_COLOR : LOSS_COLOR
            const significant = Math.abs(p.zScore) >= SIGNIFICANT_Z
            return (
              <TableRow key={`${p.playerA}|${p.playerB}`} hover>
                <TableCell sx={{ color: "text.secondary" }}>{i + 1}</TableCell>
                <PairCell a={p.playerA} b={p.playerB} />
                <TableCell
                  align="right"
                  sx={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {p.gamesTogether}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    color: p.gamesApart === 0 ? LOSS_COLOR : "text.secondary",
                  }}
                >
                  {p.gamesApart}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {p.winsTogether}–{losses}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {pct(actualRate)}{" "}
                  <Typography component="span" color="text.secondary">
                    / {pct(expectedRate)}
                  </Typography>
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    color: "text.secondary",
                  }}
                >
                  {pct(adjustedRate)}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    fontWeight: "bold",
                    color,
                  }}
                >
                  {signedPct(p.winProbDelta)}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    color: "text.secondary",
                  }}
                >
                  {p.mainA.toFixed(1)} · {p.mainB.toFixed(1)}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    fontWeight: significant ? "bold" : "normal",
                    color: significant ? color : "text.secondary",
                  }}
                >
                  {p.zScore.toFixed(1)}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </TableContainer>
  )
}
