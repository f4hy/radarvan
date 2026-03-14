import Autocomplete from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import IconButton from "@mui/material/IconButton"
import Paper from "@mui/material/Paper"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TextField from "@mui/material/TextField"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import BalanceIcon from "@mui/icons-material/Balance"
import CasinoIcon from "@mui/icons-material/Casino"
import CloseIcon from "@mui/icons-material/Close"
import PersonAddIcon from "@mui/icons-material/PersonAdd"
import LinearProgress from "@mui/material/LinearProgress"
import Stack from "@mui/material/Stack"
import * as React from "react"
import type { DraftAssignment, MapDataPayload } from "./api"
import { PlayerEnum } from "./api"
import { Client } from "./Client"
import { ScoreBar } from "./BalanceTeams"
import DisplayGeneral from "./Generals"
import Map from "./Map"
import { MAPLIST } from "./maplist"
interface DraftPlayer {
  id: number
  name: string
  team: 1 | 2 | 3 | 4
}

const TEAM_COLORS: Record<1 | 2 | 3 | 4, string> = {
  1: "#2196F3",
  2: "#F44336",
  3: "#4CAF50",
  4: "#FF9800",
}

function mapDisplayName(filename: string): string {
  // Strip userdata_maps_ or maps_ prefix, then remove doubled suffix
  let stem = filename.replace(/\.webp$/, "")
  if (stem.startsWith("userdata_maps_")) {
    stem = stem.slice("userdata_maps_".length)
  } else if (stem.startsWith("maps_")) {
    stem = stem.slice("maps_".length)
  }
  // Remove doubled suffix: "defcon6_defcon6" -> "defcon6"
  const parts = stem.split("_")
  const half = parts.length / 2
  if (
    parts.length >= 2 &&
    parts.length % 2 === 0 &&
    parts.slice(0, half).join("_") === parts.slice(half).join("_")
  ) {
    stem = parts.slice(0, half).join("_")
  }
  return stem
}

function mapApiName(filename: string): string {
  return mapDisplayName(filename)
}

let nextId = 1

export default function DisplayDraft() {
  const [selectedMap, setSelectedMap] = React.useState<string | null>(null)
  const [players, setPlayers] = React.useState<DraftPlayer[]>([])
  const [mapData, setMapData] = React.useState<MapDataPayload | null>(null)
  const [assignments, setAssignments] = React.useState<DraftAssignment[]>([])
  const [randomizedAt, setRandomizedAt] = React.useState<string | null>(null)
  const [teamRating, setTeamRating] = React.useState<Record<
    string,
    number
  > | null>(null)
  const [balanceLoading, setBalanceLoading] = React.useState(false)

  React.useEffect(() => {
    setMapData(null)
    setPlayers([])
    setAssignments([])
    setRandomizedAt(null)
    if (!selectedMap) return
    const apiName = mapApiName(selectedMap)
    Client.getMapDataApiMapDataMapNameGet({ mapName: apiName }).then(
      (data) => {
        setMapData(data)
        const count = data.playerStarts.length
        setPlayers(
          Array.from({ length: count }, (_, i) => ({
            id: nextId++,
            name: `Player ${i + 1}`,
            team: (i < Math.ceil(count / 2) ? 1 : 2) as 1 | 2,
          })),
        )
      },
      () => {
        setMapData(null)
        setPlayers([])
      },
    )
  }, [selectedMap])

  React.useEffect(() => {
    setTeamRating(null)
  }, [players])

  function checkBalance() {
    const team1 = players
      .filter((p) => p.team === 1)
      .map((p) => p.name as PlayerEnum)
    const team2 = players
      .filter((p) => p.team === 2)
      .map((p) => p.name as PlayerEnum)
    setBalanceLoading(true)
    setTeamRating(null)
    Client.balanceTeamsApiBalanceTeamsGet({
      players: [...team1, ...team2],
    }).then(
      (data) => {
        setTeamRating(data)
        setBalanceLoading(false)
      },
      () => setBalanceLoading(false),
    )
  }

  function addPlayer() {
    setPlayers((prev) => [
      ...prev,
      { id: nextId++, name: `Player ${nextId - 1}`, team: 1 },
    ])
  }

  function removePlayer(id: number) {
    setPlayers((prev) => prev.filter((p) => p.id !== id))
    setAssignments([])
    setRandomizedAt(null)
  }

  function updatePlayerName(id: number, name: string) {
    setPlayers((prev) => prev.map((p) => (p.id === id ? { ...p, name } : p)))
  }

  function updatePlayerTeam(id: number, team: 1 | 2 | 3 | 4) {
    setPlayers((prev) => prev.map((p) => (p.id === id ? { ...p, team } : p)))
    setAssignments([])
    setRandomizedAt(null)
  }

  function applyMostBalanced() {
    if (!teamRating) return
    const best = Object.entries(teamRating).reduce((a, b) =>
      Math.abs(a[1] - 0.5) < Math.abs(b[1] - 0.5) ? a : b,
    )
    const newTeam1 = new Set(best[0].split(","))
    setPlayers((prev) =>
      prev.map((p) => ({
        ...p,
        team: (newTeam1.has(p.name) ? 1 : 2) as 1 | 2,
      })),
    )
  }

  async function randomize() {
    if (!selectedMap || players.length === 0) return
    const result = await Client.randomizeDraftApiDraftRandomizePost({
      draftRequest: {
        mapName: mapApiName(selectedMap),
        players: players.map((p) => ({ name: p.name, team: p.team })),
      },
    })
    setAssignments(result.assignments)
    setRandomizedAt(new Date(result.randomizedAt).toLocaleTimeString())
  }

  const positionLimit = mapData ? mapData.playerStarts.length : 0
  const canAddPlayer = mapData !== null && players.length < positionLimit
  const namesUnique =
    new Set(players.map((p) => p.name)).size === players.length
  const validPlayerNames = new Set<string>(Object.values(PlayerEnum))
  const allNamesValid =
    players.length >= 2 && players.every((p) => validPlayerNames.has(p.name))

  const team1Set = new Set(
    players.filter((p) => p.team === 1).map((p) => p.name),
  )
  const allBalancePlayers = [
    ...players.filter((p) => p.team === 1).map((p) => p.name),
    ...players.filter((p) => p.team === 2).map((p) => p.name),
  ]
  const matchedEntry = teamRating
    ? Object.entries(teamRating).find(([key]) => {
        const keySet = new Set(key.split(","))
        return (
          keySet.size === team1Set.size &&
          [...keySet].every((n) => team1Set.has(n))
        )
      })
    : null
  const matchedScore = matchedEntry
    ? (1.0 - Math.abs(matchedEntry[1] - 0.5) * 2.0) * 100
    : null

  return (
    <Box sx={{ maxWidth: 900, mx: "auto" }}>
      <Typography variant="h5" gutterBottom>
        Map Draft
      </Typography>

      <Autocomplete
        options={MAPLIST}
        getOptionLabel={(f) => mapDisplayName(f)}
        value={selectedMap}
        onChange={(_e, val) => {
          setSelectedMap(val)
        }}
        renderInput={(params) => (
          <TextField {...params} label="Select Map" size="small" />
        )}
        sx={{ mb: 2, maxWidth: 400 }}
      />

      {selectedMap && (
        <Box sx={{ mb: 2 }}>
          <Map mapname={mapDisplayName(selectedMap)} />
        </Box>
      )}

      <Paper sx={{ p: 2, mb: 2 }}>
        <Box sx={{ display: "flex", alignItems: "center", mb: 1, gap: 1 }}>
          <Typography variant="subtitle1" sx={{ flexGrow: 1 }}>
            Players
          </Typography>
          <Button
            variant="outlined"
            size="small"
            startIcon={<PersonAddIcon />}
            disabled={!canAddPlayer}
            onClick={addPlayer}
          >
            Add Player
          </Button>
        </Box>
        {!mapData && (
          <Typography variant="body2" color="text.secondary">
            Select a map to add players.
          </Typography>
        )}
        {players.map((p) => (
          <Box
            key={p.id}
            sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}
          >
            <Autocomplete
              freeSolo
              options={Object.values(PlayerEnum)}
              value={p.name}
              onInputChange={(_e, val) => updatePlayerName(p.id, val)}
              renderInput={(params) => (
                <TextField {...params} size="small" label="Name" />
              )}
              sx={{ width: 200 }}
            />
            <ToggleButtonGroup
              size="small"
              exclusive
              value={p.team}
              onChange={(_e, val) => {
                if (val !== null) updatePlayerTeam(p.id, val as 1 | 2 | 3 | 4)
              }}
            >
              {([1, 2, 3, 4] as const).map((t) => (
                <ToggleButton
                  key={t}
                  value={t}
                  sx={{
                    "&.Mui-selected": {
                      bgcolor: TEAM_COLORS[t],
                      color: "white",
                      "&:hover": { bgcolor: TEAM_COLORS[t] },
                    },
                  }}
                >
                  {t}
                </ToggleButton>
              ))}
            </ToggleButtonGroup>
            <IconButton size="small" onClick={() => removePlayer(p.id)}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        ))}
      </Paper>

      <Stack direction="row" spacing={1} sx={{ mb: 2 }}>
        <Button
          variant="contained"
          startIcon={<CasinoIcon />}
          disabled={players.length === 0 || !mapData || !namesUnique}
          onClick={randomize}
        >
          Randomize
        </Button>
        <Tooltip
          title={
            !allNamesValid
              ? "All players must be selected from the known players list"
              : ""
          }
        >
          <span>
            <Button
              variant="outlined"
              startIcon={<BalanceIcon />}
              disabled={!allNamesValid}
              onClick={checkBalance}
            >
              Check Balance
            </Button>
          </span>
        </Tooltip>
        <Tooltip
          title={
            !allNamesValid
              ? "All players must be selected from the known players list"
              : !teamRating
                ? "Run Check Balance first"
                : ""
          }
        >
          <span>
            <Button
              variant="outlined"
              startIcon={<BalanceIcon />}
              disabled={!teamRating}
              onClick={applyMostBalanced}
            >
              Auto Balance
            </Button>
          </span>
        </Tooltip>
      </Stack>

      {balanceLoading && <LinearProgress sx={{ mb: 1 }} />}
      {matchedEntry && matchedScore !== null && (
        <ScoreBar
          team={matchedEntry[0]}
          score={matchedScore}
          selectedPlayers={allBalancePlayers}
        />
      )}

      {assignments.length > 0 && (
        <>
          {randomizedAt && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ mb: 1, display: "block" }}
            >
              Randomized at {randomizedAt}
            </Typography>
          )}
          <Table size="small">
            <TableHead>
              <TableRow>
                <TableCell>Player</TableCell>
                <TableCell>Team</TableCell>
                <TableCell>General</TableCell>
                <TableCell>Position</TableCell>
              </TableRow>
            </TableHead>
            <TableBody>
              {assignments.map((a) => (
                <TableRow key={a.playerName}>
                  <TableCell>{a.playerName}</TableCell>
                  <TableCell>
                    <Box
                      sx={{
                        display: "inline-block",
                        px: 1,
                        py: 0.25,
                        borderRadius: 1,
                        bgcolor: TEAM_COLORS[a.team as 1 | 2 | 3 | 4],
                        color: "white",
                        fontSize: 12,
                        fontWeight: "bold",
                      }}
                    >
                      Team {a.team}
                    </Box>
                  </TableCell>
                  <TableCell>
                    <DisplayGeneral general={a.general} />
                  </TableCell>
                  <TableCell>#{a.positionNumber}</TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </>
      )}
    </Box>
  )
}
