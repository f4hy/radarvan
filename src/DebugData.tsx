import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import Button from "@mui/material/Button"
import DownloadIcon from "@mui/icons-material/Download"
import FormGroup from "@mui/material/FormGroup"
import Stack from "@mui/material/Stack"
import Box from "@mui/material/Box"
import Paper from "@mui/material/Paper"
import {
  Accordion,
  AccordionSummary,
  AccordionDetails,
  TextField,
} from "@mui/material"
import Typography from "@mui/material/Typography"
import * as React from "react"
import RefreshIcon from "@mui/icons-material/Refresh"
import { GameRecord, MatchInfo } from "./api"
import { Client } from "./Client"
import { DisplayMatchInfo } from "./Matches"
import Table from "@mui/material/Table"
import Link from "@mui/material/Link"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import Tooltip from "@mui/material/Tooltip"
import { IconButton } from "@mui/material"
import { useErrorSnackbar } from "./useErrorSnackbar"

function getGameData(
  matchId: number,
  callback: (m: GameRecord[]) => void,
  onError = console.error,
) {
  Client.listReplaysApiReplaysGet({ matchId: matchId })
    .then(callback)
    .catch(onError)
}

function getDebugData(
  matchId: number,
  callback: (m: { [key: string]: unknown }) => void,
  onError = console.error,
) {
  Client.debugMatchApiDebugMatchMatchIdGet({ matchId: matchId })
    .then(callback)
    .catch(onError)
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

function DisplayDataTable(props: { data: GameRecord[] }) {
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
              <TableRow key={row.matchId}>
                <TableCell>
                  <Link>{row.matchId}</Link>
                </TableCell>
                <TableCell>{row.gameVersion}</TableCell>
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

function JsonArray({ data }: { data: unknown[] }) {
  if (data.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" component="span">
        []
      </Typography>
    )
  }
  return (
    <Box sx={{ pl: 1 }}>
      {data.map((item, i) => (
        <Box
          key={i}
          sx={{ display: "flex", gap: 1, alignItems: "flex-start", py: 0.25 }}
        >
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ minWidth: 30, flexShrink: 0, pt: 0.3 }}
          >
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

function JsonObject({ data }: { data: Record<string, unknown> }) {
  const entries = Object.entries(data)
  if (entries.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" component="span">
        {"{}"}
      </Typography>
    )
  }
  return (
    <Box>
      {entries.map(([key, value]) => (
        <Box
          key={key}
          sx={{ display: "flex", gap: 1, alignItems: "flex-start", py: 0.25 }}
        >
          <Typography
            variant="body2"
            fontWeight="bold"
            sx={{ minWidth: 180, flexShrink: 0 }}
          >
            {key}:
          </Typography>
          {typeof value === "object" && value !== null ? (
            <Box
              sx={{ borderLeft: "2px solid", borderColor: "divider", pl: 1 }}
            >
              <JsonDisplay data={value} />
            </Box>
          ) : (
            <Typography variant="body2" component="span">
              {String(value)}
            </Typography>
          )}
        </Box>
      ))}
    </Box>
  )
}

function JsonDisplay({ data }: { data: unknown }) {
  if (data === null || data === undefined) {
    return (
      <Typography variant="body2" color="text.secondary" component="span">
        null
      </Typography>
    )
  }
  if (typeof data !== "object") {
    return (
      <Typography variant="body2" component="span">
        {String(data)}
      </Typography>
    )
  }
  if (Array.isArray(data)) {
    return <JsonArray data={data} />
  }
  return <JsonObject data={data as Record<string, unknown>} />
}

function MatchIdInput(props: {
  value: string | null
  onChange: (event: React.ChangeEvent<HTMLInputElement>) => void
  onSubmit: () => void
}) {
  return (
    <FormGroup>
      <TextField
        label="matchId"
        value={props.value}
        onChange={props.onChange}
        type="text"
        inputProps={{
          inputMode: "numeric",
          pattern: "[0-9]*",
          maxLength: 20,
        }}
      />
      <Button onClick={props.onSubmit} variant="contained">
        submit
      </Button>
    </FormGroup>
  )
}

export default function DisplayDebugData() {
  const [debugData, setDebugData] = React.useState<GameRecord[]>([])
  const [matchDebugData, setMatchDebugData] = React.useState<{
    [key: string]: unknown
  }>({})
  const [jsonDownloadUrl, setJsonDownloadUrl] = React.useState<string | null>(
    null,
  )
  const [matchId, setMatchId] = React.useState<string | null>(null)
  const [matchInfo, setMatchInfo] = React.useState<MatchInfo | null>(null)
  const { showError, errorSnackbar } = useErrorSnackbar()

  const handleChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = event.target.value
    // Replace any non-digit character globally with an empty string
    const onlyNums = newValue.replace(/[^0-9]/g, "")

    setMatchId(onlyNums)
  }

  const submit = () => {
    if (matchId !== null) {
      const num = Number(matchId)
      if (!isNaN(num)) {
        getGameData(num, setDebugData, showError)
        getDebugData(num, setMatchDebugData, showError)
        setMatchInfo(null)
        Client.getMatchByIdApiMatchMatchIdGet({ matchId: num })
          .then(setMatchInfo)
          .catch(showError)
        setJsonDownloadUrl(null)
        Client.getMatchJsonUrlApiDebugJsonUrlMatchIdGet({ matchId: num })
          .then((result) => setJsonDownloadUrl(result["url"]))
          .catch(showError)
      }
    }
  }

  return (
    <Paper>
      <Typography variant="h4">
        Listing of all data toggle to show all replays not just 1 per matchid
      </Typography>
      <MatchIdInput value={matchId} onChange={handleChange} onSubmit={submit} />
      {jsonDownloadUrl && (
        <Box sx={{ p: 1 }}>
          <DownloadButton
            url={jsonDownloadUrl}
            title="Download full parsed replay JSON"
            text="Download Parsed JSON"
          />
        </Box>
      )}
      {matchInfo && <DisplayMatchInfo match={matchInfo} idx={0} />}
      <DisplayDataTable data={debugData} />
      {Object.entries(matchDebugData).map(([name, data]) => (
        <Stack key={name}>
          <Accordion defaultExpanded={true}>
            <AccordionSummary
              expandIcon={<ArrowDownwardIcon />}
              sx={{ bgcolor: "text.disabled" }}
            >
              <Typography>{name}</Typography>
            </AccordionSummary>
            <AccordionDetails>
              <JsonDisplay data={data} />
            </AccordionDetails>
          </Accordion>
        </Stack>
      ))}
      {errorSnackbar}
    </Paper>
  )
}
