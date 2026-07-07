import * as React from "react"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Alert from "@mui/material/Alert"
import Autocomplete from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Card from "@mui/material/Card"
import CardContent from "@mui/material/CardContent"
import Chip from "@mui/material/Chip"
import Grid from "@mui/material/Grid"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Tab from "@mui/material/Tab"
import Tabs from "@mui/material/Tabs"
import TextField from "@mui/material/TextField"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import { alpha } from "@mui/material/styles"
import ApartmentIcon from "@mui/icons-material/Apartment"
import BlockIcon from "@mui/icons-material/Block"
import BoltIcon from "@mui/icons-material/Bolt"
import DirectionsRunIcon from "@mui/icons-material/DirectionsRun"
import EmojiEventsIcon from "@mui/icons-material/EmojiEvents"
import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import GroupsIcon from "@mui/icons-material/Groups"
import HandshakeIcon from "@mui/icons-material/Handshake"
import InsightsIcon from "@mui/icons-material/Insights"
import MapIcon from "@mui/icons-material/Map"
import MilitaryTechIcon from "@mui/icons-material/MilitaryTech"
import SpeedIcon from "@mui/icons-material/Speed"
import SportsMmaIcon from "@mui/icons-material/SportsMma"
import StarIcon from "@mui/icons-material/Star"
import UpgradeIcon from "@mui/icons-material/Upgrade"
import WorkspacePremiumIcon from "@mui/icons-material/WorkspacePremium"
import {
  Area,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip as ChartTooltip,
  XAxis,
  YAxis,
} from "recharts"
import { Client } from "./Client"
import {
  FavoriteObject,
  GeneralWinRateSeries,
  ObjectUsageStat,
  ObjectUsageStatCategoryEnum,
  PlayerProfile,
  ProfileBadge,
} from "./api"
import DisplayGeneral from "./Generals"
import Loading from "./Loading"
import PlayerChip from "./PlayerChip"
import { usePlayerAccentColor } from "./PlayerColorsContext"
import { LOSS_COLOR, WIN_COLOR } from "./theme"
import WinRateChip from "./WinRateChip"
import WinRateRadar from "./WinRateRadar"
import { toGeneralName } from "./general_utils"
import { displayMapName, formatPercent, wilsonInterval } from "./utils"
import { useErrorSnackbar } from "./useErrorSnackbar"

// A general needs at least this many games in its running series before it's
// worth a tab - a handful of points reads as noise, not a trend.
const MIN_SERIES_GAMES = 5

function playerFromUrl(): string | null {
  return new URLSearchParams(window.location.search).get("player")
}

function setPlayerInUrl(player: string | null): void {
  const params = new URLSearchParams(window.location.search)
  if (player) {
    params.set("player", player)
  } else {
    params.delete("player")
  }
  window.history.replaceState(null, "", `?${params.toString()}`)
}

/** Split a cleaned object name into words: "TankQuadCannon" -> "Tank Quad Cannon". */
function prettyObjectName(name: string): string {
  return name.replace(/([a-z0-9])([A-Z])/g, "$1 $2")
}

// Faction accent colors grounded in the game's own three sides, kept apart
// from the app's win/loss/brand hues so a favorite's origin general reads at
// a glance without borrowing meaning from elsewhere on the page. General IDs
// 0-3 are USA-family (America), 4-7 China-family, 8-11 GLA-family.
const FACTION_COLOR = {
  America: "#3d6fb4",
  China: "#b3542e",
  GLA: "#8a7141",
} as const

function factionColor(general: number): string {
  if (general <= 3) return FACTION_COLOR.America
  if (general <= 7) return FACTION_COLOR.China
  return FACTION_COLOR.GLA
}

/** Icon + label header shared by every section so the page reads as distinct
 * modules while scrolling, instead of one undifferentiated stack. */
function SectionHeader(props: {
  icon: React.ReactNode
  title: string
  subtitle?: React.ReactNode
}) {
  return (
    <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1.5 }}>
      <Box
        sx={{
          display: "flex",
          color: "text.secondary",
          "& svg": { fontSize: 20 },
        }}
      >
        {props.icon}
      </Box>
      <Typography variant="subtitle1">{props.title}</Typography>
      {props.subtitle && (
        <Typography variant="body2" color="text.secondary">
          {props.subtitle}
        </Typography>
      )}
    </Stack>
  )
}

function StatTile(props: {
  label: string
  value: React.ReactNode
  detail?: React.ReactNode
}) {
  return (
    <Card variant="outlined" sx={{ minWidth: 140, flex: 1 }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="overline" color="text.secondary" display="block">
          {props.label}
        </Typography>
        <Typography variant="h6" component="div">
          {props.value}
        </Typography>
        {props.detail && (
          <Typography variant="body2" color="text.secondary">
            {props.detail}
          </Typography>
        )}
      </CardContent>
    </Card>
  )
}

const FAVORITE_ICON: Record<string, React.ElementType> = {
  "Favorite Unit": DirectionsRunIcon,
  "Favorite Building": ApartmentIcon,
  "Favorite Upgrade": UpgradeIcon,
  "Favorite Power": BoltIcon,
}

function FavoriteCard(props: {
  label: string
  favorite: FavoriteObject | null
}) {
  const fav = props.favorite
  const Icon = FAVORITE_ICON[props.label]
  return (
    <Card
      variant="outlined"
      sx={{
        flex: 1,
        minWidth: 200,
        ...(fav && { borderTop: `3px solid ${factionColor(fav.general)}` }),
      }}
    >
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Stack
          direction="row"
          spacing={0.75}
          alignItems="center"
          sx={{ mb: 0.25 }}
        >
          <Icon sx={{ fontSize: 16, color: "text.secondary" }} />
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ lineHeight: 1 }}
          >
            {props.label}
          </Typography>
        </Stack>
        {fav ? (
          <>
            <Typography variant="h6" component="div">
              {prettyObjectName(fav.name)}
            </Typography>
            <Stack
              direction="row"
              spacing={1}
              alignItems="center"
              sx={{ mb: 0.5 }}
            >
              <Chip
                size="small"
                label={toGeneralName(fav.general)}
                sx={{
                  bgcolor: alpha(factionColor(fav.general), 0.14),
                  color: factionColor(fav.general),
                  fontWeight: 600,
                }}
              />
              <Tooltip
                title={
                  fav.peerPerGame === 0
                    ? "No other player of this general builds this at all"
                    : "How many times more than other players of the same general (smoothed)"
                }
              >
                <Chip
                  size="small"
                  color="primary"
                  label={fav.peerPerGame === 0 ? "only one" : `${fav.score}x`}
                />
              </Tooltip>
            </Stack>
            <Typography variant="body2" color="text.secondary">
              {fav.perGame}/game
              {fav.peerPerGame === 0
                ? " — peers never build it"
                : ` vs ${fav.peerPerGame} peer avg`}{" "}
              over {fav.gamesOnGeneral} games
            </Typography>
          </>
        ) : (
          <Typography variant="body2" color="text.secondary">
            Nothing stands out (or not enough games)
          </Typography>
        )}
      </CardContent>
    </Card>
  )
}

function AversionChips(props: { aversions: FavoriteObject[] }) {
  if (props.aversions.length === 0) {
    return null
  }
  return (
    <Box>
      <SectionHeader icon={<BlockIcon />} title="Avoids" />
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
        {props.aversions.map((a) => (
          <Tooltip
            key={`${a.general}-${a.name}`}
            title={`Peers build ${a.peerPerGame}/game on ${toGeneralName(a.general)}; they build ${a.perGame}`}
          >
            <Chip
              icon={<BlockIcon sx={{ fontSize: 16 }} />}
              variant="outlined"
              color="warning"
              label={`${prettyObjectName(a.name)} (${toGeneralName(a.general)})`}
            />
          </Tooltip>
        ))}
      </Stack>
    </Box>
  )
}

const MEDAL_COLOR: Record<string, string> = {
  gold: "#d4af37",
  silver: "#9e9e9e",
  bronze: "#cd7f32",
}

function BadgeGrid(props: { badges: ProfileBadge[] }) {
  if (props.badges.length === 0) {
    return null
  }
  return (
    <Box>
      <SectionHeader icon={<WorkspacePremiumIcon />} title="Badges" />
      <Stack direction="row" spacing={1.5} sx={{ flexWrap: "wrap", gap: 1.5 }}>
        {props.badges.map((b) => (
          <Tooltip
            key={b.key}
            title={
              <>
                <div>{b.description}</div>
                <div>{b.value.toFixed(2)}/game</div>
              </>
            }
          >
            <Box
              sx={{
                width: 104,
                textAlign: "center",
                px: 1,
                py: 1.25,
                borderRadius: 2,
                border: `2px solid ${MEDAL_COLOR[b.tier]}`,
                bgcolor: alpha(MEDAL_COLOR[b.tier], 0.08),
              }}
            >
              <WorkspacePremiumIcon
                sx={{ fontSize: 30, color: MEDAL_COLOR[b.tier] }}
              />
              <Typography
                variant="caption"
                sx={{ fontWeight: 700, display: "block", mt: 0.5 }}
              >
                {b.label}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                #{b.rank} of {b.totalPlayers}
              </Typography>
            </Box>
          </Tooltip>
        ))}
      </Stack>
    </Box>
  )
}

function PercentileTile(props: {
  label: string
  value: string | null
  percentile: number | null
}) {
  if (props.value === null) {
    return null
  }
  return (
    <StatTile
      label={props.label}
      value={props.value}
      detail={
        props.percentile !== null
          ? `beats ${props.percentile}% of players`
          : undefined
      }
    />
  )
}

type PeopleTone = "ally" | "rival" | "trophy"

const TONE_COLOR: Record<PeopleTone, string> = {
  ally: WIN_COLOR,
  rival: LOSS_COLOR,
  trophy: "#d4af37",
}

const TONE_ICON: Record<PeopleTone, React.ElementType> = {
  ally: HandshakeIcon,
  rival: SportsMmaIcon,
  trophy: EmojiEventsIcon,
}

function PeopleCard(props: {
  label: string
  name: string
  record: string
  extra?: string
  tone: PeopleTone
}) {
  const color = TONE_COLOR[props.tone]
  const Icon = TONE_ICON[props.tone]
  return (
    <Card
      variant="outlined"
      sx={{ flex: 1, minWidth: 180, borderLeft: `3px solid ${color}` }}
    >
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Stack direction="row" spacing={0.75} alignItems="center">
          <Icon sx={{ fontSize: 16, color }} />
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ lineHeight: 1 }}
          >
            {props.label}
          </Typography>
        </Stack>
        <Box sx={{ mt: 0.5 }}>
          <PlayerChip name={props.name} size="medium" />
        </Box>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {props.record}
          {props.extra ? ` · ${props.extra}` : ""}
        </Typography>
      </CardContent>
    </Card>
  )
}

/** Win vs loss average duration as two proportional bars — a comparison reads
 * faster as a bar chart than as two side-by-side numbers. */
function TempoBars(props: {
  winMinutes?: number | null
  lossMinutes?: number | null
}) {
  const win = props.winMinutes ?? null
  const loss = props.lossMinutes ?? null
  if (win === null && loss === null) {
    return null
  }
  const max = Math.max(win ?? 0, loss ?? 0, 1)
  const rows: { label: string; value: number | null; color: string }[] = [
    { label: "Avg Win Length", value: win, color: WIN_COLOR },
    { label: "Avg Loss Length", value: loss, color: LOSS_COLOR },
  ]
  return (
    <Stack spacing={1} sx={{ maxWidth: 360 }}>
      {rows.map(
        (row) =>
          row.value !== null && (
            <Box key={row.label}>
              <Stack direction="row" justifyContent="space-between">
                <Typography variant="body2" color="text.secondary">
                  {row.label}
                </Typography>
                <Typography variant="body2" sx={{ fontWeight: 700 }}>
                  {row.value}m
                </Typography>
              </Stack>
              <Box
                sx={{
                  height: 8,
                  borderRadius: 1,
                  bgcolor: "action.hover",
                  overflow: "hidden",
                  mt: 0.5,
                }}
              >
                <Box
                  sx={{
                    height: "100%",
                    width: `${((row.value ?? 0) / max) * 100}%`,
                    bgcolor: row.color,
                    borderRadius: 1,
                  }}
                />
              </Box>
            </Box>
          ),
      )}
    </Stack>
  )
}

/** One general's running win-rate line: game N as this general on the x-axis,
 * cumulative win rate on the y-axis - traces how a matchup evolved rather
 * than just its final tally. */
function GeneralWinRateChart(props: { series: GeneralWinRateSeries }) {
  const data = props.series.points.map((pt) => {
    const { low, high } = wilsonInterval(pt.wins, pt.losses)
    return {
      gameNumber: pt.gameNumber,
      winRate: Math.round(pt.winRate * 100),
      wins: pt.wins,
      losses: pt.losses,
      band: [Math.round(low * 100), Math.round(high * 100)] as [number, number],
    }
  })
  return (
    <ResponsiveContainer width="100%" height={220}>
      <ComposedChart
        data={data}
        margin={{ top: 10, right: 20, left: 0, bottom: 5 }}
      >
        <CartesianGrid strokeDasharray="5 5" vertical={false} />
        <XAxis
          dataKey="gameNumber"
          tick={{ fontSize: 12 }}
          label={{
            value: "Game # on this general",
            position: "insideBottom",
            offset: -3,
            fontSize: 12,
          }}
        />
        <YAxis
          domain={[0, 100]}
          tickFormatter={(v: number) => `${v}%`}
          width={40}
          tick={{ fontSize: 12 }}
        />
        <ChartTooltip
          labelFormatter={(v) => `Game ${v}`}
          formatter={(value, name, item) => {
            if (name === "band") {
              const [low, high] = value as [number, number]
              return [`${low}%–${high}%`, "95% CI"]
            }
            const payload = item.payload as { wins: number; losses: number }
            return [
              `${value}% (${payload.wins}W-${payload.losses}L)`,
              "Win rate",
            ]
          }}
        />
        <Area
          dataKey="band"
          name="band"
          stroke="none"
          fill={WIN_COLOR}
          fillOpacity={0.15}
          isAnimationActive={false}
        />
        <Line
          type="monotone"
          dataKey="winRate"
          stroke={WIN_COLOR}
          strokeWidth={2}
          dot={false}
        />
      </ComposedChart>
    </ResponsiveContainer>
  )
}

function GeneralWinRateOverTime(props: { series: GeneralWinRateSeries[] }) {
  const eligible = props.series.filter(
    (s) => s.points.length >= MIN_SERIES_GAMES,
  )
  const [selected, setSelected] = React.useState<number | null>(
    eligible[0]?.general ?? null,
  )
  if (eligible.length === 0) {
    return null
  }
  const current = eligible.find((s) => s.general === selected) ?? eligible[0]
  return (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Win Rate Over Time
      </Typography>
      <ToggleButtonGroup
        value={current.general}
        exclusive
        size="small"
        onChange={(_, v) => v !== null && setSelected(v)}
        sx={{ mb: 2, flexWrap: "wrap", gap: 0.5 }}
      >
        {eligible.map((s) => (
          <ToggleButton key={s.general} value={s.general}>
            {toGeneralName(s.general)}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
      <GeneralWinRateChart series={current} />
    </Box>
  )
}

// Track/band/tick/marker all share this vertical center - deriving their
// top offsets from one value keeps them aligned if a size below ever changes.
const USAGE_BAR_CENTER = 24
const USAGE_TRACK_HEIGHT = 4
const USAGE_BAND_HEIGHT = 8
const USAGE_TICK_HEIGHT = 12
const USAGE_MARKER_SIZE = 12

/** Lab-report-style range indicator: 0 always anchors the left edge, a
 * shaded band marks the peer average +/-1 standard deviation, a tick labels
 * the peer median, and a dot marks where the player's own per-game rate
 * falls - reads at a glance instead of forcing a scan across a row of
 * numbers. */
function ObjectUsageBar(props: { stat: ObjectUsageStat; markerColor: string }) {
  const { stat, markerColor } = props

  // 0 is the shared anchor every row starts from; the right edge is sized
  // per object so the peer spread, median, and player's own value all fit
  // comfortably (with a little headroom rather than sitting on the edge).
  const trackMax =
    Math.max(
      stat.peerMeanPerGame + 2 * stat.peerStddevPerGame,
      stat.peerMedianPerGame,
      stat.perGame,
      0.01,
    ) * 1.15

  const toPercent = (value: number) =>
    Math.max(0, Math.min(100, (value / trackMax) * 100))

  const bandStart = toPercent(stat.peerMeanPerGame - stat.peerStddevPerGame)
  const bandEnd = toPercent(stat.peerMeanPerGame + stat.peerStddevPerGame)
  const medianPercent = toPercent(stat.peerMedianPerGame)
  const markerPercent = toPercent(stat.perGame)
  const z = stat.zScore

  return (
    <Tooltip
      title={
        <>
          Your rate: {stat.perGame.toFixed(2)}/game
          <br />
          Peer median: {stat.peerMedianPerGame.toFixed(2)}, avg{" "}
          {stat.peerMeanPerGame.toFixed(2)} ±{stat.peerStddevPerGame.toFixed(2)}{" "}
          (n={stat.peerCount})
          {z != null && (
            <>
              <br />
              {z >= 0 ? "+" : ""}
              {z.toFixed(2)}σ from average
            </>
          )}
        </>
      }
    >
      <Box sx={{ position: "relative", height: 40 }}>
        {/* the player's own value, labeled above their marker instead of as
         * separate text elsewhere in the row */}
        <Typography
          variant="caption"
          fontWeight={700}
          sx={{
            position: "absolute",
            top: 0,
            left: `${markerPercent}%`,
            transform: "translateX(-50%)",
            whiteSpace: "nowrap",
            fontSize: 10,
            lineHeight: 1,
            color: markerColor,
          }}
        >
          {stat.perGame.toFixed(2)}
        </Typography>
        <Box
          sx={{
            position: "absolute",
            top: USAGE_BAR_CENTER - USAGE_TRACK_HEIGHT / 2,
            left: 0,
            right: 0,
            height: USAGE_TRACK_HEIGHT,
            borderRadius: 2,
            bgcolor: "action.hover",
          }}
        />
        <Box
          sx={{
            position: "absolute",
            top: USAGE_BAR_CENTER - USAGE_BAND_HEIGHT / 2,
            left: `${bandStart}%`,
            width: `${bandEnd - bandStart}%`,
            height: USAGE_BAND_HEIGHT,
            borderRadius: 1,
            bgcolor: "action.selected",
          }}
        />
        <Box
          sx={{
            position: "absolute",
            top: USAGE_BAR_CENTER - USAGE_TICK_HEIGHT / 2,
            height: USAGE_TICK_HEIGHT,
            left: `${medianPercent}%`,
            width: "2px",
            bgcolor: "text.disabled",
          }}
        />
        <Box
          sx={{
            position: "absolute",
            top: USAGE_BAR_CENTER,
            left: `${markerPercent}%`,
            width: USAGE_MARKER_SIZE,
            height: USAGE_MARKER_SIZE,
            transform: "translate(-50%, -50%)",
            borderRadius: "50%",
            bgcolor: markerColor,
            border: (theme) => `2px solid ${theme.palette.background.paper}`,
            boxShadow: 1,
          }}
        />
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            position: "absolute",
            top: 30,
            left: `${medianPercent}%`,
            transform: "translateX(-50%)",
            whiteSpace: "nowrap",
            fontSize: 10,
            lineHeight: 1,
          }}
        >
          {stat.peerMedianPerGame.toFixed(2)}
        </Typography>
      </Box>
    </Tooltip>
  )
}

function ObjectUsageRow(props: { stat: ObjectUsageStat; markerColor: string }) {
  const { stat } = props
  return (
    <Box
      sx={{
        display: "flex",
        alignItems: "center",
        gap: 1.5,
        py: 0.75,
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stack
        direction="row"
        spacing={0.5}
        alignItems="center"
        sx={{ flexBasis: "20%", minWidth: 140, flexShrink: 0 }}
      >
        <DisplayGeneral general={stat.general} />
        <Typography variant="body2" noWrap>
          {stat.name}
        </Typography>
      </Stack>
      <Box sx={{ flexGrow: 1, minWidth: 0 }}>
        <ObjectUsageBar stat={stat} markerColor={props.markerColor} />
      </Box>
    </Box>
  )
}

/** Every object in one category (units/buildings/upgrades), sorted by how
 * far the player sits from the peer average - the point is to surface the
 * whole distribution, not just the extremes favorites/aversions cover. */
function ObjectUsageList(props: {
  stats: ObjectUsageStat[]
  markerColor: string
}) {
  const rows = React.useMemo(
    () =>
      [...props.stats].sort(
        (a, b) => Math.abs(b.zScore ?? 0) - Math.abs(a.zScore ?? 0),
      ),
    [props.stats],
  )

  if (rows.length === 0) {
    return (
      <Typography variant="body2" color="text.secondary" sx={{ py: 1 }}>
        Not enough games to compare yet.
      </Typography>
    )
  }

  return (
    <Box>
      {rows.map((s) => (
        <ObjectUsageRow
          key={`${s.general}-${s.name}`}
          stat={s}
          markerColor={props.markerColor}
        />
      ))}
    </Box>
  )
}

const USAGE_CATEGORY_LABEL: Record<ObjectUsageStatCategoryEnum, string> = {
  units: "Units",
  buildings: "Buildings",
  upgrades: "Upgrades",
}

function ObjectUsageSection(props: {
  objectUsage: ObjectUsageStat[]
  markerColor: string
}) {
  const [category, setCategory] =
    React.useState<ObjectUsageStatCategoryEnum>("units")
  if (props.objectUsage.length === 0) {
    return null
  }
  const byCategory = {
    units: props.objectUsage.filter((s) => s.category === "units"),
    buildings: props.objectUsage.filter((s) => s.category === "buildings"),
    upgrades: props.objectUsage.filter((s) => s.category === "upgrades"),
  }
  return (
    <Accordion disableGutters TransitionProps={{ unmountOnExit: true }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="h6">Unit / Building / Upgrade Usage</Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
          Every object with enough games to compare. The shaded band is the peer
          average ±1 standard deviation; the dot is where this player falls.
        </Typography>
        <Tabs
          value={category}
          onChange={(_, v) => setCategory(v)}
          sx={{ mb: 1.5 }}
        >
          {(Object.keys(byCategory) as ObjectUsageStatCategoryEnum[]).map(
            (key) => (
              <Tab
                key={key}
                value={key}
                label={`${USAGE_CATEGORY_LABEL[key]} (${byCategory[key].length})`}
              />
            ),
          )}
        </Tabs>
        <ObjectUsageList
          stats={byCategory[category]}
          markerColor={props.markerColor}
        />
      </AccordionDetails>
    </Accordion>
  )
}

function ProfileBody(props: { profile: PlayerProfile }) {
  const p = props.profile
  const c = p.computed ?? null
  const accent = usePlayerAccentColor(p.player)
  const radarData = p.generals
    .filter((g) => g.games >= 5)
    .map((g) => ({
      name: toGeneralName(g.general),
      winRate: Math.round(g.winRate * 100),
    }))
  const hasMaps = p.favoriteMap != null || p.bestMap != null
  const hasTempo =
    p.avgWinDurationMinutes != null || p.avgLossDurationMinutes != null

  return (
    <Stack spacing={3} sx={{ mt: 2 }}>
      <Box
        sx={{
          borderLeft: `4px solid ${accent}`,
          bgcolor: alpha(accent, 0.06),
          borderRadius: 1,
          px: 2,
          py: 1.5,
        }}
      >
        <Stack
          direction="row"
          spacing={2}
          alignItems="center"
          sx={{ flexWrap: "wrap" }}
        >
          <PlayerChip name={p.player} size="medium" />
          <Typography variant="h6">
            {p.wins}W – {p.losses}L
          </Typography>
          <WinRateChip wins={p.wins} losses={p.losses} />
          <Typography variant="body2" color="text.secondary">
            {p.games} competitive games
          </Typography>
        </Stack>
      </Box>

      {c === null && (
        <Alert severity="info">
          Deep stats (signature units, badges) haven&apos;t been computed yet
          for this data version — they refresh nightly.
        </Alert>
      )}

      {c !== null && (
        <Box>
          <SectionHeader
            icon={<StarIcon />}
            title="Signature Picks"
            subtitle={`built more than other players of the same general, over ${c.gamesAnalyzed} games`}
          />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            {(
              [
                ["Favorite Unit", c.favoriteUnit],
                ["Favorite Building", c.favoriteBuilding],
                ["Favorite Upgrade", c.favoriteUpgrade],
                ["Favorite Power", c.favoritePower],
              ] as const
            ).map(([label, favorite]) => (
              <FavoriteCard
                key={label}
                label={label}
                favorite={favorite ?? null}
              />
            ))}
          </Stack>
        </Box>
      )}

      {c !== null && <AversionChips aversions={c.aversions ?? []} />}
      {c !== null && <BadgeGrid badges={c.badges ?? []} />}

      <Box>
        <SectionHeader icon={<MilitaryTechIcon />} title="Generals" />
        <Grid container spacing={2} alignItems="center">
          <Grid size={{ xs: 12, md: 5 }}>
            {radarData.length >= 3 ? (
              <WinRateRadar data={radarData} />
            ) : (
              <Typography variant="body2" color="text.secondary">
                Not enough games per general for a radar
              </Typography>
            )}
          </Grid>
          <Grid size={{ xs: 12, md: 7 }}>
            <Stack direction="row" spacing={1.5}>
              {p.mostPlayedGeneral && (
                <StatTile
                  label="Most Played General"
                  value={toGeneralName(p.mostPlayedGeneral.general)}
                  detail={`${p.mostPlayedGeneral.games} games, ${formatPercent(p.mostPlayedGeneral.winRate)} WR`}
                />
              )}
              {p.bestGeneral && (
                <StatTile
                  label="Best General"
                  value={toGeneralName(p.bestGeneral.general)}
                  detail={`${formatPercent(p.bestGeneral.winRate)} over ${p.bestGeneral.games} games`}
                />
              )}
            </Stack>
          </Grid>
        </Grid>
        <Box sx={{ mt: 2 }}>
          <GeneralWinRateOverTime
            key={p.player}
            series={p.generalWinRateOverTime ?? []}
          />
        </Box>
      </Box>

      {hasMaps && (
        <Box>
          <SectionHeader icon={<MapIcon />} title="Maps" />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            {p.favoriteMap && (
              <StatTile
                label="Most Played Map"
                value={displayMapName(p.favoriteMap.map)}
                detail={`${p.favoriteMap.games} games, ${p.favoriteMap.wins}W-${p.favoriteMap.losses}L`}
              />
            )}
            {p.bestMap && (
              <StatTile
                label="Best Map"
                value={displayMapName(p.bestMap.map)}
                detail={`${p.bestMap.wins}W-${p.bestMap.losses}L`}
              />
            )}
          </Stack>
        </Box>
      )}

      <Box>
        <SectionHeader icon={<GroupsIcon />} title="People" />
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
          {p.favoriteTeammate && (
            <PeopleCard
              tone="ally"
              label="Favorite Teammate"
              name={p.favoriteTeammate.name}
              record={`${p.favoriteTeammate.winsTogether}W in ${p.favoriteTeammate.gamesTogether} games together`}
              extra={
                p.favoriteTeammate.synergy != null
                  ? `synergy ${p.favoriteTeammate.synergy}`
                  : undefined
              }
            />
          )}
          {p.nemesis && (
            <PeopleCard
              tone="rival"
              label="Nemesis"
              name={p.nemesis.name}
              record={`${p.nemesis.wins}W-${p.nemesis.losses}L against`}
            />
          )}
          {p.favoriteVictim && (
            <PeopleCard
              tone="trophy"
              label="Favorite Victim"
              name={p.favoriteVictim.name}
              record={`${p.favoriteVictim.wins}W-${p.favoriteVictim.losses}L against`}
            />
          )}
        </Stack>
      </Box>

      {hasTempo && (
        <Box>
          <SectionHeader icon={<SpeedIcon />} title="Tempo" />
          <TempoBars
            winMinutes={p.avgWinDurationMinutes}
            lossMinutes={p.avgLossDurationMinutes}
          />
        </Box>
      )}

      {c !== null && (
        <Box>
          <SectionHeader icon={<InsightsIcon />} title="Tendencies" />
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            {(
              [
                [
                  "Avg APM",
                  c.avgApm != null ? `${c.avgApm}` : null,
                  c.apmPercentile ?? null,
                ],
                [
                  "First Blood Rate",
                  c.firstBloodRate != null
                    ? formatPercent(c.firstBloodRate)
                    : null,
                  c.firstBloodPercentile ?? null,
                ],
                [
                  "Avg Time to Rank 5",
                  c.avgTimeToRank5 != null ? `${c.avgTimeToRank5}m` : null,
                  c.rank5Percentile ?? null,
                ],
                [
                  "Superweapons Built",
                  c.superweaponsBuiltPerGame != null
                    ? `${c.superweaponsBuiltPerGame}/game`
                    : null,
                  c.superweaponPercentile ?? null,
                ],
              ] as const
            ).map(([label, value, percentile]) => (
              <PercentileTile
                key={label}
                label={label}
                value={value}
                percentile={percentile}
              />
            ))}
          </Stack>
        </Box>
      )}

      {c !== null && (
        <ObjectUsageSection
          objectUsage={c.objectUsage ?? []}
          markerColor={accent}
        />
      )}
    </Stack>
  )
}

export default function DisplayPlayerProfile() {
  const [players, setPlayers] = React.useState<string[]>([])
  const [player, setPlayer] = React.useState<string | null>(playerFromUrl)
  const [profile, setProfile] = React.useState<PlayerProfile | null>(null)
  const [loading, setLoading] = React.useState(false)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    // Only players with a full profile (enough games for favorites/badges to
    // mean anything, computer players already excluded) show up as options.
    Client.getEligiblePlayersApiPlayerProfileEligiblePlayersGet()
      .then((names) => setPlayers(names.filter((n): n is string => n != null)))
      .catch(showError)
  }, [showError])

  React.useEffect(() => {
    if (!player) {
      setProfile(null)
      return
    }
    let cancelled = false
    setLoading(true)
    Client.getPlayerProfileApiPlayerProfileGet({ player })
      .then((p) => !cancelled && setProfile(p))
      .catch((e) => {
        if (!cancelled) {
          setProfile(null)
          showError(e)
        }
      })
      .finally(() => !cancelled && setLoading(false))
    return () => {
      cancelled = true
    }
  }, [player, showError])

  return (
    <Paper sx={{ p: 2, maxWidth: 1400 }}>
      <Typography variant="h5" sx={{ mb: 2 }}>
        Player Profile
      </Typography>
      {errorSnackbar}
      <Autocomplete
        options={players}
        value={player}
        onChange={(_, v) => {
          setPlayer(v)
          setPlayerInUrl(v)
        }}
        sx={{ maxWidth: 300 }}
        renderInput={(params) => <TextField {...params} label="Player" />}
      />
      {loading && <Loading />}
      {!loading && profile && <ProfileBody profile={profile} />}
      {!loading && !profile && !player && (
        <Typography variant="body2" color="text.secondary" sx={{ mt: 2 }}>
          Pick a player to see what they&apos;re known for.
        </Typography>
      )}
    </Paper>
  )
}
