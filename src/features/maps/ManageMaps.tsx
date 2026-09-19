import DownloadIcon from "@mui/icons-material/Download"
import LoginIcon from "@mui/icons-material/Login"
import SaveIcon from "@mui/icons-material/Save"
import UploadFileIcon from "@mui/icons-material/UploadFile"
import Alert from "@mui/material/Alert"
import Autocomplete from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import CircularProgress from "@mui/material/CircularProgress"
import Divider from "@mui/material/Divider"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import TextField from "@mui/material/TextField"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Typography from "@mui/material/Typography"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import GameMap from "../../components/Map"
import Page from "../../components/Page"
import { useAuth } from "../../lib/AuthContext"
import { startDiscordLogin } from "../../lib/auth"
import { useUrlParam } from "../../lib/useUrlState"
import { displayMapName } from "../../lib/utils"
import { downloadMapFile, fetchMapOptions, type MapOption } from "./mapDownload"
import {
  type MapUploadFiles,
  type MapUploadResponse,
  uploadMaps,
} from "./mapUpload"

type Mode = "files" | "zip"

// --- Search / view / download ---

function MapSearch() {
  const [mapName, setMapName] = useUrlParam("map")
  const [downloading, setDownloading] = React.useState(false)
  const [downloadError, setDownloadError] = React.useState<string | null>(null)

  const { data: options = [], isLoading } = useQuery({
    queryKey: ["mapOptions"],
    queryFn: fetchMapOptions,
  })

  const selected = options.find((o) => o.name === mapName) ?? null

  const handleDownload = async () => {
    if (!mapName) return
    setDownloading(true)
    setDownloadError(null)
    try {
      await downloadMapFile(mapName)
    } catch (e) {
      setDownloadError(e instanceof Error ? e.message : "Download failed")
    } finally {
      setDownloading(false)
    }
  }

  return (
    <Stack spacing={2}>
      <Autocomplete
        options={options}
        value={selected}
        loading={isLoading}
        getOptionLabel={(o: MapOption) => displayMapName(o.name)}
        isOptionEqualToValue={(o, v) => o.name === v.name}
        onChange={(_, next) => setMapName(next?.name ?? null)}
        size="small"
        sx={{ maxWidth: 360 }}
        renderInput={(params) => <TextField {...params} label="Search maps" />}
      />
      {mapName && (
        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={1.5}>
            <Stack
              direction="row"
              spacing={1}
              sx={{ alignItems: "center", flexWrap: "wrap" }}
            >
              <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>
                {displayMapName(mapName)}
              </Typography>
              {selected && (
                <Chip size="small" label={`${selected.playerCount} players`} />
              )}
              <Button
                size="small"
                variant="outlined"
                startIcon={
                  downloading ? (
                    <CircularProgress size={16} />
                  ) : (
                    <DownloadIcon />
                  )
                }
                disabled={downloading}
                onClick={handleDownload}
              >
                Download .map
              </Button>
            </Stack>
            {downloadError && <Alert severity="error">{downloadError}</Alert>}
            <Box sx={{ maxWidth: 460 }}>
              <GameMap mapname={mapName} />
            </Box>
          </Stack>
        </Paper>
      )}
    </Stack>
  )
}

// --- Upload ---

// A button that opens a file picker and reports the chosen file.
function FilePicker({
  label,
  accept,
  file,
  onPick,
}: {
  label: string
  accept: string
  file: File | null
  onPick: (f: File | null) => void
}) {
  return (
    <Button
      variant="outlined"
      component="label"
      sx={{ justifyContent: "start" }}
    >
      {file ? `${label}: ${file.name}` : label}
      <input
        type="file"
        accept={accept}
        hidden
        onChange={(e) => onPick(e.target.files?.[0] ?? null)}
      />
    </Button>
  )
}

function PreviewGrid({
  result,
  isAdmin,
}: {
  result: MapUploadResponse
  isAdmin: boolean
}) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
        gap: 2,
      }}
    >
      {(result.maps ?? []).map((m) => (
        <Paper key={m.baseName} variant="outlined" sx={{ p: 1 }}>
          <Stack spacing={1}>
            {m.image ? (
              <Box
                component="img"
                src={m.image}
                alt={m.baseName}
                sx={{ width: "100%", height: "auto", borderRadius: 1 }}
              />
            ) : (
              <Box
                sx={{
                  height: 160,
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  bgcolor: "action.hover",
                  borderRadius: 1,
                }}
              >
                <Typography
                  variant="body2"
                  sx={{
                    color: "text.secondary",
                  }}
                >
                  saved ✓
                </Typography>
              </Box>
            )}
            <Typography variant="subtitle2" noWrap title={m.baseName}>
              {m.baseName}
            </Typography>
            <Stack
              direction="row"
              spacing={1}
              sx={{
                flexWrap: "wrap",
              }}
            >
              {m.playerCount != null && (
                <Chip size="small" label={`${m.playerCount} players`} />
              )}
              {m.alreadyExists && (
                <Chip
                  size="small"
                  color="warning"
                  variant="outlined"
                  label={
                    isAdmin
                      ? "already exists — will overwrite"
                      : "already exists — needs admin to overwrite"
                  }
                />
              )}
            </Stack>
          </Stack>
        </Paper>
      ))}
    </Box>
  )
}

function MapUploadSection() {
  const { status, loading: authLoading } = useAuth()
  const [mode, setMode] = React.useState<Mode>("files")
  const [tga, setTga] = React.useState<File | null>(null)
  const [map, setMap] = React.useState<File | null>(null)
  const [zip, setZip] = React.useState<File | null>(null)
  // One result for both phases; `committed` distinguishes preview from save.
  const [result, setResult] = React.useState<MapUploadResponse | null>(null)
  const [busy, setBusy] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const currentFiles = (): MapUploadFiles =>
    mode === "zip"
      ? { zip: zip ?? undefined }
      : { tga: tga ?? undefined, map: map ?? undefined }

  const ready = mode === "zip" ? zip !== null : tga !== null && map !== null

  // Any input change invalidates the prior preview/save result.
  React.useEffect(() => {
    setResult(null)
    setError(null)
  }, [tga, map, zip, mode])

  const run = async (commit: boolean) => {
    setBusy(true)
    setError(null)
    try {
      setResult(await uploadMaps(currentFiles(), commit))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Upload failed")
    } finally {
      setBusy(false)
    }
  }

  if (authLoading) {
    return null
  }

  const isAdmin = status?.user?.isAdmin ?? false
  const savedCount = (result?.maps ?? []).filter((m) => m.saved).length

  if (!status?.loggedIn) {
    return (
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
        Log in with Discord to upload maps.
      </Alert>
    )
  }

  return (
    <Stack spacing={2}>
      <Typography variant="subtitle1" sx={{ fontWeight: "bold" }}>
        Upload a map
      </Typography>
      <Typography variant="body2" sx={{ color: "text.secondary" }}>
        Upload a <strong>.tga</strong> + <strong>.map</strong> pair, or a{" "}
        <strong>.zip</strong> of folders that each contain a .map and a .tga
        (other files ignored). You&apos;ll see a preview before anything is
        saved.
      </Typography>
      <ToggleButtonGroup
        exclusive
        size="small"
        value={mode}
        onChange={(_, next: Mode | null) => {
          if (next) setMode(next)
        }}
      >
        <ToggleButton value="files">.tga + .map</ToggleButton>
        <ToggleButton value="zip">.zip of folders</ToggleButton>
      </ToggleButtonGroup>
      <Stack
        direction="row"
        spacing={1}
        useFlexGap
        sx={{
          flexWrap: "wrap",
        }}
      >
        {mode === "files" ? (
          <>
            <FilePicker
              label="Choose .tga"
              accept=".tga"
              file={tga}
              onPick={setTga}
            />
            <FilePicker
              label="Choose .map"
              accept=".map"
              file={map}
              onPick={setMap}
            />
          </>
        ) : (
          <FilePicker
            label="Choose .zip"
            accept=".zip"
            file={zip}
            onPick={setZip}
          />
        )}
      </Stack>
      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          startIcon={<UploadFileIcon />}
          disabled={!ready || busy}
          onClick={() => run(false)}
        >
          Preview
        </Button>
        {result && !result.committed && (result.maps ?? []).length > 0 && (
          <Button
            variant="contained"
            color="success"
            startIcon={<SaveIcon />}
            disabled={busy}
            onClick={() => run(true)}
          >
            Save {(result.maps ?? []).length} map
            {(result.maps ?? []).length === 1 ? "" : "s"}
          </Button>
        )}
      </Stack>
      {error && <Alert severity="error">{error}</Alert>}
      {result?.committed && (
        <Alert severity={savedCount > 0 ? "success" : "warning"}>
          Saved {savedCount} map{savedCount === 1 ? "" : "s"}.
        </Alert>
      )}
      {(result?.errors ?? []).map((e) => (
        <Alert key={e} severity="warning">
          {e}
        </Alert>
      ))}
      {result &&
        (result.maps ?? []).length === 0 &&
        !(result.errors ?? []).length && (
          <Alert severity="warning">No valid maps found in the upload.</Alert>
        )}
      {result && (result.maps ?? []).length > 0 && (
        <PreviewGrid result={result} isAdmin={isAdmin} />
      )}
    </Stack>
  )
}

export default function ManageMaps() {
  return (
    <Page
      surface={false}
      title="Manage Maps"
      description="Search the map pool to view and download a map's .map file, or upload a new one to add it."
    >
      <Stack spacing={3}>
        <MapSearch />
        <Divider />
        <MapUploadSection />
      </Stack>
    </Page>
  )
}
