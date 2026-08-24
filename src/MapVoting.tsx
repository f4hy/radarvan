import * as React from "react"
import Alert from "@mui/material/Alert"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import Snackbar from "@mui/material/Snackbar"
import InputAdornment from "@mui/material/InputAdornment"
import Stack from "@mui/material/Stack"
import TextField from "@mui/material/TextField"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Typography from "@mui/material/Typography"
import HowToVoteIcon from "@mui/icons-material/HowToVote"
import BlockIcon from "@mui/icons-material/Block"
import ThumbUpIcon from "@mui/icons-material/ThumbUp"
import LoginIcon from "@mui/icons-material/Login"
import ArrowBackIcon from "@mui/icons-material/ArrowBack"
import SearchIcon from "@mui/icons-material/Search"
import GameMap from "./Map"
import Loading from "./Loading"
import Page from "./Page"
import PlayerCountPicker from "./PlayerCountPicker"
import { startDiscordLogin } from "./auth"
import { displayMapName } from "./utils"
import {
  MapVoteChoice,
  MapVoteOption,
  MapVotePage,
  fetchPlayerCounts,
  fetchVotePage,
  setVote,
} from "./voting"

// Cap how many map cards render at once; the rest are behind "Load all".
const MAP_RENDER_CAP = 40

// Case- and whitespace-insensitive key for filtering.
function searchKey(s: string): string {
  return s.toLowerCase().replace(/\s+/g, "")
}

function lastPlayedLabel(days: number | null): string {
  if (days === null) return "never played"
  if (days === 0) return "played today"
  if (days === 1) return "played yesterday"
  return `${days} days ago`
}

function MapCard({
  option,
  disabled,
  onChoose,
}: {
  option: MapVoteOption
  disabled: boolean
  onChoose: (choice: MapVoteChoice | null) => void
}) {
  // Clicking the active choice clears it; otherwise switch to the clicked one.
  const handle = (_: unknown, next: MapVoteChoice | null) => {
    onChoose(next === option.my_choice ? null : next)
  }
  return (
    <Stack spacing={1}>
      <GameMap mapname={option.map_name} deferData />
      <Typography
        variant="subtitle1"
        noWrap
        title={displayMapName(option.map_name)}
      >
        {displayMapName(option.map_name)}
      </Typography>
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          flexWrap: "wrap",
        }}
      >
        <Chip size="small" label={`${option.game_count} games`} />
        <Chip
          size="small"
          variant="outlined"
          label={lastPlayedLabel(option.days_since_last_played)}
        />
      </Stack>
      <ToggleButtonGroup
        exclusive
        size="small"
        value={option.my_choice}
        onChange={handle}
        disabled={disabled}
        fullWidth
      >
        <ToggleButton value="vote" color="success">
          <ThumbUpIcon fontSize="small" sx={{ mr: 0.5 }} /> Vote
        </ToggleButton>
        <ToggleButton value="veto" color="error">
          <BlockIcon fontSize="small" sx={{ mr: 0.5 }} /> Veto
        </ToggleButton>
      </ToggleButtonGroup>
    </Stack>
  )
}

export default function MapVoting() {
  const [counts, setCounts] = React.useState<number[] | null>(null)
  const [selected, setSelected] = React.useState<number | null>(null)
  const [page, setPage] = React.useState<MapVotePage | null>(null)
  const [loading, setLoading] = React.useState(true)
  const [pending, setPending] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)
  const [query, setQuery] = React.useState("")
  const [showAll, setShowAll] = React.useState(false)

  React.useEffect(() => {
    let cancelled = false
    fetchPlayerCounts()
      .then((c) => {
        if (!cancelled) setCounts(c)
      })
      .catch(() => {
        if (!cancelled) setError("Could not load player counts")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [])

  React.useEffect(() => {
    if (selected === null) {
      setPage(null)
      return
    }
    let cancelled = false
    setLoading(true)
    // Fresh count -> start uncapped-search clean.
    setQuery("")
    setShowAll(false)
    fetchVotePage(selected)
      .then((p) => {
        if (!cancelled) setPage(p)
      })
      .catch(() => {
        if (!cancelled) setError("Could not load maps")
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [selected])

  const choose = async (mapName: string, choice: MapVoteChoice | null) => {
    if (selected === null) return
    setPending(true)
    try {
      setPage(await setVote(selected, mapName, choice))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Vote failed")
    } finally {
      setPending(false)
    }
  }

  const errorBar = (
    <Snackbar
      open={error !== null}
      autoHideDuration={5000}
      onClose={() => setError(null)}
      anchorOrigin={{ vertical: "bottom", horizontal: "center" }}
    >
      <Alert severity="error" onClose={() => setError(null)}>
        {error}
      </Alert>
    </Snackbar>
  )

  if (loading) {
    return <Loading />
  }

  if (counts !== null && counts.length === 0) {
    return (
      <Page title="Map Voting" width="narrow">
        <Alert severity="info">No maps available to vote on yet.</Alert>
      </Page>
    )
  }

  if (selected === null || page === null) {
    return (
      <Page
        surface={false}
        title="Map Voting"
        description="Vote for the maps you want in the rotation and veto the ones you don't."
      >
        {counts && (
          <PlayerCountPicker
            title="How many players?"
            subtitle="Pick a player count to see its maps and cast your votes."
            counts={counts}
            onPick={setSelected}
          />
        )}
        {errorBar}
      </Page>
    )
  }

  // Filter over all maps (search reaches everything), then cap how many render.
  const filtered = page.maps.filter((option) =>
    searchKey(displayMapName(option.map_name)).includes(searchKey(query)),
  )
  const visible = showAll ? filtered : filtered.slice(0, MAP_RENDER_CAP)
  const hidden = filtered.length - visible.length

  return (
    <Page
      surface={false}
      title={`Map Voting — ${page.player_count} players`}
      description="Vote for the maps you want in the rotation and veto the ones you don't. A veto takes a map out of the draw entirely."
      actions={
        <>
          <Button
            size="small"
            startIcon={<ArrowBackIcon />}
            onClick={() => setSelected(null)}
          >
            Player count
          </Button>
          <Chip
            icon={<HowToVoteIcon />}
            color="success"
            variant="outlined"
            label={`Votes ${page.votes_used}/${page.vote_limit}`}
          />
          <Chip
            icon={<BlockIcon />}
            color="error"
            variant="outlined"
            label={`Vetoes ${page.vetoes_used}/${page.veto_limit}`}
          />
        </>
      }
    >
      <Stack spacing={2}>
        {!page.logged_in && (
          <Alert
            severity="info"
            action={
              <Button
                color="inherit"
                size="small"
                startIcon={<LoginIcon />}
                onClick={startDiscordLogin}
              >
                Log in
              </Button>
            }
          >
            Log in with Discord to vote for and veto maps.
          </Alert>
        )}
        <TextField
          fullWidth
          size="small"
          placeholder="Search maps…"
          value={query}
          onChange={(e) => {
            setQuery(e.target.value)
            setShowAll(false)
          }}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
        />
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fill, minmax(300px, 1fr))",
            gap: 2,
          }}
        >
          {visible.map((option) => (
            <MapCard
              key={option.map_name}
              option={option}
              disabled={!page.logged_in || pending}
              onChoose={(choice) => choose(option.map_name, choice)}
            />
          ))}
        </Box>
        {hidden > 0 && (
          <Button
            variant="outlined"
            fullWidth
            onClick={() => setShowAll(true)}
            sx={{ mt: 1 }}
          >
            Load all {filtered.length} maps ({hidden} more)
          </Button>
        )}
        {errorBar}
      </Stack>
    </Page>
  )
}
