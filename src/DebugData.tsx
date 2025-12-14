import Stack from "@mui/material/Stack"
import Skeleton from "@mui/material/Skeleton"
import LinearProgress from "@mui/material/LinearProgress"
import Box from "@mui/material/Box"
import Divider from "@mui/material/Divider"
import Grid from "@mui/material/Grid"
import List from "@mui/material/List"
import ListItem from "@mui/material/ListItem"
import ListItemAvatar from "@mui/material/ListItemAvatar"
import ListItemText from "@mui/material/ListItemText"
import Paper from "@mui/material/Paper"
import Typography from "@mui/material/Typography"
import _ from "lodash"
import * as React from "react"
import DisplayGeneral from "./Generals"
import { GeneralWL, Faction, factionFromJSON, DateMessage } from "./proto/match"
import { toGeneralName } from "./general_utils"

import {
  General,
  GeneralFromJSON,
  instanceOfGeneral,
  PlayerStatOutput,
  PlayerStats,
  WinLoss,
  PlayerRateOverTimeOutput,
  GameRecordOutput,
  MatchListing,
  PlayerListing,
} from "./api"
import { Client } from "./Client"
import Table from '@mui/material/Table';
import Link from '@mui/material/Link';
import TableBody from '@mui/material/TableBody';
import TableCell from '@mui/material/TableCell';
import TableContainer from '@mui/material/TableContainer';
import TableHead from '@mui/material/TableHead';
import TablePagination from '@mui/material/TablePagination';
import TableRow from '@mui/material/TableRow';
import TableSortLabel from '@mui/material/TableSortLabel';
import Toolbar from '@mui/material/Toolbar';
import Tooltip from '@mui/material/Tooltip';

function getGameData(callback: (m: GameRecordOutput[]) => void) {
  Client.listReplaysApiReplaysGet()
    .then(callback)
    .catch((e) => alert(e))
}


function DisplayDataTable(props: { data: GameRecordOutput[] }) {
  const data = props.data
  const columns = [
    { field: "json_s3_uri", headerName: "json_s3_uri" }
  ]
  const first = data[0]
  return (<Box >
    <TableContainer component={Paper}>
      <Table>
        <TableHead>
          <TableRow>
            <TableCell>matchId</TableCell>
            <TableCell>gameDate</TableCell>
            <TableCell>replayFileUrl</TableCell>
            <TableCell>Map</TableCell>
            <TableCell>Winner</TableCell>
            <TableCell>Players</TableCell>
            <TableCell>Incomplete?</TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {data.map((row) => (
            <TableRow>
              <TableCell><Tooltip title={JSON.stringify(row)}><Link>{row.matchId}</Link></Tooltip></TableCell>
              <TableCell>{row.gameDate.toDateString()}</TableCell>
              <TableCell><Link href={row.replayFileUrl}>{row.replayFileUrl.split("/").pop()}</Link></TableCell>
              <TableCell>{row.match?.map}</TableCell>
              <TableCell>{row.match?.winningTeamId}</TableCell>
              <TableCell>{((row.match?.players.map(p => `T${p.teamId}:${p.playerName}`)) ?? []).join(", ")}</TableCell>
              <TableCell>{row.match?.incomplete}</TableCell>
            </TableRow>
          ))}
        </TableBody>

      </Table>
    </TableContainer    >
  </Box>)
}

function Loading() {
  return (
    <Stack>
      <LinearProgress />
      <Stack direction="row">
        <Skeleton variant="rectangular" height={150} />
        <Skeleton variant="rectangular" height={150} />
      </Stack>
    </Stack>
  )
}


export default function DisplayDebugData() {
  const [debugData, setDebugData] = React.useState<GameRecordOutput[]>([])
  React.useEffect(() => {
    getGameData(setDebugData)
  }, [])
  if (debugData.length === 0) {
    return <Loading />
  }
  return (
    <Paper>
      <Typography variant="h4">Stats computed only from 1v1 2v2 3v3 and 4v4 games</Typography>
      <DisplayDataTable data={debugData} />
    </Paper>
  )
}
