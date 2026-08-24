import Box from "@mui/material/Box"
import Paper from "@mui/material/Paper"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import * as React from "react"

/**
 * The one page shell.
 *
 * Before this, every page invented its own: titles ran h4 / h5 / h6 or were
 * missing entirely, containers were `Paper p:2`, a `Paper` with no padding at
 * all (Balance Teams and Tournaments both had content flush to the card edge),
 * a bare `Stack`, or a `Box maxWidth:900` — and several set `maxWidth: 2000`,
 * which does nothing because Menu already caps the content column at 1700.
 *
 * `description` is not optional-by-habit: the three pages that had one (Game
 * Length, Map Stats, Team Stats) are the three that read clearly to someone who
 * didn't build them. A stats page that can't say in a sentence what it counts
 * and what it excludes is hiding that from the reader.
 */

// `narrow` is for form-shaped pages (a picker and a result) where the full
// column just spreads two controls apart; the default inherits Menu's cap.
const NARROW_WIDTH = 960

type PageWidth = "default" | "narrow"

function PageHeader(props: {
  title: string
  description?: React.ReactNode
  /** Filters, toggles or actions — sits under the description, above content. */
  actions?: React.ReactNode
}) {
  return (
    <Box sx={{ mb: 2 }}>
      <Typography variant="h5" component="h1">
        {props.title}
      </Typography>
      {props.description && (
        <Typography
          variant="body2"
          sx={{ color: "text.secondary", mt: 0.5, maxWidth: "80ch" }}
        >
          {props.description}
        </Typography>
      )}
      {props.actions && (
        <Stack
          direction="row"
          spacing={1.5}
          useFlexGap
          sx={{ flexWrap: "wrap", alignItems: "center", mt: 1.5 }}
        >
          {props.actions}
        </Stack>
      )}
    </Box>
  )
}

export default function Page(props: {
  title: string
  description?: React.ReactNode
  actions?: React.ReactNode
  width?: PageWidth
  /**
   * False puts the content straight on the page canvas so it can compose its
   * own cards (Game Length, Game Night, Map Voting work this way). True — the
   * default — wraps it in the single white surface most pages still use.
   */
  surface?: boolean
  children: React.ReactNode
}) {
  const maxWidth = props.width === "narrow" ? NARROW_WIDTH : undefined
  // A surface-less page sits straight on the canvas so it can compose its own
  // cards; otherwise it gets the single white surface most pages still use.
  const bare = props.surface === false
  const Surface = bare ? Box : Paper
  return (
    <Surface sx={{ maxWidth, ...(bare ? {} : { p: { xs: 1.5, sm: 2 } }) }}>
      <PageHeader
        title={props.title}
        description={props.description}
        actions={props.actions}
      />
      {props.children}
    </Surface>
  )
}
