import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import Button from "@mui/material/Button"
import DownloadIcon from "@mui/icons-material/Download"
import FormGroup from "@mui/material/FormGroup"
import FormControlLabel from "@mui/material/FormControlLabel"
import Stack from "@mui/material/Stack"
import Switch from "@mui/material/Switch"
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
import { Accordion, AccordionSummary, AccordionDetails, TextField } from '@mui/material';
import Typography from "@mui/material/Typography"
import _ from "lodash"
import * as React from "react"
import RefreshIcon from "@mui/icons-material/Refresh"
import DisplayGeneral from "./Generals"
import { GeneralWL, Faction, factionFromJSON, DateMessage } from "./proto/match"
import { toGeneralName } from "./general_utils"

import {
  General,
  GeneralFromJSON,
  instanceOfGeneral,
  PlayerStat,
  PlayerStats,
  WinLoss,
  PlayerRateOverTime,
  GameRecord,
  MatchListing,
  PlayerListing,
} from "./api"
import { Client } from "./Client"
import Table from "@mui/material/Table"
import Link from "@mui/material/Link"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TablePagination from "@mui/material/TablePagination"
import TableRow from "@mui/material/TableRow"
import TableSortLabel from "@mui/material/TableSortLabel"
import Toolbar from "@mui/material/Toolbar"
import Tooltip from "@mui/material/Tooltip"
import { IconButton } from "@mui/material"

function getGameData(matchId: number, callback: (m: GameRecord[]) => void) {
  Client.listReplaysApiReplaysGet({ matchId: matchId })
    .then(callback)
    .catch((e) => alert(e))
}

function getDebugData(matchId: number, callback: (m: { [key: string]: any; }) => void) {
  Client.debugMatchApiDebugMatchMatchIdGet({ matchId: matchId })
    .then(callback)
    .catch((e) => alert(e))
}


function reparse(matchId: number) {
  Client.reparseApiReparseMatchIdPost({ matchId: matchId }).then(() =>
    console.log("Parsed " + matchId),
  )
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

function DownloadButton(props: {
  url: string
  title: string
  text: string
  disabled?: boolean
}) {
  return (
    <Tooltip title={props.title}>
      <Button
        variant="contained"
        onClick={() => downloadReplay(props.url)}
        endIcon={<DownloadIcon />}
        disabled={props.disabled}
      >
        {props.text}
      </Button>
    </Tooltip>
  )
}

function DisplayDataTable(props: {
  data: GameRecord[]
}) {
  const data = props.data
  if (data.length === 0) {
    return <Typography>No matching files</Typography>
  }

  return (
    <Box>
      <TableContainer component={Paper} sx={{ maxHeight: "50%" }}>
        <Table stickyHeader sx={{ maxHeight: "50%" }}>
          <TableHead>
            <TableRow>
              <TableCell>matchId</TableCell>
              <TableCell>gameVersion</TableCell>
              <TableCell>parsed at</TableCell>
              <TableCell>reparse</TableCell>
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
                <TableCell>
                  <Link>{row.matchId}</Link>
                </TableCell>
                <TableCell>
                  {row.gameVersion}
                </TableCell>
                <TableCell>
                  {row.createdAt.toISOString().split("T")[0]}
                </TableCell>
                <TableCell>
                  <IconButton
                    color="primary"
                    onClick={() => reparse(row.matchId)}
                  >
                    <RefreshIcon />
                  </IconButton>
                </TableCell>
                <TableCell>
                  {row.gameDate.toISOString().split("T")[0]}
                </TableCell>
                <TableCell>
                  <DownloadButton
                    url={row.replayFileUrl}
                    title={row.replayFileUrl}
                    text="replay"
                  />
                </TableCell>
                <TableCell>
                  <DownloadButton
                    url={row.jsonS3Uri}
                    title={"soon" + row.jsonS3Uri}
                    text="parsed json"
                    disabled={true}
                  />
                </TableCell>
                <TableCell>{row.match?.durationMinutes.toFixed(1)}</TableCell>
                <TableCell>{row.match?.map}</TableCell>
                <TableCell>{row.match?.winningTeamId}</TableCell>
                <TableCell>
                  {(
                    row.match?.players.map((p) =>
                      p.teamId >= 0 ? `T${p.teamId}:${p.playerName}` : "",
                    ) ?? []
                  ).join(", ")}
                </TableCell>
                <TableCell>{row.match?.incomplete}</TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
    </Box>
  )
}

function JsonDisplay({ data }: { data: any }) {
  if (data === null || data === undefined) {
    return <Typography variant="body2" color="text.secondary" component="span">null</Typography>
  }
  if (typeof data !== "object") {
    return <Typography variant="body2" component="span">{String(data)}</Typography>
  }
  if (Array.isArray(data)) {
    if (data.length === 0) {
      return <Typography variant="body2" color="text.secondary" component="span">[]</Typography>
    }
    return (
      <Box sx={{ pl: 1 }}>
        {data.map((item, i) => (
          <Box key={i} sx={{ display: "flex", gap: 1, alignItems: "flex-start", py: 0.25 }}>
            <Typography variant="caption" color="text.secondary" sx={{ minWidth: 30, flexShrink: 0, pt: 0.3 }}>
              [{i}]
            </Typography>
            <Box sx={{ borderLeft: "2px solid", borderColor: "divider", pl: 1 }}>
              <JsonDisplay data={item} />
            </Box>
          </Box>
        ))}
      </Box>
    )
  }
  const entries = Object.entries(data)
  if (entries.length === 0) {
    return <Typography variant="body2" color="text.secondary" component="span">{"{}"}</Typography>
  }
  return (
    <Box>
      {entries.map(([key, value]) => (
        <Box key={key} sx={{ display: "flex", gap: 1, alignItems: "flex-start", py: 0.25 }}>
          <Typography variant="body2" fontWeight="bold" sx={{ minWidth: 180, flexShrink: 0 }}>
            {key}:
          </Typography>
          {typeof value === "object" && value !== null ? (
            <Box sx={{ borderLeft: "2px solid", borderColor: "divider", pl: 1 }}>
              <JsonDisplay data={value} />
            </Box>
          ) : (
            <Typography variant="body2" component="span">{String(value)}</Typography>
          )}
        </Box>
      ))}
    </Box>
  )
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
  const [debugData, setDebugData] = React.useState<GameRecord[]>([])
  const [matchDebugData, setMatchDebugData] = React.useState<{ [key: string]: any; }>(({}))
  const [jsonDownloadUrl, setJsonDownloadUrl] = React.useState<string | null>(null)
  const [matchId, setMatchId] = React.useState<string | null>(null);
  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value;
    // Replace any non-digit character globally with an empty string
    const onlyNums = newValue.replace(/[^0-9]/g, '');

    setMatchId(onlyNums);
  };

  const submit = () => {
    if (matchId !== null) {
      const num = Number(matchId)
      if (!isNaN(num)) {
        getGameData(num, setDebugData)
        getDebugData(num, setMatchDebugData)
        setJsonDownloadUrl(null)
        Client.getMatchJsonUrlApiDebugJsonUrlMatchIdGet({ matchId: num })
          .then((result) => setJsonDownloadUrl(result["url"]))
          .catch((e) => alert(e))
      }
    }

  }

  return (
    <Paper>
      <Typography variant="h4">
        Listing of all data toggle to show all replays not just 1 per matchid
      </Typography>
      <FormGroup>
        <TextField
          label="matchId"
          value={matchId}
          onChange={handleChange}
          type="text" // Use type="text" to enable maxLength and custom validation
          inputProps={{
            inputMode: 'numeric', // Shows a numeric keyboard on mobile devices
            pattern: '[0-9]*', // Provides a regex pattern hint to the browser
            maxLength: 20 // Example: restricts to a max length of 10 digits
          }}
        />
        <Button onClick={submit} variant="contained">
          submit
        </Button>
      </FormGroup>
      {jsonDownloadUrl && (
        <Box sx={{ p: 1 }}>
          <DownloadButton
            url={jsonDownloadUrl}
            title="Download full parsed replay JSON"
            text="Download Parsed JSON"
          />
        </Box>
      )}
      <DisplayDataTable data={debugData} />
      {
        Object.entries(matchDebugData).map(([name, data]) => (
          <Stack>
            <Accordion defaultExpanded={true}>
              <AccordionSummary
                expandIcon={<ArrowDownwardIcon />}
                sx={{ bgcolor: "text.disabled" }}
              >
                <Typography>
                  {name}
                </Typography>
              </AccordionSummary>
              <AccordionDetails>
                <JsonDisplay data={data} />
              </AccordionDetails>
            </Accordion>
          </Stack>
        )

        )
      }
    </Paper>
  )
}
