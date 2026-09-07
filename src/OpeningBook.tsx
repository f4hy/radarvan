import ExpandMoreIcon from "@mui/icons-material/ExpandMore"
import Accordion from "@mui/material/Accordion"
import AccordionDetails from "@mui/material/AccordionDetails"
import AccordionSummary from "@mui/material/AccordionSummary"
import Alert from "@mui/material/Alert"
import Box from "@mui/material/Box"
import List from "@mui/material/List"
import ListItem from "@mui/material/ListItem"
import Stack from "@mui/material/Stack"
import Typography from "@mui/material/Typography"
import { useQuery } from "@tanstack/react-query"
import type { GeneralOpeningBook } from "./api"
import { OpeningBookClient } from "./clients/openingBook"
import DisplayGeneral from "./Generals"
import Page from "./Page"
import { queryFallback } from "./QueryState"
import WinRateChip, { WinLossVolumeBar } from "./WinRateChip"

// Fixed-width columns so every row's count/bar/chip lines up regardless of
// how long its label is - sized to fit the longest real 5-building sequence
// in this corpus (e.g. "PowerPlant → Barracks → SupplyCenter → GattlingCannon
// → WarFactory") without ellipsizing it.
const LABEL_WIDTH = "0 1 39rem"
const COUNT_WIDTH = "0 0 3.5rem"
const BAR_SX = { flex: "1 1 auto", minWidth: 60, maxWidth: 180 } as const

/** One row: a label (a building sequence, or "Other"), how popular it is
 * against this general's own busiest opening, and how it's fared. */
function BuildOrderRow(props: {
  label: string
  monospace?: boolean
  gameCount: number
  winCount: number
  max: number
}) {
  const { gameCount, winCount } = props
  return (
    <ListItem disableGutters dense sx={{ gap: 1.5 }}>
      <Typography
        variant="body2"
        sx={{
          fontFamily: props.monospace ? "monospace" : undefined,
          color: props.monospace ? undefined : "text.secondary",
          flex: LABEL_WIDTH,
          minWidth: 0,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {props.label}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          color: "text.secondary",
          flex: COUNT_WIDTH,
          textAlign: "right",
          fontVariantNumeric: "tabular-nums",
        }}
      >
        {gameCount}
      </Typography>
      <Box sx={BAR_SX}>
        <WinLossVolumeBar
          wins={winCount}
          losses={gameCount - winCount}
          max={props.max}
        />
      </Box>
      <Box sx={{ flexShrink: 0 }}>
        <WinRateChip wins={winCount} losses={gameCount - winCount} />
      </Box>
    </ListItem>
  )
}

function GeneralSection(props: {
  book: GeneralOpeningBook
  defaultExpanded: boolean
}) {
  const { book } = props
  const max = Math.max(1, ...book.openings.map((o) => o.gameCount))
  return (
    <Accordion defaultExpanded={props.defaultExpanded} disableGutters>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack
          direction="row"
          spacing={2}
          sx={{ alignItems: "center", flexWrap: "wrap", width: "100%" }}
          useFlexGap
        >
          <DisplayGeneral general={book.general} />
          <Typography variant="body2" sx={{ color: "text.secondary" }}>
            {book.totalGames} game{book.totalGames === 1 ? "" : "s"} ·{" "}
            {book.openings.length} named opening
            {book.openings.length === 1 ? "" : "s"}
          </Typography>
        </Stack>
      </AccordionSummary>
      <AccordionDetails sx={{ pt: 0 }}>
        <List dense disablePadding>
          {book.openings.map((opening) => (
            <BuildOrderRow
              key={opening.buildings.join("|")}
              label={opening.buildings.join(" → ")}
              monospace
              gameCount={opening.gameCount}
              winCount={opening.winCount}
              max={max}
            />
          ))}
          {book.otherGameCount > 0 && (
            <BuildOrderRow
              label="Other (one-off builds)"
              gameCount={book.otherGameCount}
              winCount={book.otherWinCount}
              max={max}
            />
          )}
        </List>
      </AccordionDetails>
    </Accordion>
  )
}

export default function OpeningBookPage() {
  const query = useQuery({
    queryKey: ["openingBook"],
    queryFn: () => OpeningBookClient.getOpeningBookApiOpeningBookGet(),
  })
  const book = query.data

  return (
    <Page
      title="Build Orders"
      description={`Chess-site framing for build orders: each general's first 5 buildings (repeats included, so two Supply Centers in a row is its own line), clustered into the archetypes players actually settle into, with popularity and win rate per archetype. An opening needs at least ${
        book?.minGames ?? 15
      } games to get its own row; rarer builds fold into "Other" for that general.`}
      surface={false}
    >
      {queryFallback(query, "opening book")}
      {query.isSuccess && book && book.generals.length === 0 && (
        <Alert severity="info">
          Not computed yet — the opening book is built by the same nightly (or
          manually triggered) records recompute as the Records page.
        </Alert>
      )}
      {query.isSuccess &&
        book &&
        book.generals.map((general, index) => (
          <GeneralSection
            key={general.general}
            book={general}
            defaultExpanded={index < 2}
          />
        ))}
    </Page>
  )
}
