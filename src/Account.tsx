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
import { useAuth } from "./AuthContext"
import { logout, selectPlayer, startDiscordLogin } from "./auth"
import Loading from "./Loading"
import Page from "./Page"

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
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save")
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
  const handleLogout = async () => {
    await logout()
    await refresh()
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
    if (!status.logged_in || status.user === null) return <LoginPrompt />
    if (status.user.needs_player_selection) {
      return <PlayerSelection players={status.available_players} />
    }
    return (
      <Profile
        username={status.user.discord_username}
        playerName={status.user.player_name ?? ""}
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
