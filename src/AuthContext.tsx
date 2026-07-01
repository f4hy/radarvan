import * as React from "react"
import { AuthStatus, fetchAuthStatus } from "./auth"

interface AuthContextValue {
  status: AuthStatus | null
  loading: boolean
  // Re-fetch /api/auth/me (call after login/logout).
  refresh: () => Promise<void>
  // Apply an AuthStatus a mutation already returned, avoiding a redundant GET.
  setStatus: (status: AuthStatus) => void
}

const AuthContext = React.createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [status, setStatus] = React.useState<AuthStatus | null>(null)
  const [loading, setLoading] = React.useState(true)

  const refresh = React.useCallback(async () => {
    setLoading(true)
    try {
      setStatus(await fetchAuthStatus())
    } finally {
      setLoading(false)
    }
  }, [])

  React.useEffect(() => {
    void refresh()
  }, [refresh])

  const value = React.useMemo(
    () => ({ status, loading, refresh, setStatus }),
    [status, loading, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = React.useContext(AuthContext)
  if (ctx === undefined) {
    throw new Error("useAuth must be used within an AuthProvider")
  }
  return ctx
}

// True if the logged-in user is an admin (player_ids.ADMIN_PLAYERS). Also gates
// what used to be the ?debug=True views.
export function useIsAdmin(): boolean {
  return useAuth().status?.user?.is_admin ?? false
}

// True if the logged-in user can administer the 1v1 bracket tournament
// (player_ids.TOURNAMENT_ADMINS) — a separate, narrower set from useIsAdmin.
export function useIsTournamentAdmin(): boolean {
  return useAuth().status?.user?.is_tournament_admin ?? false
}
