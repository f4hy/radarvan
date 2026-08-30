// Cookie-based auth helpers.
//
// These go through the generated client like everything else. The types are
// the generated `AuthStatus`/`CurrentUser` (camelCase, regenerated from the
// backend's own models) rather than the hand-written snake_case copies that
// used to live here — those could drift from the API with nothing to catch it,
// and they were the reason the app spelled the same object two ways.

import { AuthClient } from "./clients/auth"
import type { AuthStatus, CurrentUser } from "./api"

export type { AuthStatus, CurrentUser }

const LOGGED_OUT: AuthStatus = {
  loggedIn: false,
  user: null,
  availablePlayers: [],
}

export async function fetchAuthStatus(): Promise<AuthStatus> {
  // Not-logged-in is an ordinary state, not an error: any failure to read the
  // session (401, a network blip) reads as logged out rather than throwing
  // into AuthProvider, which has no error branch and gates the whole nav.
  try {
    return await AuthClient.meApiAuthMeGet()
  } catch {
    return LOGGED_OUT
  }
}

// Full-page navigation that hands the browser to Discord's consent screen.
// Deliberately not the generated `discordLoginApiAuthDiscordLoginGet`: this has
// to be a top-level navigation so Discord can render its own page and redirect
// back, not an XHR that follows the redirect in the background.
export function startDiscordLogin(): void {
  window.location.href = "/api/auth/discord/login"
}

export async function selectPlayer(playerName: string): Promise<AuthStatus> {
  return AuthClient.selectPlayerApiAuthSelectPlayerPost({
    selectPlayerRequest: { playerName },
  })
}

export async function logout(): Promise<void> {
  await AuthClient.logoutApiAuthLogoutPost()
}
