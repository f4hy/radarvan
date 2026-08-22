import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew"
import ArrowForwardIosIcon from "@mui/icons-material/ArrowForwardIos"
import AutoAwesomeIcon from "@mui/icons-material/AutoAwesome"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Box from "@mui/material/Box"
import Chip from "@mui/material/Chip"
import Divider from "@mui/material/Divider"
import IconButton from "@mui/material/IconButton"
import MenuItem from "@mui/material/MenuItem"
import Paper from "@mui/material/Paper"
import Select from "@mui/material/Select"
import Stack from "@mui/material/Stack"
import Table from "@mui/material/Table"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableContainer from "@mui/material/TableContainer"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import Typography from "@mui/material/Typography"
import { alpha, useTheme } from "@mui/material/styles"
import * as React from "react"
import { GameNightHighlight, GameNightRecap, MatchInfo } from "./api"
import { renderAiText } from "./aiText"
import { Client, GameNightClient } from "./Client"
import Loading from "./Loading"
import MatchNarrative from "./MatchNarrative"
import PlayerChip from "./PlayerChip"
import { BRAND_COLOR, LOSS_COLOR, WIN_COLOR } from "./theme"
import { useErrorSnackbar } from "./useErrorSnackbar"

// Emoji per highlight kind. `kind` is a stable backend slug; an unrecognised
// one still renders (with the fallback), so adding a highlight server-side
// never needs a matching frontend change to be safe.
const HIGHLIGHT_ICONS: { [key: string]: string } = {
  best_record: "🔥",
  worst_record: "❄️",
  upset: "🐍",
  longest_game: "⏳",
  shortest_game: "⚡",
  first_blood: "🩸",
  apm: "🚀",
  superweapon: "☢️",
  hunted: "🚜",
}

// The backend's game-night date key is "YYYY-MM-DD" (US Eastern, 5am
// rollover). Build the Date in local time so it renders as that exact calendar
// day everywhere — new Date("YYYY-MM-DD") parses as UTC midnight, which shows
// as the previous evening anywhere west of UTC. Same reasoning as
// Matches.tsx:MatchDateSummary.
function localDate(key: string): Date {
  const [year, month, day] = key.split("-").map(Number)
  return new Date(year, month - 1, day)
}

function longDate(key: string): string {
  return localDate(key).toLocaleDateString("en-US", {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
  })
}

function clockSpan(recap: GameNightRecap): string | null {
  if (!recap.startedAt || !recap.endedAt) return null
  const start = new Date(recap.startedAt)
  const end = new Date(recap.endedAt)
  const hours = (end.getTime() - start.getTime()) / 3_600_000
  const time = (d: Date) =>
    d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" })
  return `${time(start)} – ${time(end)} (${hours.toFixed(1)}h)`
}

function HighlightCard(props: {
  highlight: GameNightHighlight
  onFocusMatch: (matchId: number) => void
}) {
  const { highlight } = props
  const clickable = highlight.matchId != null
  return (
    <Paper
      variant="outlined"
      onClick={
        clickable
          ? () => props.onFocusMatch(highlight.matchId as number)
          : undefined
      }
      title={clickable ? "Show this game below" : undefined}
      sx={{
        p: 1.5,
        flex: "1 1 220px",
        minWidth: 200,
        cursor: clickable ? "pointer" : "default",
        "&:hover": clickable ? { borderColor: BRAND_COLOR } : {},
      }}
    >
      <Stack direction="row" spacing={1} sx={{ alignItems: "flex-start" }}>
        <Typography sx={{ fontSize: 20, lineHeight: 1.2 }}>
          {HIGHLIGHT_ICONS[highlight.kind] ?? "•"}
        </Typography>
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="caption" color="text.secondary">
            {highlight.title}
          </Typography>
          <Typography variant="body2" sx={{ fontWeight: 500 }}>
            {highlight.detail}
          </Typography>
        </Box>
      </Stack>
    </Paper>
  )
}

function Standings(props: { recap: GameNightRecap }) {
  const theme = useTheme()
  const players = props.recap.players ?? []
  if (players.length === 0) return null
  return (
    <TableContainer component={Paper} variant="outlined">
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Player</TableCell>
            <TableCell align="right">W</TableCell>
            <TableCell align="right">L</TableCell>
            <TableCell align="right">Win %</TableCell>
            <TableCell align="right">Streak</TableCell>
            <TableCell sx={{ display: { xs: "none", md: "table-cell" } }}>
              Generals dealt
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {players.map((line) => {
            const rate = line.games > 0 ? line.wins / line.games : 0
            return (
              <TableRow key={line.player} hover>
                <TableCell>
                  <PlayerChip name={line.player} size="small" />
                </TableCell>
                <TableCell align="right" sx={{ color: WIN_COLOR }}>
                  {line.wins}
                </TableCell>
                <TableCell align="right" sx={{ color: LOSS_COLOR }}>
                  {line.losses}
                </TableCell>
                <TableCell
                  align="right"
                  sx={{
                    bgcolor: alpha(
                      rate >= 0.5 ? WIN_COLOR : LOSS_COLOR,
                      // Tint strength tracks how far from even the record is,
                      // so a 5-2 night reads louder than a 4-3 one.
                      Math.min(0.35, Math.abs(rate - 0.5) * 0.7),
                    ),
                    fontWeight: 500,
                  }}
                >
                  {(rate * 100).toFixed(0)}%
                </TableCell>
                <TableCell align="right">
                  {(line.bestStreak ?? 0) > 1 ? `${line.bestStreak}W` : "—"}
                </TableCell>
                <TableCell
                  sx={{
                    display: { xs: "none", md: "table-cell" },
                    color: theme.palette.text.secondary,
                    fontSize: 12,
                  }}
                >
                  {(line.generals ?? []).join(", ")}
                </TableCell>
              </TableRow>
            )
          })}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function AiSummary(props: { recap: GameNightRecap }) {
  // Deliberately absent rather than empty for most nights: the recap is written
  // once by the nightly job and never backfilled, so every night before the
  // feature shipped simply has none. Render nothing at all in that case — an
  // empty "AI recap" box on every archived night would read as broken.
  if (!props.recap.aiSummary) return null
  return (
    <Paper
      variant="outlined"
      // App.css centers page text; prose paragraphs have to opt back out or
      // the recap reads as a poem.
      sx={{
        p: 2,
        borderColor: BRAND_COLOR,
        borderLeftWidth: 4,
        textAlign: "left",
      }}
    >
      <Stack direction="row" spacing={1} sx={{ alignItems: "center", mb: 1 }}>
        <AutoAwesomeIcon fontSize="small" sx={{ color: BRAND_COLOR }} />
        <Typography variant="subtitle2">The night, written up</Typography>
      </Stack>
      {renderAiText(props.recap.aiSummary)}
    </Paper>
  )
}

function GameByGame(props: {
  date: string
  // Set when a highlight card is clicked: opens this section and scrolls the
  // named game into view, so a card like "Longest game" leads somewhere.
  focusedMatchId: number | null
}) {
  const [matches, setMatches] = React.useState<MatchInfo[] | null>(null)
  const [expanded, setExpanded] = React.useState(false)
  const rowRefs = React.useRef<{ [key: number]: HTMLDivElement | null }>({})
  const { showError, errorSnackbar } = useErrorSnackbar()
  const load = React.useCallback(() => {
    if (matches !== null) return
    Client.getMatchesByDateApiMatchesByDateDateGet({
      // The generated client serializes Date params via toISOString() (UTC), so
      // the param must be UTC midnight of the backend's date key — which is
      // what new Date("YYYY-MM-DD") produces.
      date: new Date(props.date),
      excludeDev: true,
    })
      .then((result) => setMatches(result.matches))
      .catch(showError)
  }, [matches, props.date, showError])

  React.useEffect(() => {
    if (props.focusedMatchId === null) return
    setExpanded(true)
    load()
  }, [props.focusedMatchId, load])

  // Separate from the effect above: the row only exists once the fetch has
  // resolved and the accordion has rendered its children.
  React.useEffect(() => {
    if (props.focusedMatchId === null || matches === null) return
    rowRefs.current[props.focusedMatchId]?.scrollIntoView({
      behavior: "smooth",
      block: "center",
    })
  }, [props.focusedMatchId, matches])

  return (
    <Accordion
      expanded={expanded}
      slotProps={{ transition: { unmountOnExit: true } }}
      onChange={(_e, isExpanded) => {
        setExpanded(isExpanded)
        if (isExpanded) load()
      }}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography sx={{ fontWeight: 600 }}>Game by game</Typography>
      </AccordionSummary>
      <AccordionDetails>
        {errorSnackbar}
        {matches === null ? (
          <Loading />
        ) : (
          <Stack spacing={1.5}>
            {matches.map((match) => (
              <Box
                key={match.id}
                ref={(el: HTMLDivElement | null) => {
                  rowRefs.current[match.id] = el
                }}
                sx={
                  match.id === props.focusedMatchId
                    ? { outline: `2px solid ${BRAND_COLOR}`, borderRadius: 1 }
                    : {}
                }
              >
                <MatchNarrative matchId={match.id} />
              </Box>
            ))}
          </Stack>
        )}
      </AccordionDetails>
    </Accordion>
  )
}

export default function GameNight() {
  const [nights, setNights] = React.useState<string[]>([])
  const [focusedMatchId, setFocusedMatchId] = React.useState<number | null>(
    null,
  )
  const [selected, setSelected] = React.useState<string | null>(() =>
    new URLSearchParams(window.location.search).get("date"),
  )
  const [recap, setRecap] = React.useState<GameNightRecap | null>(null)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    Client.getDatesApiDatesGet()
      .then((dates) => {
        // Already newest-first from the API.
        const keys = Object.keys(dates)
        setNights(keys)
        setSelected((current) => current ?? keys[0] ?? null)
      })
      .catch(showError)
  }, [showError])

  React.useEffect(() => {
    if (selected === null) return
    setRecap(null)
    setFocusedMatchId(null)
    // Keep the URL shareable — this page's whole point is dropping a link to
    // one night in chat.
    const params = new URLSearchParams(window.location.search)
    params.set("date", selected)
    window.history.replaceState(null, "", `?${params.toString()}`)
    GameNightClient.getGameNightRecapApiGameNightNightGet({
      night: new Date(selected),
    })
      .then(setRecap)
      .catch(showError)
  }, [selected, showError])

  const index = selected ? nights.indexOf(selected) : -1
  // nights is newest-first, so the *later* night is at a lower index.
  const goNewer = index > 0 ? () => setSelected(nights[index - 1]) : undefined
  const goOlder =
    index >= 0 && index < nights.length - 1
      ? () => setSelected(nights[index + 1])
      : undefined

  const picker = (
    <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
      <IconButton size="small" disabled={!goOlder} onClick={goOlder}>
        <ArrowBackIosNewIcon fontSize="inherit" />
      </IconButton>
      <Select
        size="small"
        value={selected ?? ""}
        onChange={(e) => setSelected(e.target.value)}
        sx={{ minWidth: 220 }}
      >
        {nights.map((night) => (
          <MenuItem key={night} value={night}>
            {longDate(night)}
          </MenuItem>
        ))}
      </Select>
      <IconButton size="small" disabled={!goNewer} onClick={goNewer}>
        <ArrowForwardIosIcon fontSize="inherit" />
      </IconButton>
    </Stack>
  )

  if (recap === null) {
    return (
      <Stack spacing={2}>
        {errorSnackbar}
        {picker}
        <Loading />
      </Stack>
    )
  }

  const span = clockSpan(recap)
  return (
    <Stack spacing={2}>
      {errorSnackbar}
      <Typography variant="h5">Game Night</Typography>
      {picker}

      {recap.matchCount === 0 ? (
        <Typography color="text.secondary">
          Nothing was played that night.
        </Typography>
      ) : (
        <>
          <Stack
            direction="row"
            spacing={1}
            useFlexGap
            sx={{ flexWrap: "wrap", alignItems: "center" }}
          >
            <Chip
              label={`${recap.matchCount} ${
                recap.matchCount === 1 ? "game" : "games"
              }`}
              color="primary"
              size="small"
            />
            {Object.entries(recap.formats ?? {}).map(([format, count]) => (
              <Chip
                key={format}
                label={`${count}× ${format}`}
                size="small"
                variant="outlined"
              />
            ))}
            {span && (
              <Typography variant="body2" color="text.secondary">
                {span}
              </Typography>
            )}
            {recap.medianMinutes != null && (
              <Typography variant="body2" color="text.secondary">
                median {recap.medianMinutes.toFixed(1)} min
              </Typography>
            )}
          </Stack>

          <AiSummary recap={recap} />

          {(recap.highlights ?? []).length > 0 && (
            <Stack
              direction="row"
              spacing={1.5}
              useFlexGap
              sx={{ flexWrap: "wrap" }}
            >
              {(recap.highlights ?? []).map((highlight) => (
                <HighlightCard
                  key={`${highlight.kind}-${highlight.title}`}
                  highlight={highlight}
                  onFocusMatch={setFocusedMatchId}
                />
              ))}
            </Stack>
          )}

          <Divider />
          <Typography variant="h6">Standings</Typography>
          {recap.countedMatches < recap.matchCount && (
            <Typography variant="caption" color="text.secondary">
              Records cover the {recap.countedMatches} decided competitive{" "}
              {recap.countedMatches === 1 ? "game" : "games"}; the other{" "}
              {recap.matchCount - recap.countedMatches}{" "}
              {recap.matchCount - recap.countedMatches === 1 ? "was" : "were"}{" "}
              unfinished, a comp-stomp, or a free-for-all.
            </Typography>
          )}
          <Standings recap={recap} />

          <Stack
            direction="row"
            spacing={1}
            useFlexGap
            sx={{ flexWrap: "wrap" }}
          >
            {Object.entries(recap.maps ?? {}).map(([name, count]) => (
              <Chip
                key={name}
                label={count > 1 ? `${name} ×${count}` : name}
                size="small"
                variant="outlined"
              />
            ))}
          </Stack>

          <GameByGame
            date={recap.date.toISOString().slice(0, 10)}
            focusedMatchId={focusedMatchId}
          />
        </>
      )}
    </Stack>
  )
}
