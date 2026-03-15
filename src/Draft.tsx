import Autocomplete from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import IconButton from "@mui/material/IconButton"
import Paper from "@mui/material/Paper"
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
import type { DraftAssignment, MapDataPayload, MapsByPlayerCount } from "./api"
import Chip from "@mui/material/Chip"
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

let nextId = 1

export default function DisplayDraft() {
  const [mapsByCount, setMapsByCount] = React.useState<MapsByPlayerCount[]>([])
  const [selectedPlayerCount, setSelectedPlayerCount] = React.useState<
    number | null
  >(null)
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
    Client.getMapsByPlayerCountApiMapsByPlayerCountGet().then(setMapsByCount, () => {})
  }, [])

  React.useEffect(() => {
    setMapData(null)
    setPlayers([])
    setAssignments([])
    setRandomizedAt(null)
    if (!selectedMap) return
    const apiName = mapDisplayName(selectedMap)
    Client.getMapDataApiMapDataMapNameGet({ mapName: apiName }).then(
      (data) => {
        setMapData(data)
        const count = data.playerStarts.length
        const enumNames = Object.values(PlayerEnum)
        setPlayers(
          Array.from({ length: count }, (_, i) => ({
            id: nextId++,
            name: enumNames[i] ?? `Player ${i + 1}`,
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

  function clearDraft() {
    setAssignments([])
    setRandomizedAt(null)
  }

  function removePlayer(id: number) {
    setPlayers((prev) => prev.filter((p) => p.id !== id))
    clearDraft()
  }

  function updatePlayerName(id: number, name: string) {
    setPlayers((prev) => prev.map((p) => (p.id === id ? { ...p, name } : p)))
  }

  function updatePlayerTeam(id: number, team: 1 | 2 | 3 | 4) {
    setPlayers((prev) => prev.map((p) => (p.id === id ? { ...p, team } : p)))
    clearDraft()
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
        mapName: mapDisplayName(selectedMap),
        players: players.map((p) => ({ name: p.name, team: p.team })),
      },
    })
    setAssignments(result.assignments)
    setRandomizedAt(new Date(result.randomizedAt).toLocaleTimeString())
  }

  const knownMaps = React.useMemo(() => {
    if (!selectedPlayerCount) return null
    return new Set(
      mapsByCount.find((g) => g.playerCount === selectedPlayerCount)?.maps ??
        [],
    )
  }, [mapsByCount, selectedPlayerCount])

  const filteredMapList = knownMaps
    ? MAPLIST.filter((f) => knownMaps.has(mapDisplayName(f)))
    : MAPLIST

  const assignmentByName = React.useMemo(
    () => Object.fromEntries(assignments.map((a) => [a.playerName, a])),
    [assignments],
  )

  const positionToPlayer = React.useMemo(
    () =>
      Object.fromEntries(
        assignments.map((a) => [a.positionNumber, a.playerName]),
      ),
    [assignments],
  )

  const positionLimit = mapData ? mapData.playerStarts.length : 0
  const canAddPlayer = mapData !== null && players.length < positionLimit
  const namesUnique =
    new Set(players.map((p) => p.name)).size === players.length
  const validPlayerNames = new Set<string>(Object.values(PlayerEnum))
  const allNamesValid =
    players.length >= 2 && players.every((p) => validPlayerNames.has(p.name))

  const teamCounts = players.reduce<Record<number, number>>((acc, p) => {
    acc[p.team] = (acc[p.team] ?? 0) + 1
    return acc
  }, {})
  const teamSizes = Object.values(teamCounts)
  const teamsBalanced =
    teamSizes.length >= 2 && teamSizes.every((n) => n === teamSizes[0])

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

      {mapsByCount.length > 0 && (
        <Box sx={{ mb: 1 }}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={selectedPlayerCount}
            onChange={(_e, val) => {
              setSelectedPlayerCount(val)
              setSelectedMap(null)
            }}
          >
            {mapsByCount.map(({ playerCount }) => (
              <ToggleButton key={playerCount} value={playerCount}>
                {playerCount}p
              </ToggleButton>
            ))}
          </ToggleButtonGroup>
        </Box>
      )}

      <Autocomplete
        options={filteredMapList}
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
        <Box sx={{ mb: 2, maxWidth: 600 }}>
          <Map
            mapname={mapDisplayName(selectedMap)}
            playerPositions={positionToPlayer}
          />
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
            {assignmentByName[p.name] && (
              <>
                <DisplayGeneral general={assignmentByName[p.name].general} />
                <Chip
                  label={`#${assignmentByName[p.name].positionNumber}`}
                  size="small"
                  variant="outlined"
                />
              </>
            )}
            <IconButton size="small" onClick={() => removePlayer(p.id)}>
              <CloseIcon fontSize="small" />
            </IconButton>
          </Box>
        ))}
      </Paper>

      <Stack direction="row" spacing={1} sx={{ mb: 2 }} alignItems="center">
        <Button
          variant="contained"
          startIcon={<CasinoIcon />}
          disabled={
            players.length === 0 || !mapData || !namesUnique || !teamsBalanced
          }
          onClick={randomize}
        >
          Randomize
        </Button>
        {randomizedAt && (
          <Typography variant="caption" color="text.secondary">
            Locked at {randomizedAt}
          </Typography>
        )}
        <Tooltip
          title={
            !teamsBalanced
              ? "Teams must have equal numbers of players"
              : !allNamesValid
                ? "All players must be selected from the known players list"
                : ""
          }
        >
          <span>
            <Button
              variant="outlined"
              startIcon={<BalanceIcon />}
              disabled={!allNamesValid || !teamsBalanced}
              onClick={checkBalance}
            >
              Check Balance
            </Button>
          </span>
        </Tooltip>
        <Tooltip
          title={
            !teamsBalanced
              ? "Teams must have equal numbers of players"
              : !allNamesValid
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
              disabled={!teamRating || !teamsBalanced}
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
    </Box>
  )
}
