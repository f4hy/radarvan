import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Alert from "@mui/material/Alert"
import Autocomplete from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Card from "@mui/material/Card"
import CardContent from "@mui/material/CardContent"
import Chip from "@mui/material/Chip"
import Stack from "@mui/material/Stack"
import Table from "@mui/material/Table"
import TableContainer from "@mui/material/TableContainer"
import TableBody from "@mui/material/TableBody"
import TableCell from "@mui/material/TableCell"
import TableHead from "@mui/material/TableHead"
import TableRow from "@mui/material/TableRow"
import TextField from "@mui/material/TextField"
import Tooltip from "@mui/material/Tooltip"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { GeneralPowers, PowerRow, PowerStats, UnusualPick } from "./api"
import { Client } from "./Client"
import DisplayGeneral from "./Generals"
import { toGeneralName } from "./general_utils"
import Loading from "./Loading"
import Page from "./Page"
import { useErrorSnackbar } from "./useErrorSnackbar"
import { formatPercent } from "./utils"

// Below this the chip would read "0.00/min vs 0.00" - which is every China and
// Infantry game, since neither has a scouting power to fire.
const RECON_CHIP_FLOOR = 0.005

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

// Percentage points, not a ratio: "takes it 30pp more often than the group" is
// the sentence a reader can act on. A ratio would make 2%-vs-1% look like the
// biggest gap on the page.
function formatGap(gap: number): string {
  const points = Math.round(gap * 100)
  return `${points > 0 ? "+" : ""}${points}pp`
}

function formatRate(perMinute: number): string {
  return perMinute.toFixed(2)
}

/** A player figure with the group's in the same cell, so the eye compares once. */
function Compare(props: {
  value: string
  group: string
  gap: number
  /** Below this the difference isn't worth coloring. */
  threshold: number
}) {
  const notable = Math.abs(props.gap) >= props.threshold
  const color = !notable
    ? "text.primary"
    : props.gap > 0
      ? "success.main"
      : "error.main"
  return (
    <Stack direction="row" spacing={0.75} sx={{ alignItems: "baseline" }}>
      <Box component="span" sx={{ color, fontWeight: notable ? 600 : 400 }}>
        {props.value}
      </Box>
      <Box component="span" sx={{ color: "text.disabled", fontSize: "0.8em" }}>
        vs {props.group}
      </Box>
    </Stack>
  )
}

function PowerTable(props: { rows: PowerRow[] }) {
  return (
    <TableContainer sx={{ overflowX: "auto" }}>
      <Table size="small">
        <TableHead>
          <TableRow>
            <TableCell>Power</TableCell>
            <TableCell align="right">
              <Tooltip title="Share of this player's games on this general in which they bought the power at all, against the rest of the group's share.">
                <span>Pick rate</span>
              </Tooltip>
            </TableCell>
            <TableCell align="right">
              <Tooltip title="Average levels bought in the games they took it. 1.0 means they never upgrade past the first level.">
                <span>Levels</span>
              </Tooltip>
            </TableCell>
            <TableCell align="right">
              <Tooltip title="Average minute they open the power, over the games they bought it.">
                <span>Bought at</span>
              </Tooltip>
            </TableCell>
            <TableCell align="right">
              <Tooltip title="Total activations across the games shown.">
                <span>Uses</span>
              </Tooltip>
            </TableCell>
            <TableCell align="right">
              <Tooltip title="Activations per minute alive - eliminations shorten the denominator, so an early death doesn't read as passivity.">
                <span>Per min</span>
              </Tooltip>
            </TableCell>
          </TableRow>
        </TableHead>
        <TableBody>
          {props.rows.map((row) => (
            <TableRow key={row.power} hover>
              <TableCell>
                <Stack
                  direction="row"
                  spacing={0.75}
                  sx={{ alignItems: "center" }}
                >
                  <span>{row.power}</span>
                  {!row.purchasable && (
                    <Tooltip title="Granted by a building rather than bought with a generals point, so it has usage but no pick rate.">
                      <Chip label="free" size="small" variant="outlined" />
                    </Tooltip>
                  )}
                  {row.unlocksUnit && (
                    <Tooltip title="A generals point that unlocks a unit rather than a panel button - bought like a power, never fired.">
                      <Chip label="unit" size="small" variant="outlined" />
                    </Tooltip>
                  )}
                </Stack>
              </TableCell>
              <TableCell align="right">
                {row.purchasable ? (
                  <Compare
                    value={formatPercent(row.pickRate)}
                    group={formatPercent(row.groupPickRate)}
                    gap={row.pickRate - row.groupPickRate}
                    threshold={0.15}
                  />
                ) : (
                  <Box component="span" sx={{ color: "text.disabled" }}>
                    —
                  </Box>
                )}
              </TableCell>
              <TableCell align="right">
                {row.gamesPicked > 0 ? (
                  <Compare
                    value={row.avgLevels.toFixed(1)}
                    group={
                      row.groupAvgLevels > 0
                        ? row.groupAvgLevels.toFixed(1)
                        : "—"
                    }
                    gap={row.avgLevels - row.groupAvgLevels}
                    threshold={0.5}
                  />
                ) : (
                  <Box component="span" sx={{ color: "text.disabled" }}>
                    —
                  </Box>
                )}
              </TableCell>
              <TableCell align="right">
                {row.avgPickMinute != null ? (
                  <Box component="span">{row.avgPickMinute.toFixed(1)}m</Box>
                ) : (
                  <Box component="span" sx={{ color: "text.disabled" }}>
                    —
                  </Box>
                )}
              </TableCell>
              <TableCell align="right">
                {row.uses > 0 ? (
                  row.uses
                ) : (
                  <Box component="span" sx={{ color: "text.disabled" }}>
                    —
                  </Box>
                )}
              </TableCell>
              <TableCell align="right">
                <Compare
                  value={formatRate(row.usesPerMinute)}
                  group={formatRate(row.groupUsesPerMinute)}
                  gap={row.usesPerMinute - row.groupUsesPerMinute}
                  threshold={0.1}
                />
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </TableContainer>
  )
}

function GeneralSection(props: {
  general: GeneralPowers
  defaultExpanded: boolean
}) {
  const { general } = props
  const reconGap = general.reconPerMinute - general.groupReconPerMinute
  return (
    <Accordion defaultExpanded={props.defaultExpanded} disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack
          direction="row"
          spacing={2}
          sx={{ alignItems: "center", flexWrap: "wrap", width: "100%" }}
          useFlexGap
        >
          <DisplayGeneral general={general.general} />
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            {general.games} game{general.games === 1 ? "" : "s"} · group has{" "}
            {general.groupGames}
          </Typography>
          {Math.max(general.reconPerMinute, general.groupReconPerMinute) >=
            RECON_CHIP_FLOOR && (
            <Tooltip title="Spy Drone + Spy Satellite + Radar Van Scan per minute alive - how often they actually look at the map, against the rest of the group on this general.">
              <Chip
                size="small"
                variant="outlined"
                color={
                  Math.abs(reconGap) < 0.1
                    ? "default"
                    : reconGap > 0
                      ? "success"
                      : "error"
                }
                label={`recon ${formatRate(general.reconPerMinute)}/min vs ${formatRate(
                  general.groupReconPerMinute,
                )}`}
              />
            </Tooltip>
          )}
        </Stack>
      </AccordionSummary>
      <AccordionDetails sx={{ p: 0 }}>
        <PowerTable rows={general.rows} />
      </AccordionDetails>
    </Accordion>
  )
}

function SignatureCard(props: { unusual: UnusualPick[] }) {
  if (props.unusual.length === 0) {
    return null
  }
  return (
    <Card variant="outlined" sx={{ mb: 2 }}>
      <CardContent>
        <Typography variant="subtitle1" sx={{ mb: 0.5 }}>
          Stands out from the group
        </Typography>
        <Typography variant="body2" sx={{ color: "text.secondary", mb: 1.5 }}>
          Picks where this player&apos;s rate is furthest from everyone
          else&apos;s on the same general, weighted by how many games back it
          up.
        </Typography>
        <Stack direction="row" spacing={1} useFlexGap sx={{ flexWrap: "wrap" }}>
          {props.unusual.map((pick) => (
            <Tooltip
              key={`${pick.general}-${pick.power}`}
              title={`${formatPercent(pick.pickRate)} of their ${pick.games} games on this general, against ${formatPercent(
                pick.groupPickRate,
              )} for the rest of the group.`}
            >
              <Chip
                // The general is part of the label, not decoration: the same
                // power is a different habit on a different general, and
                // without it the list repeats "Cluster Mines" three times with
                // no way to tell which one is which.
                label={`${toGeneralName(pick.general)} · ${pick.power} ${formatGap(
                  pick.pickRate - pick.groupPickRate,
                )}`}
                color={pick.direction === "over" ? "success" : "error"}
                variant="outlined"
                size="small"
              />
            </Tooltip>
          ))}
        </Stack>
      </CardContent>
    </Card>
  )
}

export default function Powers() {
  const [stats, setStats] = React.useState<PowerStats | null>(null)
  const [player, setPlayer] = React.useState<string | null>(playerFromUrl)
  const [loading, setLoading] = React.useState(true)
  const { showError, errorSnackbar } = useErrorSnackbar()

  React.useEffect(() => {
    setLoading(true)
    Client.getPowerStatsApiPowerStatsGet(player ? { player } : {})
      .then(setStats)
      .catch(showError)
      .finally(() => setLoading(false))
  }, [player, showError])

  const profile = stats?.profile ?? null

  return (
    <Page
      title="Generals Powers"
      description="What each player spends generals points on, and how often they fire what they bought. Picks come from the replay's PurchaseScience orders; activations are counted per minute the player was still alive. Every figure is compared against the rest of the group on the same general."
      actions={
        <Autocomplete
          options={stats?.players ?? []}
          value={player}
          onChange={(_, value) => {
            setPlayer(value)
            setPlayerInUrl(value)
          }}
          sx={{ minWidth: 260 }}
          size="small"
          renderInput={(params) => <TextField {...params} label="Player" />}
        />
      }
      surface={false}
    >
      {loading && <Loading />}
      {!loading && !player && (
        <Typography variant="body2" sx={{ color: "text.secondary" }}>
          Pick a player to see which powers they take, and which ones nobody
          else does.
        </Typography>
      )}
      {!loading && player && profile && profile.generals.length === 0 && (
        <Alert severity="info">
          No general with enough games yet for {player}. Power data covers{" "}
          {stats?.matches ?? 0} matches so far.
        </Alert>
      )}
      {!loading && profile && profile.generals.length > 0 && (
        <>
          <SignatureCard unusual={profile.unusual} />
          {profile.generals.map((general, index) => (
            <GeneralSection
              key={general.general}
              general={general}
              defaultExpanded={index < 2}
            />
          ))}
        </>
      )}
      {errorSnackbar}
    </Page>
  )
}
