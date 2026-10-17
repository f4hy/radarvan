// Cookie-based auth helpers.
//
// These go through the generated client like everything else, typed by the
// generated `AuthStatus`/`CurrentUser` rather than hand-written copies.

import {
  logoutApiAuthLogoutPost,
  meApiAuthMeGet,
  selectPlayerApiAuthSelectPlayerPost,
} from "../api/sdk.gen"
import type { AuthStatus, CurrentUser } from "../api/types.gen"

export type { AuthStatus, CurrentUser }

const LOGGED_OUT: AuthStatus = {
  logged_in: false,
  user: null,
  available_players: [],
}

export async function fetchAuthStatus(): Promise<AuthStatus> {
  // Not-logged-in is an ordinary state, not an error: any failure to read the
  // session (401, a network blip) reads as logged out rather than throwing
  // into AuthProvider, which has no error branch and gates the whole nav.
  try {
    return (await meApiAuthMeGet()).data
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
  const { data } = await selectPlayerApiAuthSelectPlayerPost({
    body: { player_name: playerName },
  })
  return data
}

export async function logout(): Promise<void> {
  await logoutApiAuthLogoutPost()
}
