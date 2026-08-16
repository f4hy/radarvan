// The bracket page (and its nav tab, see Menu.tsx) is open to everyone,
// including logged-out visitors — the reveal_at gate on individual
// placements (see routes/bracket.py) is what keeps the tournament a secret
// pre-reveal, not this flag. Flip PRODUCTION_BRACKET_VISIBLE_TO_ALL back to
// false to lock the whole page down to tournament admins again (e.g. before
// a future tournament is ready to announce at all).
//
// This lives in its own module rather than in Bracket.tsx because Menu.tsx
// reads it at module scope to decide whether to show the nav tab: importing it
// from Bracket.tsx would pull that (large, chart-heavy) module into the initial
// bundle and defeat the React.lazy split.
const PRODUCTION_BRACKET_VISIBLE_TO_ALL = true

export const BRACKET_VISIBLE_TO_ALL =
  PRODUCTION_BRACKET_VISIBLE_TO_ALL ||
  import.meta.env.VITE_BRACKET_VISIBLE_TO_ALL === "true"
