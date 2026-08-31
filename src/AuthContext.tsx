import * as React from "react"
import { type AuthStatus, fetchAuthStatus } from "./auth"

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
// the debug views.
export function useIsAdmin(): boolean {
  return useAuth().status?.user?.isAdmin ?? false
}

// True if the logged-in user can administer the 1v1 bracket tournament
// (player_ids.TOURNAMENT_ADMINS) — a separate, narrower set from useIsAdmin.
export function useIsTournamentAdmin(): boolean {
  return useAuth().status?.user?.isTournamentAdmin ?? false
}

// True if the logged-in user can run the operational admin tasks behind the
// Admin panel (player_ids.OPS_ADMINS) — narrower again than useIsAdmin, which
// only unlocks the debug views. The backend gates every one of those routes on
// the same set, so this is presentation only, not the security boundary.
export function useIsOpsAdmin(): boolean {
  return useAuth().status?.user?.isOpsAdmin ?? false
}
