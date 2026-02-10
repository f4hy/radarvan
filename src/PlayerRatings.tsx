import Card from '@mui/material/Card';
import CardContent from '@mui/material/CardContent';

import Radio from '@mui/material/Radio';
import RadioGroup from '@mui/material/RadioGroup';
import Slider from '@mui/material/Slider';
import Alert from '@mui/material/Alert';
import Tab from '@mui/material/Tab';
import Tabs from '@mui/material/Tabs';
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import ClearIcon from "@mui/icons-material/Clear"
import CheckIcon from "@mui/icons-material/Check"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Table from "@mui/material/Table"
import Link from "@mui/material/Link"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import Box from "@mui/material/Box"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TablePagination from "@mui/material/TablePagination"
import TableRow from "@mui/material/TableRow"
import Button from "@mui/material/Button"
import Stack from "@mui/material/Stack"
import Skeleton from "@mui/material/Skeleton"
import LinearProgress from "@mui/material/LinearProgress"
import Divider from "@mui/material/Divider"
import FormGroup from "@mui/material/FormGroup"
import FormControlLabel from "@mui/material/FormControlLabel"
import Paper from "@mui/material/Paper"
import Grid from "@mui/material/Grid"
import Checkbox from "@mui/material/Checkbox"
import { ButtonGroup, Chip, Tooltip as MuiTooltip } from "@mui/material"
import { Typography } from "@mui/material"

import * as React from "react"
import {
  Bar,
  BarChart,
  LabelList,
  CartesianGrid,
  ErrorBar,
  Scatter,
  ScatterChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
  ZAxis,
  Legend,
} from "recharts"
import DisplayGeneral from "./Generals"
import {
  General,
  GeneralStat,
  GeneralStats,
  Tournament,
  TournamentResult,
  MatchupResult,
  WinLoss,
  MatchInfo,
  TournamentStat,
  TournamentReport,
  PlayerEnum,
  PlayerRatings,
} from "./api"
import { PlayerEnumFromJSON } from "./api"
import { Client } from "./Client"
import { toGeneralName } from "./general_utils"
import { DisplayMatchInfo } from "./Matches"

const shapes: (
  | "circle"
  | "cross"
  | "diamond"
  | "square"
  | "star"
  | "triangle"
)[] = ["circle", "star", "square", "triangle"]

function getPlayerRatings(
  callback: (m: PlayerRatings[]) => void,
) {
  Client.getPlayerRatingsApiPlayerRatingsGet()
    .then(callback)
    .catch((e) => alert(e))
}

function formatLabel(val: string | number): string {
  if (typeof (val) == 'number') {
    return `${Number(val).toFixed(1)}`;
  }
  return val
}
export default function DisplayPlayerRatings() {
  const [playerRatings, setPlayerRatings] = React.useState<PlayerRatings[]>([])
  React.useEffect(() => {
    getPlayerRatings(setPlayerRatings)
  }, [])

  const data = playerRatings.map((r) => ({ ...r, variance: (r.sigma * r.sigma) }))
  return (
    <Paper sx={{ flexGrow: 1, maxWidth: 2000 }}>
      <Typography variant="h4">Player Ratings (debug only)</Typography>
      <ResponsiveContainer width="100%" height={500}>
        <ScatterChart margin={{ top: 5, right: 10, left: 50, bottom: 5 }}>
          <Scatter
            name="skill"
            data={data}
            shape="triangle"
            fill="blue"
          >
            <LabelList dataKey="ordinal" position="bottom" offset={40} formatter={(s: number) => s.toFixed(2)} fontSize={25} />
            <ErrorBar
              dataKey="sigma"
              width={10}
              strokeWidth={5}
              stroke="skyblue"
              direction="y"
            />
          </Scatter>
          <XAxis
            dataKey="name"
          />
          <YAxis
            label={{
              value: "Estimated Skill",
              position: "insideLeft",
              fontSize: 25,
              strokeFill: "black",
              offset: -10,
              angle: -90,
            }}
            type="number"
            dataKey="mu"
            domain={[0, 50]}

          />
          <ZAxis type="number" range={[100, 100]} />
          <Tooltip
            cursor={{ strokeDasharray: "3 3" }}
            formatter={formatLabel}
          />
          <CartesianGrid />
        </ScatterChart>
      </ResponsiveContainer>
      <ResponsiveContainer width="100%" height={250}>
      <BarChart data={data} layout="horizontal"  margin={{ top: 5, right: 10, left: 50, bottom: 5 }}>
        <CartesianGrid strokeDasharray="5 5" vertical={false} />
        <Bar dataKey="gameCount" fill="#42A5F5" />
        <XAxis dataKey="name" />
        <YAxis
				            label={{
              value: "# games",
              position: "insideLeft",
              fontSize: 25,
              strokeFill: "black",
              offset: -10,
              angle: -90,
            }}
/>
        <Tooltip cursor={false} />
      </BarChart>
      </ResponsiveContainer>
    </Paper>
  )
}
