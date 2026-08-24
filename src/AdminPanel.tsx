// Operational control panel: one button per admin task (scrape, reparse,
// backfill, recompute, override, delete).
//
// Everything here goes through `adminApi.adminRequest` — a same-origin fetch so
// the session cookie rides along. The backend gates each route on
// `dependencies=OPS_ADMIN` (player_ids.OPS_ADMINS), so this page is *not* the
// security boundary; hiding it from non-admins is presentation only.
//
// Tasks are data, not JSX: add an entry to SECTIONS and it renders, validates,
// runs, and reports like the rest. A task whose effect cannot be taken back -
// it rewrites or destroys stored data, or it bills an LLM call - sets
// `confirmWord`, which arms its button only once the operator has typed that
// exact string, and `confirmLabel` to say which kind it is.

import * as React from "react"
import Alert from "@mui/material/Alert"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import CircularProgress from "@mui/material/CircularProgress"
import Divider from "@mui/material/Divider"
import MenuItem from "@mui/material/MenuItem"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import TextField from "@mui/material/TextField"
import Typography from "@mui/material/Typography"
import LoginIcon from "@mui/icons-material/Login"
import PlayArrowIcon from "@mui/icons-material/PlayArrow"
import WarningAmberIcon from "@mui/icons-material/WarningAmber"
import { useAuth, useIsOpsAdmin } from "./AuthContext"
import { startDiscordLogin } from "./auth"
import { AdminMethod, QueryValues, adminRequest } from "./adminApi"

type Values = Record<string, string>

interface TaskField {
  name: string
  label: string
  type: "number" | "text" | "date"
  defaultValue: string
  // Present for a dropdown instead of a free-text/number input.
  options?: readonly { value: string; label: string }[]
  width?: number
  // Blank is a legitimate value — the handler defaults the param, and
  // `adminApi` drops empty query values rather than sending `?winner=`.
  // Everything else must be filled in before the task can run.
  optional?: boolean
}

interface AdminTask {
  id: string
  title: string
  description: string
  method: AdminMethod
  // Path is a function of the field values so a task can put one in the URL
  // (/api/scrape/{days}) and the rest in the query string.
  path: (v: Values) => string
  // Field names sent as query params. Anything consumed by `path` is left out.
  query?: readonly string[]
  fields?: readonly TaskField[]
  // Destructive tasks only: the exact string the operator must type to arm the
  // button. A function so it can demand the match id itself, which makes a
  // mis-typed id impossible to confirm rather than merely discouraged.
  confirmWord?: (v: Values) => string
  // What the warning chip says. Defaults to "destructive"; a task that spends
  // money rather than destroying data says so instead, because the operator is
  // being warned about two different things.
  confirmLabel?: string
}

interface TaskSection {
  title: string
  blurb: string
  tasks: readonly AdminTask[]
}

const num = (
  name: string,
  label: string,
  defaultValue: string,
  width = 130,
): TaskField => ({ name, label, type: "number", defaultValue, width })

const BOOL_OPTIONS = [
  { value: "true", label: "true" },
  { value: "false", label: "false" },
] as const

// Team is an IntEnum on the wire (api_types/common.py); NONE=0 clears the
// winner while still recording the override.
const TEAM_OPTIONS = [
  { value: "", label: "(unset)" },
  { value: "0", label: "0 — none" },
  { value: "1", label: "1" },
  { value: "2", label: "2" },
  { value: "3", label: "3" },
  { value: "4", label: "4" },
] as const

const SECTIONS: readonly TaskSection[] = [
  {
    title: "Ingest",
    blurb:
      "Pull new replays in and turn parsed JSON into matches. The scheduler already runs the scrape every 6h; these are the manual pokes.",
    tasks: [
      {
        id: "scrape",
        title: "Scrape gentool",
        description:
          "Scrape the last N days of replays and register them. Runs in the background — the response only confirms it was scheduled.",
        method: "POST",
        path: (v) => `/api/scrape/${v.days}`,
        fields: [num("days", "Days", "1")],
      },
      {
        id: "register_matches",
        title: "Register matches",
        description:
          "Create Match rows for any parsed replay JSON that has none yet.",
        method: "POST",
        path: () => "/api/register_matches/",
        query: ["max_to_update"],
        fields: [num("max_to_update", "Max", "100")],
      },
      {
        id: "register_replay_url",
        title: "Register replay from URL",
        description:
          "Fetch, parse, and register a single .rep from a URL. No-ops if it is already parsed.",
        method: "POST",
        path: () => "/api/register_replay_url",
        query: ["url_of_replay"],
        fields: [
          {
            name: "url_of_replay",
            label: "Replay URL",
            type: "text",
            defaultValue: "",
            width: 420,
          },
        ],
      },
    ],
  },
  {
    title: "Reparse",
    blurb:
      "Re-run the parser over replays already stored. Anything that calls cncstats is slow and rate-limited — keep the batch sizes small.",
    tasks: [
      {
        id: "reparse",
        title: "Reparse one match",
        description:
          "Re-run cncstats on a single match and recompute its composition.",
        method: "POST",
        path: (v) => `/api/reparse/${v.match_id}`,
        fields: [num("match_id", "Match ID", "")],
      },
      {
        id: "reparse_recent",
        title: "Reparse recent",
        description:
          "Re-run cncstats on every match played in the last N days.",
        method: "POST",
        path: () => "/api/reparse_recent/",
        query: ["days"],
        fields: [num("days", "Days", "3")],
      },
      {
        id: "reparse_before_date",
        title: "Reparse before date",
        description:
          "Re-run cncstats on matches whose parsed JSON is older than the given date — how new parser fields get picked up.",
        method: "POST",
        path: () => "/api/reparse_before_date/",
        query: ["before", "max_to_update"],
        fields: [
          {
            name: "before",
            label: "Before",
            type: "date",
            defaultValue: "",
            width: 170,
          },
          num("max_to_update", "Max", "10"),
        ],
      },
      {
        id: "reparse_non_v2",
        title: "Reparse non-v2",
        description:
          "Re-run cncstats on matches still stored in the pre-v2 JSON shape. Runs concurrently.",
        method: "POST",
        path: () => "/api/reparse_non_v2/",
        query: ["max_to_update", "max_concurrent"],
        fields: [
          num("max_to_update", "Max", "10"),
          num("max_concurrent", "Concurrency", "8", 150),
        ],
      },
      {
        id: "refresh_matches_from_json",
        title: "Refresh from stored JSON",
        description:
          "Rebuild Match rows from the JSON already in S3 and write back the ones that differ. Does NOT call cncstats, so it is cheap.",
        method: "POST",
        path: () => "/api/refresh_matches_from_json/",
        query: ["max_to_update"],
        fields: [num("max_to_update", "Max", "10")],
      },
      {
        id: "fix_incomplete",
        title: "Fix incomplete-with-winner",
        description:
          "Reparse matches flagged incomplete that nonetheless recorded a winner.",
        method: "POST",
        path: () => "/api/fix_incomplete/",
        query: ["max_to_update"],
        fields: [num("max_to_update", "Max", "1")],
      },
      {
        id: "fix_unk_player",
        title: "Fix unknown players",
        description: 'Reparse matches containing a player resolved as "unk".',
        method: "POST",
        path: () => "/api/fix_unk_player/",
        query: ["max_to_update"],
        fields: [num("max_to_update", "Max", "1")],
      },
    ],
  },
  {
    title: "Backfill",
    blurb:
      "Incremental and idempotent — call repeatedly until the remaining count reaches zero.",
    tasks: [
      {
        id: "backfill_composition",
        title: "Compositions",
        description:
          "Compute and persist teams / humans vs CPUs / category for matches missing it.",
        method: "POST",
        path: () => "/api/backfill/composition",
        query: ["max_to_update"],
        fields: [num("max_to_update", "Max", "100")],
      },
      {
        id: "match_composition",
        title: "Composition for one match",
        description: "Recompute and persist the composition of a single match.",
        method: "POST",
        path: (v) => `/api/matches/${v.match_id}/composition`,
        fields: [num("match_id", "Match ID", "")],
      },
      {
        id: "backfill_player_roles",
        title: "Player roles",
        description:
          "Stamp match_players.role from stored replay JSON. Reads S3 only — no cncstats calls — so it is free to run in bulk.",
        method: "POST",
        path: () => "/api/backfill_player_roles/",
        query: ["max_to_update", "max_concurrent"],
        fields: [
          num("max_to_update", "Max", "100"),
          num("max_concurrent", "Concurrency", "16", 150),
        ],
      },
      {
        id: "backfill_tournament_games",
        title: "Tournament links",
        description:
          "Re-detect which matches belong to a scheduled bracket slot. Leaves admin-set (manual) links alone.",
        method: "POST",
        path: () => "/api/backfill/tournament_games",
      },
    ],
  },
  {
    title: "Maps",
    blurb:
      "Map geometry, CRCs, and the cncstats mirror. Pushing to cncstats needs CNCSTATS_API_KEY configured.",
    tasks: [
      {
        id: "backfill_map_crcs",
        title: "Backfill map CRCs",
        description:
          "Fill in MapData.crc from a sample match's replay, or from the hosted .map bytes for maps nobody has played.",
        method: "POST",
        path: () => "/api/backfill_map_crcs",
        query: ["max_to_update"],
        fields: [num("max_to_update", "Max", "50")],
      },
      {
        id: "reparse_maps",
        title: "Reparse map geometry",
        description:
          "Bring stored geometry up to date with the current mapparse binary, then fetch maps that have no MapData row at all.",
        method: "POST",
        path: () => "/api/reparse_maps",
        query: ["max_to_update"],
        fields: [num("max_to_update", "Max", "20")],
      },
      {
        id: "push_maps_to_cncstats",
        title: "Push maps to cncstats",
        description:
          "Register maps we host with cncstats /add_map. Skips anything already synced or already present there.",
        method: "POST",
        path: () => "/api/push_maps_to_cncstats",
        query: ["max_to_update"],
        fields: [num("max_to_update", "Max", "10")],
      },
      {
        id: "fetch_map_for_match",
        title: "Fetch map for match",
        description:
          "Fetch the cncstats map for one match's CRC, upload it to S3, and optionally parse its geometry.",
        method: "POST",
        path: (v) => `/api/fetch_map_for_match/${v.match_id}`,
        query: ["parse_map"],
        fields: [
          num("match_id", "Match ID", ""),
          {
            name: "parse_map",
            label: "Parse map",
            type: "text",
            defaultValue: "true",
            options: BOOL_OPTIONS,
            width: 130,
          },
        ],
      },
    ],
  },
  {
    title: "Recompute",
    blurb:
      "Rebuild derived tables. These run in the background and return as soon as they are queued; a second call while one is in flight gets a 409.",
    tasks: [
      {
        id: "superlatives_recompute",
        title: "Superlatives",
        description:
          "Recompute the records/superlatives tables. Also runs nightly at 04:00.",
        method: "POST",
        path: () => "/api/superlatives/recompute",
      },
      {
        id: "player_profile_recompute",
        title: "Player profiles",
        description: "Recompute every player's cached profile payload.",
        method: "POST",
        path: () => "/api/player_profile/recompute",
      },
      {
        id: "generate_tournament_report",
        title: "Tournament report",
        description:
          "Regenerate and store the round-robin tournament report for a slug.",
        method: "POST",
        path: (v) =>
          `/api/generate_tournament_report/${encodeURIComponent(v.tournament_name)}`,
        fields: [
          {
            name: "tournament_name",
            label: "Tournament",
            type: "text",
            defaultValue: "2025_2v2_tournament",
            width: 260,
          },
        ],
      },
    ],
  },
  {
    title: "Game night recaps",
    blurb:
      "The LLM-written half of the game-night page. Every night generated is a real, billed call, so the budget is a separate number from the search window, and nothing here is free to re-run. The deterministic recap needs none of this - it renders for every night already.",
    tasks: [
      {
        id: "backfill_game_night_summaries",
        title: "Backfill missing recaps",
        description:
          "Write recaps for the last N closed game nights that have none, newest first, spending at most Max calls per run. Never overwrites an existing one, and never touches the night still being played. The report lists every night considered with what was done about it, so one run also shows what the next one would spend.",
        method: "POST",
        path: () => "/api/backfill_game_night_summaries",
        query: ["days", "max_to_update"],
        fields: [
          num("days", "Days", "7"),
          num("max_to_update", "Max calls", "1", 150),
        ],
        confirmWord: () => "SPEND",
        confirmLabel: "spends money",
      },
      {
        id: "generate_game_night_summary",
        title: "Generate one night",
        description:
          "Write (or, with Overwrite, rewrite) a single night's recap. Unlike the backfill this does not require the night to be closed, so it can show what tonight would read like.",
        method: "POST",
        path: (v) => `/api/generate_game_night_summary/${v.night}`,
        query: ["force"],
        fields: [
          {
            name: "night",
            label: "Game night",
            type: "date",
            defaultValue: "",
            width: 170,
          },
          {
            name: "force",
            label: "Overwrite",
            type: "text",
            defaultValue: "false",
            options: BOOL_OPTIONS,
            width: 140,
          },
        ],
        confirmWord: (v) => v.night,
        confirmLabel: "spends money",
      },
    ],
  },
  {
    title: "Overrides and deletes",
    blurb:
      "These rewrite or destroy stored data. Each one stays disabled until you type its confirmation exactly.",
    tasks: [
      {
        id: "set_override",
        title: "Set winner override",
        description:
          "Force a match's winning team and/or incomplete reason. Takes precedence everywhere and survives reparses.",
        method: "POST",
        path: () => "/api/set_override/",
        query: ["match_id", "winner", "incomplete"],
        fields: [
          num("match_id", "Match ID", ""),
          {
            name: "winner",
            label: "Winning team",
            type: "text",
            defaultValue: "",
            options: TEAM_OPTIONS,
            width: 160,
            optional: true,
          },
          {
            name: "incomplete",
            label: "Incomplete reason",
            type: "text",
            defaultValue: "",
            width: 220,
            optional: true,
          },
        ],
        confirmWord: (v) => v.match_id,
      },
      {
        id: "delete_override",
        title: "Delete winner override",
        description:
          "Remove a match's override so its parsed result stands again.",
        method: "DELETE",
        path: (v) => `/api/override/${v.match_id}`,
        fields: [num("match_id", "Match ID", "")],
        confirmWord: (v) => v.match_id,
      },
      {
        id: "clear_details_cache",
        title: "Clear MatchDetails cache",
        description:
          "Drop every row of the durable match_details_cache table and invalidate the corpus. A debugging hatch — a details change should bump DETAILS_VERSION instead.",
        method: "POST",
        path: () => "/api/clear_details_cache/",
        confirmWord: () => "CLEAR",
      },
      {
        id: "reset_match",
        title: "Reset match",
        description:
          "Delete all parsed data for a match and set its ReplayFiles back to pending. The replay itself stays in S3, so a rescrape can rebuild it.",
        method: "DELETE",
        path: (v) => `/api/match/${v.match_id}`,
        fields: [num("match_id", "Match ID", "")],
        confirmWord: (v) => v.match_id,
      },
    ],
  },
]

function initialValues(task: AdminTask): Values {
  return Object.fromEntries(
    (task.fields ?? []).map((f) => [f.name, f.defaultValue]),
  )
}

// A field left blank is only acceptable when it is marked optional. Being a
// query param is NOT what makes one optional: /api/set_override/ takes its
// match_id in the query and still needs one, and firing without it would just
// 422 after the confirmation had been satisfied by an empty string.
function missingRequired(task: AdminTask, values: Values): boolean {
  return (task.fields ?? []).some(
    (f) => !f.optional && values[f.name].trim() === "",
  )
}

function TaskCard({ task }: { task: AdminTask }) {
  const [values, setValues] = React.useState<Values>(() => initialValues(task))
  const [confirmText, setConfirmText] = React.useState("")
  const [running, setRunning] = React.useState(false)
  const [result, setResult] = React.useState<unknown>(undefined)
  const [error, setError] = React.useState<string | null>(null)

  const expected = task.confirmWord?.(values).trim() ?? ""
  // `expected` is empty while the field it echoes is — an empty confirmation
  // must never count as typed, or the guard arms itself.
  const armed =
    task.confirmWord === undefined ||
    (expected !== "" && confirmText.trim() === expected)
  const incomplete = missingRequired(task, values)
  const disabled = running || incomplete || !armed

  const run = async () => {
    setRunning(true)
    setError(null)
    setResult(undefined)
    try {
      const query: QueryValues = Object.fromEntries(
        (task.query ?? []).map((name) => [name, values[name]]),
      )
      const body = await adminRequest<unknown>(
        task.path(values),
        task.method,
        query,
        task.title,
      )
      setResult(body ?? { ok: true })
      setConfirmText("")
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e))
    } finally {
      setRunning(false)
    }
  }

  return (
    <Paper variant="outlined" sx={{ p: 2 }}>
      <Stack spacing={1.5}>
        <Box>
          <Stack direction="row" spacing={1} sx={{ alignItems: "center" }}>
            <Typography variant="subtitle1" sx={{ fontWeight: 600 }}>
              {task.title}
            </Typography>
            {task.confirmWord && (
              <Chip
                size="small"
                color="warning"
                variant="outlined"
                icon={<WarningAmberIcon />}
                label={task.confirmLabel ?? "destructive"}
              />
            )}
          </Stack>
          <Typography variant="body2" color="text.secondary">
            {task.description}
          </Typography>
          <Typography
            variant="caption"
            color="text.disabled"
            sx={{ fontFamily: "monospace" }}
          >
            {task.method} {task.path(values)}
          </Typography>
        </Box>

        <Stack
          direction="row"
          spacing={1.5}
          sx={{ flexWrap: "wrap" }}
          useFlexGap
        >
          {(task.fields ?? []).map((field) => (
            <TextField
              key={field.name}
              select={field.options !== undefined}
              size="small"
              type={field.options ? "text" : field.type}
              label={field.label}
              value={values[field.name]}
              slotProps={
                field.type === "date"
                  ? { inputLabel: { shrink: true } }
                  : undefined
              }
              onChange={(e) =>
                setValues((prev) => ({ ...prev, [field.name]: e.target.value }))
              }
              sx={{ width: field.width ?? 130 }}
            >
              {field.options?.map((opt) => (
                <MenuItem key={opt.value} value={opt.value}>
                  {opt.label}
                </MenuItem>
              ))}
            </TextField>
          ))}

          {task.confirmWord && (
            <TextField
              size="small"
              color="warning"
              label={expected ? `Type ${expected}` : "Confirm"}
              value={confirmText}
              onChange={(e) => setConfirmText(e.target.value)}
              sx={{ width: 180 }}
            />
          )}

          <Button
            variant="contained"
            color={task.confirmWord ? "warning" : "primary"}
            disabled={disabled}
            onClick={() => void run()}
            startIcon={
              running ? (
                <CircularProgress size={16} color="inherit" />
              ) : (
                <PlayArrowIcon />
              )
            }
          >
            Run
          </Button>
        </Stack>

        {error && <Alert severity="error">{error}</Alert>}
        {result !== undefined && (
          <Box
            component="pre"
            sx={{
              m: 0,
              p: 1.5,
              maxHeight: 260,
              overflow: "auto",
              fontSize: 12,
              borderRadius: 1,
              bgcolor: "action.hover",
            }}
          >
            {JSON.stringify(result, null, 2)}
          </Box>
        )}
      </Stack>
    </Paper>
  )
}

// Shown to anyone who reaches ?page=admin-panel without the privilege. The
// routes 401/403 regardless — this just says so in words rather than as a wall
// of failed requests.
function NotAuthorized() {
  const { status, loading } = useAuth()
  if (loading) return null
  return (
    <Box sx={{ maxWidth: 560 }}>
      <Alert severity="warning" sx={{ mb: 2 }}>
        {status?.logged_in
          ? "Your account isn't an operations admin, so these tasks aren't available to you."
          : "Log in with Discord to check whether your account can run admin tasks."}
      </Alert>
      {!status?.logged_in && (
        <Button
          variant="contained"
          startIcon={<LoginIcon />}
          onClick={startDiscordLogin}
        >
          Login with Discord
        </Button>
      )}
    </Box>
  )
}

export default function AdminPanel() {
  const isOpsAdmin = useIsOpsAdmin()
  if (!isOpsAdmin) return <NotAuthorized />

  return (
    <Stack spacing={4} sx={{ maxWidth: 1100 }}>
      <Alert severity="info">
        Every task here runs against the live database. Batch sizes default to
        something small on purpose — the reparse tasks call cncstats once per
        match.
      </Alert>

      {SECTIONS.map((section) => (
        <Box key={section.title}>
          <Typography variant="h6">{section.title}</Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
            {section.blurb}
          </Typography>
          <Divider sx={{ mb: 2 }} />
          <Stack spacing={2}>
            {section.tasks.map((task) => (
              <TaskCard key={task.id} task={task} />
            ))}
          </Stack>
        </Box>
      ))}
    </Stack>
  )
}
