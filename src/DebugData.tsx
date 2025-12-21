import Button from "@mui/material/Button"
import DownloadIcon from "@mui/icons-material/Download"
import FormGroup from '@mui/material/FormGroup';
import FormControlLabel from '@mui/material/FormControlLabel';
import Stack from "@mui/material/Stack"
import Switch from '@mui/material/Switch';
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
function downloadURI(uri: string, name: string) {
  var link = document.createElement("a")
  link.download = name
  link.href = uri
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function downloadReplay(url: string) {
  const filename = url.split("/").pop()
  if (filename) {
    downloadURI(url, filename)
  }
}

function DownloadButton(props: { url: string, title: string, text: string, disabled?: boolean  }) {
  return (<Tooltip title={props.title}>
    <Button
      variant="contained"
      onClick={() => downloadReplay(props.url)}
      endIcon={<DownloadIcon />}
			disabled={props.disabled}
    >
      {props.text}
    </Button>
  </Tooltip>)
}

function DisplayDataTable(props: { data: GameRecordOutput[], exclude_unparsed: boolean }) {
  const data = props.exclude_unparsed ? props.data.filter((d => d.match)) : props.data
  const columns = [
    { field: "json_s3_uri", headerName: "json_s3_uri" }
  ]
  const first = data[0]
  return (<Box >
    <TableContainer component={Paper} sx={{ maxHeight: "50%" }}>
      <Table stickyHeader sx={{ maxHeight: "50%" }}>
        <TableHead>
          <TableRow>
            <TableCell>matchId</TableCell>
            <TableCell>gameDate</TableCell>
            <TableCell>replayFileUrl</TableCell>
            <TableCell>Prased Json</TableCell>
            <TableCell>Duration minutes</TableCell>
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
              <TableCell>{row.gameDate.toISOString().split('T')[0]}</TableCell>
              <TableCell>
                <DownloadButton url={row.replayFileUrl} title={row.replayFileUrl} text="replay" />
              </TableCell>
              <TableCell>
              <DownloadButton url={row.jsonS3Uri} title={"soon" + row.jsonS3Uri} text="parsed json" disabled={true} />
              </TableCell>
              <TableCell>{row.match?.durationMinutes.toFixed(1)}</TableCell>
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
  const [checked, setChecked] = React.useState(true);
  React.useEffect(() => {
    getGameData(setDebugData)
  }, [])
  if (debugData.length === 0) {
    return <Loading />
  }
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    setChecked(event.target.checked);
  };

  return (
    <Paper>
      <Typography variant="h4">Listing of all data toggle to show all replays not just 1 per matchid</Typography>
      <FormGroup>
        <FormControlLabel control={<Switch
          checked={checked}
          onChange={handleChange}
        />}
          label="Toggle on shows just one replay per match"
        />
      </FormGroup>
      <DisplayDataTable data={debugData} exclude_unparsed={checked} />
    </Paper>
  )
}
