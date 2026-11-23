import PersonIcon from "@mui/icons-material/Person"
import SearchIcon from "@mui/icons-material/Search"
import TagIcon from "@mui/icons-material/Tag"
import Autocomplete, { createFilterOptions } from "@mui/material/Autocomplete"
import Box from "@mui/material/Box"
import Dialog from "@mui/material/Dialog"
import IconButton from "@mui/material/IconButton"
import InputAdornment from "@mui/material/InputAdornment"
import TextField from "@mui/material/TextField"
import Tooltip from "@mui/material/Tooltip"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import { useNavigate } from "react-router"
import {
  getEligiblePlayersApiPlayerProfileEligiblePlayersGetOptions,
  getPlayerGameCountsApiPlayerGameCountsGetOptions,
} from "../api/@tanstack/react-query.gen"
import { matchHref, playerProfileHref } from "../lib/links"
import type { RouteGroup } from "../routes"

type SearchOption =
  | { kind: "match"; label: string; href: string }
  | { kind: "player"; label: string; href: string }
  | { kind: "page"; label: string; href: string; icon: React.ReactNode }

const GROUP_LABEL: Record<SearchOption["kind"], string> = {
  match: "Match",
  player: "Players",
  page: "Pages",
}

const MATCH_ID = /^#?\s*([1-9]\d*)$/
const baseFilter = createFilterOptions<SearchOption>()

// A typed number is a match id: offer it first, alongside anything else it matches.
function filterOptions(
  options: SearchOption[],
  state: Parameters<typeof baseFilter>[1],
): SearchOption[] {
  const filtered = baseFilter(options, state)
  const id = MATCH_ID.exec(state.inputValue.trim())?.[1]
  if (id === undefined) return filtered
  return [
    { kind: "match", label: `Match #${id}`, href: matchHref(Number(id)) },
    ...filtered,
  ]
}

function isTypingTarget(target: EventTarget | null): boolean {
  if (!(target instanceof HTMLElement)) return false
  return (
    target.isContentEditable ||
    ["INPUT", "TEXTAREA", "SELECT"].includes(target.tagName)
  )
}

function SearchBox(props: {
  groups: RouteGroup[]
  inputRef?: React.Ref<HTMLInputElement>
  autoFocus?: boolean
  onDone?: () => void
}) {
  const navigate = useNavigate()
  const [input, setInput] = React.useState("")
  // The player list is only fetched once someone reaches for the box, so a
  // visitor who never searches doesn't pay a request on every page load.
  const [wanted, setWanted] = React.useState(props.autoFocus ?? false)
  const playersQuery = useQuery({
    ...getEligiblePlayersApiPlayerProfileEligiblePlayersGetOptions(),
    enabled: wanted,
    select: (names) => names.filter((n): n is string => n != null),
  })
  const countsQuery = useQuery({
    ...getPlayerGameCountsApiPlayerGameCountsGetOptions(),
    enabled: wanted,
  })

  const options = React.useMemo<SearchOption[]>(() => {
    const games = new Map(countsQuery.data?.map((c) => [c.name, c.count]))
    const players = [...(playersQuery.data ?? [])]
      .sort((a, b) => (games.get(b) ?? 0) - (games.get(a) ?? 0))
      .map(
        (name): SearchOption => ({
          kind: "player",
          label: name,
          href: playerProfileHref(name),
        }),
      )
    const pages = props.groups.flatMap((g) =>
      g.routes.map(
        (r): SearchOption => ({
          kind: "page",
          label: r.title,
          href: `/${r.slug}`,
          icon: r.icon,
        }),
      ),
    )
    return [...players, ...pages]
  }, [playersQuery.data, countsQuery.data, props.groups])

  return (
    <Autocomplete<SearchOption, false, false, false>
      options={options}
      value={null}
      inputValue={input}
      onInputChange={(_, v, reason) => {
        if (reason !== "reset") setInput(v)
      }}
      onChange={(_, option) => {
        if (option == null) return
        setInput("")
        navigate(option.href)
        props.onDone?.()
      }}
      onOpen={() => setWanted(true)}
      filterOptions={filterOptions}
      groupBy={(o) => GROUP_LABEL[o.kind]}
      getOptionKey={(o) => `${o.kind}:${o.href}`}
      isOptionEqualToValue={(a, b) => a.href === b.href}
      loading={playersQuery.isPending && wanted}
      noOptionsText="No player or page by that name"
      blurOnSelect
      autoHighlight
      size="small"
      forcePopupIcon={false}
      sx={{ width: "100%" }}
      renderOption={({ key, ...optionProps }, option) => (
        <Box
          component="li"
          key={key}
          {...optionProps}
          sx={{ gap: 1.5, "& .MuiSvgIcon-root": { fontSize: 18 } }}
        >
          <Box
            component="span"
            sx={{ display: "flex", color: "text.secondary" }}
          >
            {option.kind === "page" ? (
              option.icon
            ) : option.kind === "player" ? (
              <PersonIcon />
            ) : (
              <TagIcon />
            )}
          </Box>
          {option.label}
        </Box>
      )}
      renderInput={(params) => (
        <TextField
          {...params}
          inputRef={props.inputRef}
          autoFocus={props.autoFocus}
          placeholder="Player, page or match #"
          onFocus={() => setWanted(true)}
          slotProps={{
            ...params.slotProps,
            htmlInput: {
              ...params.slotProps.htmlInput,
              "aria-label": "Site search",
            },
            input: {
              ...params.slotProps.input,
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            },
          }}
        />
      )}
    />
  )
}

/** App-bar search: jump to a player's profile, any page, or a match by id.
 * `/` or Ctrl/⌘+K focuses it from anywhere. */
export default function SiteSearch(props: { groups: RouteGroup[] }) {
  const inputRef = React.useRef<HTMLInputElement>(null)
  const [dialogOpen, setDialogOpen] = React.useState(false)

  React.useEffect(() => {
    function onKeyDown(e: KeyboardEvent) {
      const shortcut =
        (e.key === "k" && (e.metaKey || e.ctrlKey)) ||
        (e.key === "/" && !e.metaKey && !e.ctrlKey && !e.altKey)
      if (!shortcut || (e.key === "/" && isTypingTarget(e.target))) return
      e.preventDefault()
      // The inline box is display:none on phones, so it has no layout box there.
      const input = inputRef.current
      if (input?.offsetParent != null) input.focus()
      else setDialogOpen(true)
    }
    window.addEventListener("keydown", onKeyDown)
    return () => window.removeEventListener("keydown", onKeyDown)
  }, [])

  return (
    <>
      <Box
        sx={{ display: { xs: "none", sm: "block" }, width: 320, maxWidth: 1 }}
      >
        <SearchBox groups={props.groups} inputRef={inputRef} />
      </Box>
      <Tooltip title="Search">
        <IconButton
          color="inherit"
          aria-label="Site search"
          onClick={() => setDialogOpen(true)}
          sx={{ display: { xs: "inline-flex", sm: "none" } }}
        >
          <SearchIcon />
        </IconButton>
      </Tooltip>
      <Dialog
        open={dialogOpen}
        onClose={() => setDialogOpen(false)}
        fullWidth
        slotProps={{
          paper: { sx: { alignSelf: "flex-start", mt: 8, p: 1.5 } },
        }}
      >
        <SearchBox
          groups={props.groups}
          autoFocus
          onDone={() => setDialogOpen(false)}
        />
      </Dialog>
    </>
  )
}
