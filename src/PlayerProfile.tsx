import * as React from "react"
import Alert from "@mui/material/Alert"
import Autocomplete from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Card from "@mui/material/Card"
import CardContent from "@mui/material/CardContent"
import Chip from "@mui/material/Chip"
import Grid from "@mui/material/Grid"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import TextField from "@mui/material/TextField"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import { Client } from "./Client"
import { FavoriteObject, PlayerProfile, ProfileBadge } from "./api"
import Loading from "./Loading"
import PlayerChip from "./PlayerChip"
import WinRateChip from "./WinRateChip"
import WinRateRadar from "./WinRateRadar"
import { toGeneralName } from "./general_utils"
import { displayMapName, formatPercent } from "./utils"
import { useErrorSnackbar } from "./useErrorSnackbar"

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

function FavoriteCard(props: {
  label: string
  favorite: FavoriteObject | null
}) {
  const fav = props.favorite
  return (
    <Card variant="outlined" sx={{ flex: 1, minWidth: 200 }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="overline" color="text.secondary" display="block">
          {props.label}
        </Typography>
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
              <Chip size="small" label={toGeneralName(fav.general)} />
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
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Avoids
      </Typography>
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
        {props.aversions.map((a) => (
          <Tooltip
            key={`${a.general}-${a.name}`}
            title={`Peers build ${a.peerPerGame}/game on ${toGeneralName(a.general)}; they build ${a.perGame}`}
          >
            <Chip
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

const MEDAL_EMOJI: Record<string, string> = {
  gold: "🥇",
  silver: "🥈",
  bronze: "🥉",
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
    <Box sx={{ mt: 2 }}>
      <Typography variant="subtitle1" sx={{ mb: 1 }}>
        Badges
      </Typography>
      <Stack direction="row" spacing={1} sx={{ flexWrap: "wrap", gap: 1 }}>
        {props.badges.map((b) => (
          <Tooltip
            key={b.key}
            title={
              <>
                <div>{b.description}</div>
                <div>
                  {b.value.toFixed(2)}/game — #{b.rank} of {b.totalPlayers}
                </div>
              </>
            }
          >
            <Chip
              variant="outlined"
              label={`${MEDAL_EMOJI[b.tier]} ${b.label}`}
              sx={{
                borderColor: MEDAL_COLOR[b.tier],
                color: MEDAL_COLOR[b.tier],
                fontWeight: 600,
              }}
            />
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

function PeopleCard(props: {
  label: string
  name: string
  record: string
  extra?: string
}) {
  return (
    <Card variant="outlined" sx={{ flex: 1, minWidth: 180 }}>
      <CardContent sx={{ py: 1.5, "&:last-child": { pb: 1.5 } }}>
        <Typography variant="overline" color="text.secondary" display="block">
          {props.label}
        </Typography>
        <PlayerChip name={props.name} size="medium" />
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          {props.record}
          {props.extra ? ` · ${props.extra}` : ""}
        </Typography>
      </CardContent>
    </Card>
  )
}

function ProfileBody(props: { profile: PlayerProfile }) {
  const p = props.profile
  const c = p.computed ?? null
  const radarData = p.generals
    .filter((g) => g.games >= 5)
    .map((g) => ({
      name: toGeneralName(g.general),
      winRate: Math.round(g.winRate * 100),
    }))
  return (
    <Stack spacing={2} sx={{ mt: 2 }}>
      <Stack direction="row" spacing={2} alignItems="center">
        <PlayerChip name={p.player} size="medium" />
        <Typography variant="h6">
          {p.wins}W – {p.losses}L
        </Typography>
        <WinRateChip wins={p.wins} losses={p.losses} />
        <Typography variant="body2" color="text.secondary">
          {p.games} competitive games
        </Typography>
      </Stack>

      {c === null && (
        <Alert severity="info">
          Deep stats (signature units, badges) haven&apos;t been computed yet
          for this data version — they refresh nightly.
        </Alert>
      )}

      {c !== null && (
        <Box>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Signature picks{" "}
            <Typography component="span" variant="body2" color="text.secondary">
              (built more than other players of the same general, over{" "}
              {c.gamesAnalyzed} games)
            </Typography>
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <FavoriteCard
              label="Favorite Unit"
              favorite={c.favoriteUnit ?? null}
            />
            <FavoriteCard
              label="Favorite Building"
              favorite={c.favoriteBuilding ?? null}
            />
            <FavoriteCard
              label="Favorite Upgrade"
              favorite={c.favoriteUpgrade ?? null}
            />
            <FavoriteCard
              label="Favorite Power"
              favorite={c.favoritePower ?? null}
            />
          </Stack>
          <AversionChips aversions={c.aversions ?? []} />
          <BadgeGrid badges={c.badges ?? []} />
        </Box>
      )}

      <Grid container spacing={2}>
        <Grid size={{ xs: 12, md: 5 }}>
          <Typography variant="subtitle1">Generals</Typography>
          {radarData.length >= 3 ? (
            <WinRateRadar data={radarData} />
          ) : (
            <Typography variant="body2" color="text.secondary">
              Not enough games per general for a radar
            </Typography>
          )}
        </Grid>
        <Grid size={{ xs: 12, md: 7 }}>
          <Stack spacing={1.5} sx={{ mt: 3 }}>
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
            <Stack direction="row" spacing={1.5}>
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
            <Stack direction="row" spacing={1.5}>
              {p.avgWinDurationMinutes !== null &&
                p.avgWinDurationMinutes !== undefined && (
                  <StatTile
                    label="Avg Win Length"
                    value={`${p.avgWinDurationMinutes}m`}
                  />
                )}
              {p.avgLossDurationMinutes !== null &&
                p.avgLossDurationMinutes !== undefined && (
                  <StatTile
                    label="Avg Loss Length"
                    value={`${p.avgLossDurationMinutes}m`}
                  />
                )}
            </Stack>
          </Stack>
        </Grid>
      </Grid>

      <Box>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          People
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
          {p.favoriteTeammate && (
            <PeopleCard
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
              label="Nemesis"
              name={p.nemesis.name}
              record={`${p.nemesis.wins}W-${p.nemesis.losses}L against`}
            />
          )}
          {p.favoriteVictim && (
            <PeopleCard
              label="Favorite Victim"
              name={p.favoriteVictim.name}
              record={`${p.favoriteVictim.wins}W-${p.favoriteVictim.losses}L against`}
            />
          )}
        </Stack>
      </Box>

      {c !== null && (
        <Box>
          <Typography variant="subtitle1" sx={{ mb: 1 }}>
            Tendencies
          </Typography>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <PercentileTile
              label="Avg APM"
              value={c.avgApm != null ? `${c.avgApm}` : null}
              percentile={c.apmPercentile ?? null}
            />
            <PercentileTile
              label="First Blood Rate"
              value={
                c.firstBloodRate != null
                  ? formatPercent(c.firstBloodRate)
                  : null
              }
              percentile={c.firstBloodPercentile ?? null}
            />
            <PercentileTile
              label="Avg Time to Rank 5"
              value={c.avgTimeToRank5 != null ? `${c.avgTimeToRank5}m` : null}
              percentile={c.rank5Percentile ?? null}
            />
            <PercentileTile
              label="Superweapons Built"
              value={
                c.superweaponsBuiltPerGame != null
                  ? `${c.superweaponsBuiltPerGame}/game`
                  : null
              }
              percentile={c.superweaponPercentile ?? null}
            />
          </Stack>
        </Box>
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
