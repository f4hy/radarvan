import * as React from "react"
import Alert from "@mui/material/Alert"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Chip from "@mui/material/Chip"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import ToggleButton from "@mui/material/ToggleButton"
import ToggleButtonGroup from "@mui/material/ToggleButtonGroup"
import Typography from "@mui/material/Typography"
import LoginIcon from "@mui/icons-material/Login"
import UploadFileIcon from "@mui/icons-material/UploadFile"
import SaveIcon from "@mui/icons-material/Save"
import { useAuth } from "./AuthContext"
import { startDiscordLogin } from "./auth"
import { MapUploadFiles, MapUploadResponse, uploadMaps } from "./mapUpload"

type Mode = "files" | "zip"

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

function PreviewGrid({ result }: { result: MapUploadResponse }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fill, minmax(260px, 1fr))",
        gap: 2,
      }}
    >
      {result.maps.map((m) => (
        <Paper key={m.base_name} variant="outlined" sx={{ p: 1 }}>
          <Stack spacing={1}>
            {m.image ? (
              <Box
                component="img"
                src={m.image}
                alt={m.base_name}
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
                <Typography variant="body2" color="text.secondary">
                  saved ✓
                </Typography>
              </Box>
            )}
            <Typography variant="subtitle2" noWrap title={m.base_name}>
              {m.base_name}
            </Typography>
            <Stack direction="row" spacing={1} flexWrap="wrap">
              {m.player_count != null && (
                <Chip size="small" label={`${m.player_count} players`} />
              )}
              {m.already_exists && (
                <Chip
                  size="small"
                  color="warning"
                  variant="outlined"
                  label="already exists — will overwrite"
                />
              )}
            </Stack>
          </Stack>
        </Paper>
      ))}
    </Box>
  )
}

export default function MapUpload() {
  const { status, loading: authLoading } = useAuth()
  const [mode, setMode] = React.useState<Mode>("files")
  const [tga, setTga] = React.useState<File | null>(null)
  const [map, setMap] = React.useState<File | null>(null)
  const [zip, setZip] = React.useState<File | null>(null)
  const [preview, setPreview] = React.useState<MapUploadResponse | null>(null)
  const [saved, setSaved] = React.useState<MapUploadResponse | null>(null)
  const [busy, setBusy] = React.useState(false)
  const [error, setError] = React.useState<string | null>(null)

  const currentFiles = (): MapUploadFiles =>
    mode === "zip"
      ? { zip: zip ?? undefined }
      : { tga: tga ?? undefined, map: map ?? undefined }

  const ready = mode === "zip" ? zip !== null : tga !== null && map !== null

  const resetResults = () => {
    setPreview(null)
    setSaved(null)
    setError(null)
  }

  const doPreview = async () => {
    setBusy(true)
    resetResults()
    try {
      setPreview(await uploadMaps(currentFiles(), false))
    } catch (e) {
      setError(e instanceof Error ? e.message : "Preview failed")
    } finally {
      setBusy(false)
    }
  }

  const doSave = async () => {
    setBusy(true)
    setError(null)
    try {
      const result = await uploadMaps(currentFiles(), true)
      setSaved(result)
      setPreview(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : "Save failed")
    } finally {
      setBusy(false)
    }
  }

  if (authLoading) {
    return null
  }

  if (!status?.logged_in) {
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
      <Typography variant="h6">Upload a map</Typography>
      <Typography variant="body2" color="text.secondary">
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
          if (next) {
            setMode(next)
            resetResults()
          }
        }}
      >
        <ToggleButton value="files">.tga + .map</ToggleButton>
        <ToggleButton value="zip">.zip of folders</ToggleButton>
      </ToggleButtonGroup>

      <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
        {mode === "files" ? (
          <>
            <FilePicker
              label="Choose .tga"
              accept=".tga"
              file={tga}
              onPick={(f) => {
                setTga(f)
                resetResults()
              }}
            />
            <FilePicker
              label="Choose .map"
              accept=".map"
              file={map}
              onPick={(f) => {
                setMap(f)
                resetResults()
              }}
            />
          </>
        ) : (
          <FilePicker
            label="Choose .zip"
            accept=".zip"
            file={zip}
            onPick={(f) => {
              setZip(f)
              resetResults()
            }}
          />
        )}
      </Stack>

      <Stack direction="row" spacing={1}>
        <Button
          variant="contained"
          startIcon={<UploadFileIcon />}
          disabled={!ready || busy}
          onClick={doPreview}
        >
          Preview
        </Button>
        {preview && preview.maps.length > 0 && (
          <Button
            variant="contained"
            color="success"
            startIcon={<SaveIcon />}
            disabled={busy}
            onClick={doSave}
          >
            Save {preview.maps.length} map
            {preview.maps.length === 1 ? "" : "s"}
          </Button>
        )}
      </Stack>

      {error && <Alert severity="error">{error}</Alert>}

      {saved && (
        <Alert severity="success">
          Saved {saved.maps.length} map{saved.maps.length === 1 ? "" : "s"}.
        </Alert>
      )}

      {preview?.errors.map((e, i) => (
        <Alert key={i} severity="warning">
          {e}
        </Alert>
      ))}

      {preview && preview.maps.length === 0 && !preview.errors.length && (
        <Alert severity="warning">No valid maps found in the upload.</Alert>
      )}

      {preview && preview.maps.length > 0 && <PreviewGrid result={preview} />}
    </Stack>
  )
}
