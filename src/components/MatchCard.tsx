import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward"
import DownloadIcon from "@mui/icons-material/Download"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import ErrorIcon from "@mui/icons-material/Error"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import QuestionMarkIcon from "@mui/icons-material/QuestionMark"
import SmartToyIcon from "@mui/icons-material/SmartToy"
import VisibilityIcon from "@mui/icons-material/Visibility"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Card from "@mui/material/Card"
import Chip from "@mui/material/Chip"
import Collapse from "@mui/material/Collapse"
import Divider from "@mui/material/Divider"
import IconButton from "@mui/material/IconButton"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import { Tooltip } from "@mui/material"
import Typography from "@mui/material/Typography"

import groupBy from "lodash/groupBy"
import * as React from "react"

import { type MatchInfo, type Player, Team } from "../api"
import { FilesClient } from "../clients/files"
import DisplayGeneral from "./Generals"
import GameMap, { type PlayerPosition } from "./Map"
import { MatchRowLoading } from "./Loading"
import { PlayerDot } from "./PlayerChip"
import { useColorMode } from "../lib/ColorModeContext"
import { toGeneralName } from "../lib/general_utils"
import {
  getColorHex,
  isCompetitor,
  isObserver,
  playerPalette,
} from "../lib/utils"

// ShowMatchDetails drags in recharts, and this is the landing page — most
// visits never expand a match, so it is split out and only fetched on demand.
const ShowMatchDetails = React.lazy(
  () => import("../features/games/ShowMatchDetails"),
)

function LazyMatchDetails(props: { id: number }) {
  return (
    <React.Suspense fallback={<MatchRowLoading />}>
      <ShowMatchDetails id={props.id} />
    </React.Suspense>
  )
}

export function normalizePlayerName(name: string): string {
  if (name === "TacticalAI" || name === "Tactical AI") return "T AI"
  const armyMatch = name.match(/^(.+?)\s?Army$/)
  if (armyMatch) return `${armyMatch[1]}A`
  return name
}

function buildPlayerPositions(
  players: Player[],
): Record<number, PlayerPosition> {
  return Object.fromEntries(
    players
      // Observers carry a starting position too, and since these are keyed by
      // it a spectator can otherwise overwrite the real player standing there.
      .filter(
        (p): p is Player & { startingPosition: number } =>
          isCompetitor(p) && p.startingPosition != null,
      )
      .map((p) => [
        p.startingPosition,
        {
          name: normalizePlayerName(p.name),
          color: p.color,
          general: toGeneralName(p.general),
        },
      ]),
  )
}

// Win/loss is carried by a single colored status band at the top of an
// otherwise-neutral card, so names stay readable and the page isn't wall-to-wall
// saturated panels. Solid enough for white band text.
const WON_BAND = "#2f8f57"
const LOST_BAND = "#c2544f"
const NEUTRAL_BAND = "#7a828f"

function StatusBand(props: {
  color: string
  icon: React.ReactNode
  label: string
  center?: boolean
}) {
  return (
    <Box
      sx={{
        bgcolor: props.color,
        color: "common.white",
        px: 1.5,
        py: 0.5,
        display: "flex",
        alignItems: "center",
        justifyContent: props.center ? "center" : "flex-start",
        gap: 0.75,
        "& .MuiSvgIcon-root": { fontSize: "1.1rem" },
      }}
    >
      {props.icon}
      <Typography variant="subtitle2" sx={{ fontWeight: 700 }} noWrap>
        {props.label}
      </Typography>
    </Box>
  )
}

function TeamCard(props: { players: Player[]; won: boolean }) {
  const { mode } = useColorMode()
  const first = props.players[0]
  const team = first?.team
  let label = `${props.won ? "Won" : "Lost"} · Team ${team}`
  let icon = props.won ? <EmojiEventsIcon /> : <ErrorIcon />
  let bandColor = props.won ? WON_BAND : LOST_BAND
  // Observer-ness comes from `role`, not `team` - see utils.isObserver.
  if (first != null && isObserver(first)) {
    label = "Observers"
    icon = <VisibilityIcon />
    bandColor = NEUTRAL_BAND
  } else if (team === Team.NUMBER_0) {
    label = "Unknown Team"
    icon = <QuestionMarkIcon />
    bandColor = NEUTRAL_BAND
  }
  return (
    <Card
      sx={{
        width: { xs: "100%", sm: "50%", md: "auto" },
        flex: { md: 1 },
        minWidth: 0,
        overflow: "hidden",
      }}
    >
      <StatusBand color={bandColor} icon={icon} label={label} />
      <Stack divider={<Divider />}>
        {props.players.map((p) => (
          <Box
            // Color is unique per player in a match; names aren't (twin CPUs).
            key={`${p.name}-${p.color}`}
            sx={{
              display: "flex",
              alignItems: "center",
              gap: 1.5,
              px: 1.5,
              py: 1,
            }}
          >
            <DisplayGeneral general={p.general} />
            <PlayerDot color={getColorHex(p.color)} size={10} />
            <Typography
              variant="h6"
              noWrap
              sx={{
                fontWeight: 700,
                color: playerPalette(getColorHex(p.color), mode).ink,
              }}
            >
              {normalizePlayerName(p.name)}
            </Typography>
          </Box>
        ))}
      </Stack>
    </Card>
  )
}

function FfaPlayerCard(props: { player: Player }) {
  const { mode } = useColorMode()
  const { player } = props
  return (
    <Card sx={{ minWidth: 150, overflow: "hidden" }}>
      <StatusBand
        color={player.won ? WON_BAND : NEUTRAL_BAND}
        icon={player.won ? <EmojiEventsIcon /> : <ErrorIcon />}
        label={player.won ? "Winner" : "Lost"}
        center
      />
      <Stack
        spacing={1}
        sx={{
          alignItems: "center",
          p: 1.5,
        }}
      >
        <DisplayGeneral general={player.general} />
        <Stack direction="row" spacing={0.75} sx={{ alignItems: "center" }}>
          <PlayerDot color={getColorHex(player.color)} size={10} />
          <Typography
            variant="subtitle1"
            noWrap
            sx={{
              fontWeight: 700,
              color: playerPalette(getColorHex(player.color), mode).ink,
            }}
          >
            {normalizePlayerName(player.name)}
          </Typography>
        </Stack>
      </Stack>
    </Card>
  )
}

// Shared frame for one match so consecutive matches in a day read as distinct
// panels: a white surface lifted off the grey page with a hairline border + soft
// shadow, padded so the inner team cards sit inside a clear boundary.
const MATCH_CARD_SX = {
  width: "99%",
  maxWidth: 1600,
  borderRadius: 2,
  bgcolor: "background.paper",
  p: 1.5,
  mb: 2.5,
  boxShadow: 1,
} as const

// Compact, scannable match header shared by the FFA and team cards: the key
// facts (format, map, length) read on one line; date/version/id are demoted to a
// muted caption, with a small secondary action (download) at the top-right. The
// winner is intentionally omitted — each team card carries a "Won/Lost" band.
function MatchHeader(props: {
  match: MatchInfo
  formatLabel: string
  action?: React.ReactNode
}) {
  const { match } = props
  const mapName = match.map.split("/").slice(-1)[0]
  const date = match.timestamp.toLocaleString("en-US", {
    timeZoneName: "short",
  })
  return (
    <Stack
      direction="row"
      spacing={1}
      sx={{
        justifyContent: "space-between",
        alignItems: "flex-start",
        width: "100%",
      }}
    >
      <Stack
        direction="row"
        spacing={1}
        sx={{
          alignItems: "center",
          flexWrap: "wrap",
          minWidth: 0,
        }}
      >
        <Chip label={props.formatLabel} size="small" variant="outlined" />
        <Typography
          variant="body2"
          sx={{
            fontWeight: 600,
          }}
        >
          {mapName}
        </Typography>
        {match.hasAi && (
          <Tooltip title="AI player present — ratings for this game are only minorly impacted">
            <SmartToyIcon fontSize="small" sx={{ color: "text.secondary" }} />
          </Tooltip>
        )}
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
          }}
        >
          {match.durationMinutes.toFixed(1)} min · {date} · v{match.gameVersion}{" "}
          · ID {match.id}
        </Typography>
      </Stack>
      {props.action}
    </Stack>
  )
}

// Small, secondary download action that lives in the header rather than as a
// full-width button below the match.
function DownloadReplayButton(props: { matchId: number }) {
  return (
    <Tooltip title="Download replay">
      <IconButton
        size="small"
        aria-label="Download replay"
        onClick={() => downloadReplay(props.matchId)}
      >
        <DownloadIcon fontSize="small" />
      </IconButton>
    </Tooltip>
  )
}

// An accordion-style expander for the heavy match details: full-width row with a
// rotating chevron. The caller renders the details inside a <Collapse> with
// unmountOnExit so they aren't fetched until the row is first opened.
function DetailsExpander(props: { open: boolean; onToggle: () => void }) {
  return (
    <Button
      fullWidth
      onClick={props.onToggle}
      endIcon={
        <ExpandMoreIcon
          sx={{
            transform: props.open ? "rotate(180deg)" : "none",
            transition: "transform 0.2s",
          }}
        />
      }
      sx={{
        mt: 1,
        py: 0.75,
        justifyContent: "space-between",
        color: "text.secondary",
        borderTop: 1,
        borderColor: "divider",
        borderRadius: 0,
        "&:hover": { bgcolor: "action.hover" },
      }}
    >
      {props.open ? "Hide match details" : "Show match details"}
    </Button>
  )
}

function FfaMatchDisplay(props: { match: MatchInfo }) {
  const { match } = props
  const [details, setDetails] = React.useState<boolean>(false)
  const playerPositions = React.useMemo(
    () => buildPlayerPositions(match.players),
    [match.players],
  )
  return (
    <Paper variant="outlined" sx={MATCH_CARD_SX}>
      <MatchHeader
        match={match}
        formatLabel="FFA"
        action={<DownloadReplayButton matchId={match.id} />}
      />
      <Stack
        direction="row"
        sx={{
          flexWrap: "wrap",
          gap: 1,
          mt: 1,
        }}
      >
        {match.players.map((p) => (
          // Color is unique per player in a match; names aren't (twin CPUs).
          <FfaPlayerCard key={`${p.name}-${p.color}`} player={p} />
        ))}
        <GameMap mapname={match.map} playerPositions={playerPositions} />
      </Stack>
      <DetailsExpander open={details} onToggle={() => setDetails((v) => !v)} />
      <Collapse in={details} unmountOnExit>
        <LazyMatchDetails id={match.id} />
      </Collapse>
    </Paper>
  )
}

function downloadURI(uri: string, name: string) {
  const link = document.createElement("a")
  link.download = name
  link.href = uri
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
}

function downloadReplay(matchId: number) {
  FilesClient.getMatchReplayUrlApiReplayUrlMatchIdGet({ matchId })
    .then((result) => {
      if (!result.url) return
      // The name is also signed into the presigned URL's Content-Disposition -
      // `download` alone is ignored on a cross-origin (S3) href.
      downloadURI(result.url, result.filename)
    })
    .catch(console.error)
}

export const MatchCard = React.memo(function MatchCard(props: {
  match: MatchInfo
  idx: number
}) {
  const [details, setDetails] = React.useState<boolean>(false)
  const playerPositions = React.useMemo(
    () => buildPlayerPositions(props.match.players),
    [props.match.players],
  )

  if (props.match.composition?.isFfa && !props.match.incomplete) {
    return <FfaMatchDisplay match={props.match} />
  }

  const header = (
    <MatchHeader
      match={props.match}
      formatLabel={props.match.composition?.category ?? "?"}
    />
  )

  // Group observers together regardless of the team they happen to carry:
  // historically they sit on team 0 and only re-parsed matches have -1, so
  // grouping on `team` alone splits them across cards (and labels the team-0
  // ones "Unknown Team").
  const teams = groupBy(props.match.players, (p) =>
    isObserver(p) ? "observers" : p.team,
  )

  const paperprops: Record<string, string | number> = { ...MATCH_CARD_SX }
  const incomplete = (props.match.incomplete ?? "").length !== 0
  const matchDisplay = (
    <Paper sx={paperprops} variant="outlined">
      <MatchHeader
        match={props.match}
        formatLabel={props.match.composition?.category ?? "?"}
        action={<DownloadReplayButton matchId={props.match.id} />}
      />
      {props.match?.notes?.length ? (
        <Typography
          sx={{
            color: "warning.main",
            fontWeight: "bold",
            mt: 0.5,
          }}
        >
          {props.match.notes}
        </Typography>
      ) : null}
      {incomplete ? (
        <Typography
          sx={{
            color: "error.main",
            fontWeight: "bold",
            mt: 0.5,
          }}
        >
          {props.match.incomplete}
        </Typography>
      ) : null}
      <Stack
        direction="row"
        sx={{
          justifyContent: "flex-start",
          flexWrap: { xs: "wrap", md: "nowrap" },
          mt: 1,
        }}
      >
        {Object.values(teams).map((team) => (
          <TeamCard
            key={team[0].team}
            players={team}
            won={team[0].team === props.match.winningTeam}
          />
        ))}
        <Box sx={{ flexShrink: 0 }}>
          <GameMap
            mapname={props.match.map}
            playerPositions={playerPositions}
          />
        </Box>
      </Stack>
      <DetailsExpander open={details} onToggle={() => setDetails((v) => !v)} />
      <Collapse in={details} unmountOnExit>
        <LazyMatchDetails id={props.match.id} />
      </Collapse>
    </Paper>
  )

  if (props.match.incomplete) {
    paperprops.bgcolor = "action.disabledBackground"
    paperprops.borderColor = "error.main"
    return (
      <Accordion defaultExpanded={false}>
        <AccordionSummary
          expandIcon={<ArrowDownwardIcon />}
          sx={{ bgcolor: "action.hover" }}
        >
          <Typography
            sx={{
              color: "error.main",
            }}
          >
            Mismatch:{" "}
          </Typography>
          {header}
        </AccordionSummary>
        <AccordionDetails>{matchDisplay}</AccordionDetails>
      </Accordion>
    )
  }
  return matchDisplay
})
