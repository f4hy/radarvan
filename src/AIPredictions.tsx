import * as React from "react"
import Box from "@mui/material/Box"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import Paper from "@mui/material/Paper"
import Divider from "@mui/material/Divider"
import Alert from "@mui/material/Alert"
import Chip from "@mui/material/Chip"
import { useTheme } from "@mui/material/styles"
import {
  Area,
  AreaChart,
  CartesianGrid,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Client } from "./Client"
import { MatchPrediction, ResponseError, WinProbOverTime } from "./api"
import { formatPercent } from "./utils"
import WinShareBar from "./WinShareBar"
import Loading from "./Loading"

// A panel's data once its fetch settles: the result, or a friendly error.
type Panel<T> = T | { error: string }

function describeError(e: unknown): string {
  const status = e instanceof ResponseError ? e.response.status : undefined
  if (status === 503)
    return "The prediction model isn't deployed on this server yet."
  if (status === 404) return "Match not found."
  if (status === 422)
    return "This match isn't a two-team game, so the models can't score it."
  return "Could not load prediction."
}

function PregamePrediction(props: { pred: MatchPrediction }) {
  const theme = useTheme()
  const teamA = theme.palette.primary.main
  const teamB = theme.palette.error.main
  const { pred } = props
  const probA = pred.probTeamAWins
  const favoredA = pred.favoredTeam === pred.teamA
  return (
    <Box>
      <Typography variant="subtitle1" gutterBottom>
        Pre-game prediction
      </Typography>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
        }}
      >
        From the outcome model — players, generals, factions and map only (no
        in-game events).
      </Typography>
      <Stack spacing={1.5} sx={{ mt: 1.5 }}>
        <Stack
          direction="row"
          sx={{
            justifyContent: "space-between",
          }}
        >
          <Typography sx={{ color: teamA, fontWeight: "bold" }}>
            Team A: {pred.teamAPlayers.join(", ")}
          </Typography>
          <Typography sx={{ color: teamA }}>{formatPercent(probA)}</Typography>
        </Stack>
        {/* Probability bar: filled portion = P(Team A wins). */}
        <WinShareBar fraction={probA} leftColor={teamA} rightColor={teamB} />
        <Stack
          direction="row"
          sx={{
            justifyContent: "space-between",
          }}
        >
          <Typography sx={{ color: teamB, fontWeight: "bold" }}>
            Team B: {pred.teamBPlayers.join(", ")}
          </Typography>
          <Typography sx={{ color: teamB }}>
            {formatPercent(1 - probA)}
          </Typography>
        </Stack>
        <Typography variant="body2">
          Favored:{" "}
          <strong style={{ color: favoredA ? teamA : teamB }}>
            Team {favoredA ? "A" : "B"}
          </strong>{" "}
          ({formatPercent(pred.favoredWinProb)})
        </Typography>
        {pred.unknownPlayers && pred.unknownPlayers.length > 0 && (
          <Typography
            variant="caption"
            sx={{
              color: "text.secondary",
            }}
          >
            Unknown to the model (weak signal): {pred.unknownPlayers.join(", ")}
          </Typography>
        )}
      </Stack>
    </Box>
  )
}

function OverTimePrediction(props: { data: WinProbOverTime }) {
  const theme = useTheme()
  const teamA = theme.palette.primary.main
  const teamB = theme.palette.error.main
  const { data } = props
  const chart = React.useMemo(
    () =>
      data.points.map((p) => ({
        minute: Number(p.atMinute.toFixed(2)),
        probA: p.probTeamA * 100,
        probB: (1 - p.probTeamA) * 100,
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
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
        }}
      >
        From the sequence model — updates as the match unfolds (builds, kills,
        captures, economy). Shows P(Team A wins) at each point in the game.
      </Typography>
      <Box sx={{ width: "100%", height: 300, mt: 1.5 }}>
        <ResponsiveContainer>
          <AreaChart
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
              formatter={(v, name) => [
                `${Number(v).toFixed(0)}%`,
                name === "probA" ? "Team A" : "Team B",
              ]}
              labelFormatter={(label) => `${Number(label).toFixed(1)} min`}
            />
            <ReferenceLine
              y={50}
              stroke="#fff"
              strokeWidth={1.5}
              strokeDasharray="4 4"
            />
            {/* Stacked + expanded: blue fills up to P(Team A), red fills the
                rest, so the boundary between them is the win probability. */}
            <Area
              type="monotone"
              dataKey="probA"
              stackId="prob"
              stroke={teamA}
              fill={teamA}
              fillOpacity={0.75}
              strokeWidth={2}
              isAnimationActive={false}
            />
            <Area
              type="monotone"
              dataKey="probB"
              stackId="prob"
              stroke={teamB}
              fill={teamB}
              fillOpacity={0.75}
              strokeWidth={0}
              isAnimationActive={false}
            />
          </AreaChart>
        </ResponsiveContainer>
      </Box>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          mt: 1,
        }}
      >
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
          }}
        >
          Line above 50% favors <span style={{ color: teamA }}>Team A</span>;
          below favors <span style={{ color: teamB }}>Team B</span>.
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
  const [pregame, setPregame] = React.useState<Panel<MatchPrediction> | null>(
    null,
  )
  const [overTime, setOverTime] = React.useState<Panel<WinProbOverTime> | null>(
    null,
  )

  React.useEffect(() => {
    let cancelled = false
    setPregame(null)
    setOverTime(null)
    Client.predictMatchApiPredictMatchMatchIdGet({ matchId: props.matchId })
      .then((r) => !cancelled && setPregame(r))
      .catch((e) => !cancelled && setPregame({ error: describeError(e) }))
    Client.predictOverTimeApiPredictOverTimeMatchIdGet({
      matchId: props.matchId,
    })
      .then((r) => !cancelled && setOverTime(r))
      .catch((e) => !cancelled && setOverTime({ error: describeError(e) }))
    return () => {
      cancelled = true
    }
  }, [props.matchId])

  if (pregame === null || overTime === null) {
    return <Loading />
  }

  return (
    <Stack spacing={2} sx={{ maxWidth: 760 }}>
      <Paper variant="outlined" sx={{ p: 2 }}>
        {"error" in pregame ? (
          <Alert severity="info">{pregame.error}</Alert>
        ) : (
          <PregamePrediction pred={pregame} />
        )}
      </Paper>
      <Divider />
      <Paper variant="outlined" sx={{ p: 2 }}>
        {"error" in overTime ? (
          <Alert severity="info">{overTime.error}</Alert>
        ) : (
          <OverTimePrediction data={overTime} />
        )}
      </Paper>
    </Stack>
  )
}
