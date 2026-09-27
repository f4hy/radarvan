import { useQueryClient } from "@tanstack/react-query"
import * as React from "react"
import Alert from "@mui/material/Alert"
import Box from "@mui/material/Box"
import Button from "@mui/material/Button"
import Card from "@mui/material/Card"
import CardContent from "@mui/material/CardContent"
import MenuItem from "@mui/material/MenuItem"
import Stack from "@mui/material/Stack"
import TextField from "@mui/material/TextField"
import Typography from "@mui/material/Typography"
import LoginIcon from "@mui/icons-material/Login"
import LogoutIcon from "@mui/icons-material/Logout"
import { errorMessage } from "../../lib/apiError"
import { useAuth } from "../../lib/AuthContext"
import { logout, selectPlayer, startDiscordLogin } from "../../lib/auth"
import Loading from "../../components/Loading"
import Page from "../../components/Page"

// Cached reads carry the viewer's own state (their prediction picks, their
// votes, admin-only previews), so a change of identity drops them. The billed
// commentary queries are left alone: they don't depend on who is asking, and
// resetting one would ask the server for it again.
function useResetUserData(): () => Promise<void> {
  const queryClient = useQueryClient()
  return React.useCallback(
    () =>
      queryClient.resetQueries({
        predicate: (q) =>
          q.queryKey[0] !== "matchupCommentary" &&
          q.queryKey[0] !== "bracketSummary",
      }),
    [queryClient],
  )
}

// Center a single card; the account flows are all narrow.
function AccountCard({ children }: { children: React.ReactNode }) {
  return (
    <Box sx={{ display: "flex", justifyContent: "center", mt: 2 }}>
      <Card sx={{ maxWidth: 420, width: "100%" }}>
        <CardContent>{children}</CardContent>
      </Card>
    </Box>
  )
}

function LoginPrompt() {
  return (
    <AccountCard>
      <Stack
        spacing={2}
        sx={{
          alignItems: "center",
        }}
      >
        <Typography variant="h6">Sign in</Typography>
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
            textAlign: "center",
          }}
        >
          Log in with Discord to vote for and veto maps.
        </Typography>
        <Button
          variant="contained"
          startIcon={<LoginIcon />}
          onClick={startDiscordLogin}
        >
          Sign in with Discord
        </Button>
      </Stack>
    </AccountCard>
  )
}

function PlayerSelection({ players }: { players: string[] }) {
  const { setStatus } = useAuth()
  const resetUserData = useResetUserData()
  const [name, setName] = React.useState("")
  const [error, setError] = React.useState<string | null>(null)
  const [saving, setSaving] = React.useState(false)

  const handleConfirm = async () => {
    if (!name) return
    setSaving(true)
    setError(null)
    try {
      // The POST already returns the updated status — apply it directly.
      setStatus(await selectPlayer(name))
      await resetUserData()
    } catch (e) {
      setError(await errorMessage(e))
    } finally {
      setSaving(false)
    }
  }

  return (
    <AccountCard>
      <Stack spacing={2}>
        <Typography variant="h6">Which player are you?</Typography>
        <Typography
          variant="body2"
          sx={{
            color: "text.secondary",
          }}
        >
          Pick your in-game name so we can tie your votes to your stats. This is
          a one-time choice.
        </Typography>
        <TextField
          select
          label="In-game name"
          value={name}
          onChange={(e) => setName(e.target.value)}
        >
          {players.map((p) => (
            <MenuItem key={p} value={p}>
              {p}
            </MenuItem>
          ))}
        </TextField>
        {error && <Alert severity="error">{error}</Alert>}
        <Button
          variant="contained"
          disabled={!name || saving}
          onClick={handleConfirm}
        >
          Confirm
        </Button>
      </Stack>
    </AccountCard>
  )
}

function Profile({
  username,
  playerName,
}: {
  username: string
  playerName: string
}) {
  const { refresh } = useAuth()
  const resetUserData = useResetUserData()
  const [error, setError] = React.useState<string | null>(null)
  const handleLogout = async () => {
    setError(null)
    try {
      await logout()
    } catch (e) {
      setError(await errorMessage(e))
      return
    }
    await refresh()
    await resetUserData()
  }
  return (
    <AccountCard>
      <Stack spacing={2}>
        <Typography variant="h6">Signed in</Typography>
        <Typography variant="body2">
          Discord: <strong>{username}</strong>
        </Typography>
        <Typography variant="body2">
          Playing as: <strong>{playerName}</strong>
        </Typography>
        {error && <Alert severity="error">{error}</Alert>}
        <Button
          variant="outlined"
          startIcon={<LogoutIcon />}
          onClick={handleLogout}
        >
          Log out
        </Button>
      </Stack>
    </AccountCard>
  )
}

export default function Account() {
  const { status, loading } = useAuth()

  const body = () => {
    if (loading || status === null) return <Loading />
    if (!status.loggedIn || !status.user) return <LoginPrompt />
    if (status.user.needsPlayerSelection) {
      return <PlayerSelection players={status.availablePlayers ?? []} />
    }
    return (
      <Profile
        username={status.user.discordUsername}
        playerName={status.user.playerName ?? ""}
      />
    )
  }

  return (
    <Page
      surface={false}
      width="narrow"
      title="Account"
      description="Sign in with Discord and tell us which in-game name is yours, so your votes count toward your stats."
    >
      {body()}
    </Page>
  )
}
