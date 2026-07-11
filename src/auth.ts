// Cookie-based auth helpers.
//
// These talk to /api/auth/* with the session cookie, deliberately *separate*
// from the generated API-key client in Client.ts. We use relative URLs so the
// requests stay same-origin (dev: through the Vite proxy; prod: same host),
// which is what lets the signed session cookie ride along.

export interface CurrentUser {
  discord_id: string
  discord_username: string
  discord_avatar: string | null
  player_name: string | null
  needs_player_selection: boolean
  is_admin: boolean
  is_tournament_admin: boolean
}

export interface AuthStatus {
  logged_in: boolean
  user: CurrentUser | null
  available_players: string[]
}

const LOGGED_OUT: AuthStatus = {
  logged_in: false,
  user: null,
  available_players: [],
}

export async function fetchAuthStatus(): Promise<AuthStatus> {
  const resp = await fetch("/api/auth/me", { credentials: "same-origin" })
  if (!resp.ok) {
    return LOGGED_OUT
  }
  return (await resp.json()) as AuthStatus
}

// Full-page navigation that hands the browser to Discord's consent screen.
export function startDiscordLogin(): void {
  window.location.href = "/api/auth/discord/login"
}

export async function selectPlayer(playerName: string): Promise<AuthStatus> {
  const resp = await fetch("/api/auth/select_player", {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ player_name: playerName }),
  })
  if (!resp.ok) {
    const detail = await resp.text()
    throw new Error(detail || `select_player failed (${resp.status})`)
  }
  return (await resp.json()) as AuthStatus
}

export async function logout(): Promise<void> {
  await fetch("/api/auth/logout", {
    method: "POST",
    credentials: "same-origin",
  })
}
