import * as React from "react"
import Page from "./Page"
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
            <Typography variant="subtitle2" noWrap title={m.base_name}>
              {m.base_name}
            </Typography>
            <Stack
              direction="row"
              spacing={1}
              sx={{
                flexWrap: "wrap",
              }}
            >
              {m.player_count != null && (
                <Chip size="small" label={`${m.player_count} players`} />
              )}
              {m.already_exists && (
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

export default function MapUpload() {
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

  const isAdmin = status?.user?.is_admin ?? false
  const savedCount = result?.maps.filter((m) => m.saved).length ?? 0

  if (!status?.logged_in) {
    return (
      <Page
        surface={false}
        width="narrow"
        title="Upload Map"
        description="Add a map to the pool so it shows up in voting, the draw and map stats."
      >
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
      </Page>
    )
  }

  return (
    <Page
      surface={false}
      width="narrow"
      title="Upload Map"
      description={
        <>
          Upload a <strong>.tga</strong> + <strong>.map</strong> pair, or a{" "}
          <strong>.zip</strong> of folders that each contain a .map and a .tga
          (other files ignored). You&apos;ll see a preview before anything is
          saved.
        </>
      }
    >
      <Stack spacing={2}>
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
          {result && !result.committed && result.maps.length > 0 && (
            <Button
              variant="contained"
              color="success"
              startIcon={<SaveIcon />}
              disabled={busy}
              onClick={() => run(true)}
            >
              Save {result.maps.length} map
              {result.maps.length === 1 ? "" : "s"}
            </Button>
          )}
        </Stack>
        {error && <Alert severity="error">{error}</Alert>}
        {result?.committed && (
          <Alert severity={savedCount > 0 ? "success" : "warning"}>
            Saved {savedCount} map{savedCount === 1 ? "" : "s"}.
          </Alert>
        )}
        {result?.errors.map((e, i) => (
          <Alert key={i} severity="warning">
            {e}
          </Alert>
        ))}
        {result && result.maps.length === 0 && !result.errors.length && (
          <Alert severity="warning">No valid maps found in the upload.</Alert>
        )}
        {result && result.maps.length > 0 && (
          <PreviewGrid result={result} isAdmin={isAdmin} />
        )}
      </Stack>
    </Page>
  )
}
