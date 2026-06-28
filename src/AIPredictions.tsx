import * as React from "react"
import Box from "@mui/material/Box"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import Paper from "@mui/material/Paper"
import Divider from "@mui/material/Divider"
import LinearProgress from "@mui/material/LinearProgress"
import Alert from "@mui/material/Alert"
import Chip from "@mui/material/Chip"
import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Client } from "./Client"
import { MatchPrediction, WinProbOverTime } from "./api"
import Loading from "./Loading"

const TEAM_A_COLOR = "#1976d2"
const TEAM_B_COLOR = "#d32f2f"

function fmtPct(p: number): string {
  return `${(p * 100).toFixed(0)}%`
}

function describeError(e: unknown): string {
  const status =
    typeof e === "object" && e !== null && "response" in e
      ? (e as { response?: { status?: number } }).response?.status
      : undefined
  if (status === 503)
    return "The prediction model isn't deployed on this server yet."
  if (status === 404) return "Match not found."
  if (status === 422)
    return "This match isn't a two-team game, so the models can't score it."
  return "Could not load prediction."
}

function PregamePrediction(props: { pred: MatchPrediction }) {
  const { pred } = props
  const probA = pred.probTeamAWins
  const favoredA = pred.favoredTeam === pred.teamA
  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom>
        Pre-game prediction
      </Typography>
      <Typography variant="caption" color="text.secondary">
        From the outcome model — players, generals, factions and map only (no
        in-game events).
      </Typography>
      <Stack spacing={1.5} sx={{ mt: 1.5 }}>
        <Stack direction="row" justifyContent="space-between">
          <Typography sx={{ color: TEAM_A_COLOR, fontWeight: "bold" }}>
            Team A: {pred.teamAPlayers.join(", ")}
          </Typography>
          <Typography sx={{ color: TEAM_A_COLOR }}>{fmtPct(probA)}</Typography>
        </Stack>
        {/* Probability bar: filled portion = P(Team A wins). */}
        <Box
          sx={{
            position: "relative",
            height: 14,
            borderRadius: 1,
            overflow: "hidden",
            bgcolor: TEAM_B_COLOR,
          }}
        >
          <Box
            sx={{
              position: "absolute",
              inset: 0,
              width: `${probA * 100}%`,
              bgcolor: TEAM_A_COLOR,
            }}
          />
        </Box>
        <Stack direction="row" justifyContent="space-between">
          <Typography sx={{ color: TEAM_B_COLOR, fontWeight: "bold" }}>
            Team B: {pred.teamBPlayers.join(", ")}
          </Typography>
          <Typography sx={{ color: TEAM_B_COLOR }}>
            {fmtPct(1 - probA)}
          </Typography>
        </Stack>
        <Typography variant="body2">
          Favored:{" "}
          <strong style={{ color: favoredA ? TEAM_A_COLOR : TEAM_B_COLOR }}>
            Team {favoredA ? "A" : "B"}
          </strong>{" "}
          ({fmtPct(pred.favoredWinProb)})
        </Typography>
        {pred.unknownPlayers && pred.unknownPlayers.length > 0 && (
          <Typography variant="caption" color="text.secondary">
            Unknown to the model (weak signal): {pred.unknownPlayers.join(", ")}
          </Typography>
        )}
      </Stack>
    </Box>
  )
}

function OverTimePrediction(props: { data: WinProbOverTime }) {
  const { data } = props
  const chart = React.useMemo(
    () =>
      data.points.map((p) => ({
        minute: Number(p.atMinute.toFixed(2)),
        prob: p.probTeamA * 100,
      })),
    [data.points],
  )
  const winner =
    data.actualWinner === "team_a"
      ? "Team A"
      : data.actualWinner === "team_b"
        ? "Team B"
        : null
  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom>
        Win probability over time
      </Typography>
      <Typography variant="caption" color="text.secondary">
        From the sequence model — updates as the match unfolds (builds, kills,
        captures, economy). Shows P(Team A wins) at each point in the game.
      </Typography>
      <Box sx={{ width: "100%", height: 300, mt: 1.5 }}>
        <ResponsiveContainer>
          <LineChart
            data={chart}
            margin={{ top: 8, right: 16, bottom: 8, left: 0 }}
          >
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="minute"
              type="number"
              domain={[0, "dataMax"]}
              tickFormatter={(m: number) => `${m.toFixed(0)}m`}
            />
            <YAxis domain={[0, 100]} tickFormatter={(v: number) => `${v}%`} />
            <Tooltip
              formatter={(v) => [`${Number(v).toFixed(0)}%`, "P(Team A wins)"]}
              labelFormatter={(label) => `${Number(label).toFixed(1)} min`}
            />
            <ReferenceLine y={50} stroke="#888" strokeDasharray="4 4" />
            <Line
              type="monotone"
              dataKey="prob"
              stroke={TEAM_A_COLOR}
              strokeWidth={2}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </Box>
      <Stack direction="row" spacing={1} alignItems="center" sx={{ mt: 1 }}>
        <Typography variant="caption" color="text.secondary">
          Line above 50% favors{" "}
          <span style={{ color: TEAM_A_COLOR }}>Team A</span>; below favors{" "}
          <span style={{ color: TEAM_B_COLOR }}>Team B</span>.
        </Typography>
        {winner && (
          <Chip
            size="small"
            label={`Actual winner: ${winner}`}
            color={data.actualWinner === "team_a" ? "primary" : "error"}
            variant="outlined"
          />
        )}
      </Stack>
    </Box>
  )
}

export default function AIPredictions(props: { matchId: number }) {
  const [pregame, setPregame] = React.useState<MatchPrediction | null>(null)
  const [overTime, setOverTime] = React.useState<WinProbOverTime | null>(null)
  const [pregameErr, setPregameErr] = React.useState<string | null>(null)
  const [overTimeErr, setOverTimeErr] = React.useState<string | null>(null)
  const [loading, setLoading] = React.useState(true)

  React.useEffect(() => {
    let cancelled = false
    setLoading(true)
    setPregame(null)
    setOverTime(null)
    setPregameErr(null)
    setOverTimeErr(null)
    const p1 = Client.predictMatchApiPredictMatchMatchIdGet({
      matchId: props.matchId,
    })
      .then((r) => {
        if (!cancelled) setPregame(r)
      })
      .catch((e) => {
        if (!cancelled) setPregameErr(describeError(e))
      })
    const p2 = Client.predictOverTimeApiPredictOverTimeMatchIdGet({
      matchId: props.matchId,
    })
      .then((r) => {
        if (!cancelled) setOverTime(r)
      })
      .catch((e) => {
        if (!cancelled) setOverTimeErr(describeError(e))
      })
    Promise.allSettled([p1, p2]).then(() => {
      if (!cancelled) setLoading(false)
    })
    return () => {
      cancelled = true
    }
  }, [props.matchId])

  if (loading) {
    return (
      <Box sx={{ p: 2 }}>
        <LinearProgress />
        <Loading />
      </Box>
    )
  }

  return (
    <Stack spacing={2} sx={{ maxWidth: 760 }}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        {pregame ? (
          <PregamePrediction pred={pregame} />
        ) : (
          <Alert severity="info">
            {pregameErr ?? "No pre-game prediction."}
          </Alert>
        )}
      </Paper>
      <Divider />
      <Paper variant="outlined" sx={{ p: 2 }}>
        {overTime ? (
          <OverTimePrediction data={overTime} />
        ) : (
          <Alert severity="info">
            {overTimeErr ?? "No over-time prediction."}
          </Alert>
        )}
      </Paper>
    </Stack>
  )
}
