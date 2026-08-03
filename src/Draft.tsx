import Autocomplete from "@mui/material/Autocomplete"
import { toGeneralName } from "./general_utils"
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
import LinearProgress from "@mui/material/LinearProgress"
import Stack from "@mui/material/Stack"
import * as React from "react"
import type {
  DraftAssignment,
  MapDataPayload,
  MapsByPlayerCount,
  PlayerGameCount,
} from "./api"
import Chip from "@mui/material/Chip"
import { PlayerEnum } from "./api"
import { Client, MapClient } from "./Client"
import { ScoreBar } from "./BalanceTeams"
import DisplayGeneral from "./Generals"
import GameMap from "./Map"

const VALID_PLAYER_NAMES = new Set<string>(Object.values(PlayerEnum))

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

let nextId = 1

export default function DisplayDraft() {
  const [mapsByCount, setMapsByCount] = React.useState<MapsByPlayerCount[]>([])
  const [topPlayers, setTopPlayers] = React.useState<string[]>([])
  const [selectedPlayerCount, setSelectedPlayerCount] = React.useState<
    number | null
  >(6)
  const [selectedMap, setSelectedMap] = React.useState<string | null>(null)
  const [players, setPlayers] = React.useState<DraftPlayer[]>([])
  const [_mapData, setMapData] = React.useState<MapDataPayload | null>(null)
  const [assignments, setAssignments] = React.useState<DraftAssignment[]>([])
  const [randomizedAt, setRandomizedAt] = React.useState<string | null>(null)
  const [teamRating, setTeamRating] = React.useState<Record<
    string,
    number
  > | null>(null)
  const [balanceLoading, setBalanceLoading] = React.useState(false)

  React.useEffect(() => {
    MapClient.getMapsByPlayerCountApiMapsByPlayerCountGet().then(
      setMapsByCount,
      () => {},
    )
    Client.getPlayerTeamGameCountsApiPlayerGameCountsTeamGet().then(
      (data: PlayerGameCount[]) => setTopPlayers(data.map((p) => p.name)),
      () => {},
    )
  }, [])

  React.useEffect(() => {
    setAssignments([])
    setRandomizedAt(null)
    setSelectedMap(null)
    if (!selectedPlayerCount) {
      setPlayers([])
      return
    }
    setPlayers(
      Array.from({ length: selectedPlayerCount }, (_, i) => ({
        id: nextId++,
        name: topPlayers[i] ?? `Player ${i + 1}`,
        team: (i % 2 === 0 ? 1 : 2) as 1 | 2,
      })),
    )
  }, [selectedPlayerCount, topPlayers])

  React.useEffect(() => {
    setMapData(null)
    setAssignments([])
    setRandomizedAt(null)
    if (!selectedMap) return
    MapClient.getMapDataApiMapDataMapNameGet({ mapName: selectedMap }).then(
      (data) => setMapData(data),
      () => setMapData(null),
    )
  }, [selectedMap])

  React.useEffect(() => {
    setTeamRating(null)
    if (!allNamesValid || !teamsBalanced) return
    const team1 = players
      .filter((p) => p.team === 1)
      .map((p) => p.name as PlayerEnum)
    const team2 = players
      .filter((p) => p.team === 2)
      .map((p) => p.name as PlayerEnum)
    setBalanceLoading(true)
    Client.balanceTeamsApiBalanceTeamsGet({
      players: [...team1, ...team2],
    }).then(
      (data) => {
        setTeamRating(data)
        setBalanceLoading(false)
      },
      () => setBalanceLoading(false),
    )
  }, [players])

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
    const team1Names = new Set(best[0].split(","))
    setPlayers((prev) =>
      prev.map((p) => ({
        ...p,
        team: (team1Names.has(p.name) ? 1 : 2) as 1 | 2,
      })),
    )
  }

  async function randomize() {
    if (!selectedMap || players.length === 0) return
    const result = await Client.randomizeDraftApiDraftRandomizePost({
      draftRequest: {
        mapName: selectedMap,
        players: players.map((p) => ({ name: p.name, team: p.team })),
      },
    })
    setAssignments(result.assignments)
    setRandomizedAt(new Date(result.randomizedAt).toLocaleTimeString())
  }

  const knownMaps = React.useMemo(() => {
    if (!selectedPlayerCount) return null
    return new Set(
      mapsByCount
        .find((g) => g.playerCount === selectedPlayerCount)
        ?.maps.map((x) => x.toLowerCase()) ?? [],
    )
  }, [mapsByCount, selectedPlayerCount])

  const filteredMapList = Array.from(knownMaps ?? []).sort()

  const assignmentByName = React.useMemo(
    () => Object.fromEntries(assignments.map((a) => [a.playerName, a])),
    [assignments],
  )

  const positionToPlayer = React.useMemo(
    () =>
      Object.fromEntries(
        assignments.map((a) => [
          a.positionNumber,
          {
            name: `${a.playerName}[${a.team}]`,
            general: toGeneralName(a.general),
          },
        ]),
      ),
    [assignments],
  )

  const allNamesValid =
    players.length >= 2 && players.every((p) => VALID_PLAYER_NAMES.has(p.name))

  const teamCounts = players.reduce<Record<number, number>>((acc, p) => {
    acc[p.team] = (acc[p.team] ?? 0) + 1
    return acc
  }, {})
  const teamSizes = Object.values(teamCounts)
  const teamsBalanced =
    teamSizes.length >= 2 && teamSizes.every((n) => n === teamSizes[0])

  const { team1Set, team2Set, allBalancePlayers } = React.useMemo(() => {
    const t1 = new Set(players.filter((p) => p.team === 1).map((p) => p.name))
    const t2 = new Set(players.filter((p) => p.team === 2).map((p) => p.name))
    const all = [...t1, ...t2]
    return { team1Set: t1, team2Set: t2, allBalancePlayers: all }
  }, [players])

  const matchedEntry = React.useMemo(() => {
    if (!teamRating) return null
    return (
      Object.entries(teamRating).find(([key]) => {
        const keySet = new Set(key.split(","))
        return (
          (keySet.size === team1Set.size &&
            [...keySet].every((n) => team1Set.has(n))) ||
          (keySet.size === team2Set.size &&
            [...keySet].every((n) => team2Set.has(n)))
        )
      }) ?? null
    )
  }, [teamRating, team1Set, team2Set])

  const matchedScore = React.useMemo(
    () =>
      matchedEntry ? (1.0 - Math.abs(matchedEntry[1] - 0.5) * 2.0) * 100 : null,
    [matchedEntry],
  )

  const availablePlayersBySlot = React.useMemo(
    () =>
      players.map((p) =>
        Object.values(PlayerEnum).filter(
          (name) =>
            !players.some((other) => other.id !== p.id && other.name === name),
        ),
      ),
    [players],
  )

  return (
    <Box sx={{ maxWidth: 900, mx: "auto" }}>
      <Typography variant="h5" gutterBottom>
        Map Draft
      </Typography>
      {mapsByCount.length > 0 && (
        <Box sx={{ mb: 2 }}>
          <ToggleButtonGroup
            size="small"
            exclusive
            value={selectedPlayerCount}
            onChange={(_e, val) => {
              if (val !== null) setSelectedPlayerCount(val)
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
      {selectedPlayerCount && (
        <>
          <Paper sx={{ p: 2, mb: 2 }}>
            <Typography variant="subtitle1" sx={{ mb: 1 }}>
              Players
            </Typography>
            {players.map((p, idx) => (
              <Box
                key={p.id}
                sx={{ display: "flex", alignItems: "center", gap: 1, mb: 1 }}
              >
                <Autocomplete
                  options={availablePlayersBySlot[idx]}
                  value={VALID_PLAYER_NAMES.has(p.name) ? p.name : null}
                  onChange={(_e, val) => {
                    if (val !== null) updatePlayerName(p.id, val)
                  }}
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
                    if (val !== null)
                      updatePlayerTeam(p.id, val as 1 | 2 | 3 | 4)
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
                    <DisplayGeneral
                      general={assignmentByName[p.name].general}
                    />
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

          <Autocomplete
            options={filteredMapList}
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
              <GameMap
                mapname={selectedMap}
                playerPositions={positionToPlayer}
                showDownload
              />
            </Box>
          )}

          <Stack
            direction="row"
            spacing={1}
            sx={{
              alignItems: "center",
              mb: 2,
            }}
          >
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
                  disabled={!teamRating || !teamsBalanced}
                  onClick={applyMostBalanced}
                >
                  Auto Balance
                </Button>
              </span>
            </Tooltip>
            <Button
              variant="contained"
              startIcon={<CasinoIcon />}
              disabled={false}
              onClick={randomize}
            >
              Randomize
            </Button>
            {randomizedAt && (
              <Typography
                variant="caption"
                sx={{
                  color: "text.secondary",
                }}
              >
                Locked at {randomizedAt}
              </Typography>
            )}
          </Stack>

          {balanceLoading && <LinearProgress sx={{ mb: 1 }} />}
          {matchedEntry && matchedScore !== null && (
            <ScoreBar
              team={matchedEntry[0]}
              score={matchedScore}
              selectedPlayers={allBalancePlayers}
            />
          )}
        </>
      )}
    </Box>
  )
}
