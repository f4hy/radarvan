import { useQuery } from "@tanstack/react-query"
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
import Typography from "@mui/material/Typography"
import { Tooltip as MuiTooltip } from "@mui/material"

import type { PlayerSynergy } from "../../api/types.gen"
import { getPlayerSynergyApiPlayerRatingsSynergyGetOptions } from "../../api/@tanstack/react-query.gen"
import QueryState from "../../components/QueryState"
import { PlayerLabel } from "../../components/PlayerChip"
import { WIN_COLOR, LOSS_COLOR } from "../../lib/theme"
import { useUrlChoice, useUrlFlag } from "../../lib/useUrlState"

const FORMAT_OPTIONS = ["All", "2v2", "3v3", "4v4"] as const
type GameFormat = (typeof FORMAT_OPTIONS)[number]

const MIN_GAMES_OPTIONS = [3, 5, 10] as const
const SIGNIFICANT_Z = 2

// Win-rate difference in percentage points.
function signedPp(x: number | null | undefined): string {
  if (x == null) return "—"
  return `${x >= 0 ? "+" : ""}${(x * 100).toFixed(1)}pp`
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
        sx={{
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <PlayerLabel name={props.a} />
        <Typography
          component="span"
          sx={{
            color: "text.secondary",
          }}
        >
          +
        </Typography>
        <PlayerLabel name={props.b} />
      </Stack>
    </TableCell>
  )
}

export default function DisplayPlayerSynergy() {
  const [format, setFormat] = useUrlChoice<GameFormat>(
    "format",
    FORMAT_OPTIONS,
    "All",
  )
  const [minGames, setMinGames] = useUrlChoice("minGames", MIN_GAMES_OPTIONS, 3)
  const [significantOnly, setSignificantOnly] = useUrlFlag("significant")

  const query = useQuery(
    getPlayerSynergyApiPlayerRatingsSynergyGetOptions({
      query: {
        min_games_together: minGames,
        ...(format === "All" ? {} : { game_format: format }),
      },
    }),
  )
  const pairs = query.data

  const visible = React.useMemo(() => {
    if (!pairs) return []
    return significantOnly
      ? pairs.filter((p) => Math.abs(p.z_score) >= SIGNIFICANT_Z)
      : pairs
  }, [pairs, significantOnly])

  return (
    <Stack spacing={2}>
      <Box>
        <Typography variant="h5" gutterBottom>
          Player Synergy
        </Typography>
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
          }}
        >
          Do two players win more (or less) often as teammates than the rating
          model expected? Before each game we record the team's win probability
          from the ratings at that moment; a pair's <b>synergy</b> is its wins
          together minus the sum of those probabilities, per game. Every pair on
          a team shares the team's result, so a player who keeps beating their
          rating lifts all their pairs — compare against <b>Solo</b>, each
          player's same measure in games without the other. Sorted by <b>z</b>{" "}
          (excess wins over the model's standard deviation), so small samples
          don't dominate. Ratings are replayed over every format, so a 2v2 view
          still uses earlier 3v3/4v4 history.
        </Typography>
      </Box>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={2}
        sx={{
          alignItems: { xs: "flex-start", sm: "center" },
        }}
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

        <Stack
          direction="row"
          spacing={1}
          sx={{
            alignItems: "center",
          }}
        >
          <Typography
            variant="body2"
            sx={{
              color: "text.secondary",
            }}
          >
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
      </Stack>
      <QueryState query={query} what="synergy">
        {() =>
          visible.length === 0 ? (
            <Typography
              variant="body2"
              sx={{
                color: "text.secondary",
              }}
            >
              No pairs match the current filters.
            </Typography>
          ) : (
            <SynergyTable pairs={visible} />
          )
        }
      </QueryState>
    </Stack>
  )
}

// Public, no-controls synergy view for the (non-admin) Rating Trend page: only
// pairs with a strong, well-established effect — at least SIMPLE_MIN_GAMES games
// together and |z| above SIMPLE_MIN_Z — shown as just games + synergy.
const SIMPLE_MIN_GAMES = 10
const SIMPLE_MIN_Z = 2

export function SimplePlayerSynergy() {
  const query = useQuery(
    getPlayerSynergyApiPlayerRatingsSynergyGetOptions({
      query: { min_games_together: SIMPLE_MIN_GAMES },
    }),
  )

  if (query.isPending || query.isError) {
    return (
      <QueryState query={query} what="synergy">
        {() => null}
      </QueryState>
    )
  }
  const pairs = query.data
  const strong = pairs.filter((p) => Math.abs(p.z_score) >= SIMPLE_MIN_Z)
  if (strong.length === 0) {
    return (
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
        }}
      >
        No pairs yet have enough shared games to show a confident synergy.
      </Typography>
    )
  }

  return (
    <>
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
          mb: 1,
        }}
      >
        Pairs who win more (green) or less (red) together than the rating model
        expected, with enough shared games to be confident.
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
              <TableRow key={`${p.player_a}|${p.player_b}`} hover>
                <PairCell a={p.player_a} b={p.player_b} />
                <TableCell
                  align="right"
                  sx={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {p.games_together}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    fontWeight: "bold",
                    color: p.win_rate_delta >= 0 ? WIN_COLOR : LOSS_COLOR,
                  }}
                >
                  {signedPp(p.win_rate_delta)}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
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
              <MuiTooltip title="Wins–losses while teamed up">
                <span>W–L</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Actual win rate together vs. the average pregame win probability">
                <span>Actual / Exp.</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Wins together minus expected wins">
                <span>Excess</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Win rate above expectation, per game together">
                <span>Synergy</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Each player's win rate above expectation in games without the other, in pair order. A pair's synergy close to the sum of these is mostly the players, not the pairing. — means too few games apart.">
                <span>Solo A · B</span>
              </MuiTooltip>
            </TableCell>
            <TableCell align="right">
              <MuiTooltip title="Excess wins / the model's standard deviation of wins. |z| ≥ 2 ≈ statistically meaningful">
                <span>z</span>
              </MuiTooltip>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {props.pairs.map((p, i) => {
            const losses = p.games_together - p.wins_together
            const actualRate = p.wins_together / p.games_together
            const expectedRate = p.expected_wins / p.games_together
            const color = p.win_rate_delta >= 0 ? WIN_COLOR : LOSS_COLOR
            const significant = Math.abs(p.z_score) >= SIGNIFICANT_Z
            return (
              <TableRow key={`${p.player_a}|${p.player_b}`} hover>
                <TableCell sx={{ color: "text.secondary" }}>{i + 1}</TableCell>
                <PairCell a={p.player_a} b={p.player_b} />
                <TableCell
                  align="right"
                  sx={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {p.games_together}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {p.wins_together}–{losses}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{ fontVariantNumeric: "tabular-nums" }}
                >
                  {pct(actualRate)}{" "}
                  <Typography
                    component="span"
                    sx={{
                      color: "text.secondary",
                    }}
                  >
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
                  {p.excess_wins >= 0 ? "+" : ""}
                  {p.excess_wins.toFixed(1)}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    fontWeight: "bold",
                    color,
                  }}
                >
                  {signedPp(p.win_rate_delta)}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    color: "text.secondary",
                  }}
                >
                  {signedPp(p.solo_a)} · {signedPp(p.solo_b)}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    fontVariantNumeric: "tabular-nums",
                    fontWeight: significant ? "bold" : "normal",
                    color: significant ? color : "text.secondary",
                  }}
                >
                  {p.z_score.toFixed(1)}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </TableContainer>
  )
}
