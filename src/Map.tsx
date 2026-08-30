// biome-ignore-all lint/suspicious/noArrayIndexKey: overlay dots are drawn
// from a positional list rebuilt whole on every map change — they carry no
// state and never reorder within a render.
import Card from "@mui/material/Card"
import Tooltip from "@mui/material/Tooltip"
import Box from "@mui/material/Box"
import IconButton from "@mui/material/IconButton"
import Typography from "@mui/material/Typography"
import DownloadIcon from "@mui/icons-material/Download"
import { useQuery } from "@tanstack/react-query"
import * as React from "react"
import { MapClient } from "./clients/map"
import { formatCash, getColorHex, totalMapSupply } from "./utils"

export type PlayerPosition = {
  name: string
  color?: string
  general?: string
}

type PointCategory = "playerStarts" | "supply" | "tech" | "garrison"

type PointStyle = {
  color: string
  size: number
  symbol?: string
  border?: string
}

const BASE_STYLES: Record<PointCategory, PointStyle> = {
  playerStarts: { color: "#000000", size: 12 },
  supply: { color: "#32CD32", size: 14, symbol: "$" },
  tech: { color: "#ffdd00", size: 14, symbol: "★" },
  garrison: { color: "#FFFFFF", size: 5, border: "2px solid #333333" },
}

function pointStyle(category: PointCategory, name: string): PointStyle {
  const base = BASE_STYLES[category]
  if (category === "supply" && name.includes("Small")) {
    return { ...base, color: "#1E90FF", size: 8 }
  }
  if (category === "tech" && name.includes("Derrick")) {
    return { ...base, symbol: "⛽" }
  }
  return base
}

function getMapImageApiUrl(mapname: string) {
  return `${import.meta.env.BASE_URL}api/map_image/${encodeURIComponent(mapname)}`
}

/** The map's image on its own, at list-row size.
 *
 * `GameMap` below is the full article - overlay dots, supply tooltip, a 300px
 * floor - which is the wrong thing to put in a row of eighty collapsed
 * accordions. This is just the picture, lazily loaded, so a list of map names
 * is recognisable at a glance without eighty overlay fetches behind it. */
export function MapThumbnail(props: { mapname: string; size?: number }) {
  const [failed, setFailed] = React.useState(false)
  const size = props.size ?? 44
  const basename = props.mapname.split("/").slice(-1).pop() ?? ""
  const sx = {
    width: size,
    height: size,
    borderRadius: 1,
    flexShrink: 0,
    display: "block",
    objectFit: "cover" as const,
  }
  React.useEffect(() => setFailed(false), [basename])
  if (!basename || failed) {
    return (
      <Box
        sx={{
          ...sx,
          bgcolor: "action.hover",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: size * 0.5,
          lineHeight: 1,
        }}
      >
        🗺️
      </Box>
    )
  }
  return (
    <Box
      component="img"
      src={getMapImageApiUrl(basename)}
      alt=""
      loading="lazy"
      decoding="async"
      onError={() => setFailed(true)}
      sx={sx}
    />
  )
}

/**
 * One map's geometry and supply data.
 *
 * This used to carry its own `mapDataResolved` / `mapDataInFlight` pair to
 * cache resolved payloads and deduplicate concurrent requests — a map thumbnail
 * appears in lists of eighty rows, and the same map repeats. The query client
 * does both, keyed on the map name, so the hand-rolled pair is gone.
 *
 * Map data is immutable in practice (it changes only when someone uploads a new
 * map file), so it is worth holding far longer than the corpus default.
 */
const MAP_DATA_STALE_MS = 60 * 60_000

function mapDataQueryOptions(mapname: string) {
  return {
    queryKey: ["mapData", mapname],
    queryFn: () =>
      MapClient.getMapDataApiMapDataMapNameGet({ mapName: mapname }),
    staleTime: MAP_DATA_STALE_MS,
    gcTime: MAP_DATA_STALE_MS,
    // A map with no data row 404s; that is an answer, not a failure to retry.
    retry: false,
  }
}

// Total collectible supply cash for a map — null until resolved, or if the map
// has none. `mapname` may be a full path (e.g. "userdata/maps/Foo") like
// MatchDetails.mapName; only the basename is a valid map_data lookup key.
export function useMapSupplyTotal(mapname: string): number | null {
  const basename = mapname.split("/").slice(-1).pop() ?? ""
  const { data } = useQuery({
    ...mapDataQueryOptions(basename),
    enabled: basename !== "",
  })
  return data ? totalMapSupply(data.supply) : null
}

export type EventDot = {
  x: number
  y: number
  color: string
  tooltip?: string
  // Optional styling used by the replay-playback overlay. Defaults preserve the
  // original kill-map look (8px translucent circle).
  shape?: "circle" | "square" | "x"
  size?: number
  opacity?: number
  borderColor?: string
}

export default function GameMap(props: {
  mapname: string
  playerPositions?: Record<number, PlayerPosition>
  eventDots?: EventDot[]
  showDownload?: boolean
  // When true, don't fetch the map overlay data (player starts / supply / tech)
  // up front — only the image. The data is fetched on first hover and then kept.
  deferData?: boolean
}) {
  const [imgError, setImgError] = React.useState(false)
  const [dataRequested, setDataRequested] = React.useState(false)
  const containerRef = React.useRef<HTMLDivElement>(null)

  // html2canvas is ~194 kB and only the Draft page's download button (the one
  // showDownload call site) ever reaches it, so it is imported on click rather
  // than at module scope — GameMap itself renders on the landing page.
  async function downloadScreenshot() {
    if (!containerRef.current) return
    const { default: html2canvas } = await import("html2canvas")
    const canvas = await html2canvas(containerRef.current, { useCORS: true })
    const link = document.createElement("a")
    link.download = `${props.mapname}.png`
    link.href = canvas.toDataURL("image/png")
    link.click()
  }

  const mapname = props.mapname.split("/").slice(-1).pop() ?? ""
  const mapUrl = mapname ? getMapImageApiUrl(mapname) : ""

  React.useEffect(() => {
    setImgError(false)
    setDataRequested(false)
  }, [mapname])

  // Deferred maps wait for a hover before fetching overlay data — `enabled` is
  // what expresses that now, and an already-cached map still renders instantly
  // because the query reads the cache without running the fetcher.
  const { data: mapData } = useQuery({
    ...mapDataQueryOptions(mapname),
    enabled: mapname !== "" && (!props.deferData || dataRequested),
  })

  const showPlaceholder = !mapUrl || imgError
  const supplyTotal = mapData ? totalMapSupply(mapData.supply) : 0
  const tooltipTitle =
    supplyTotal > 0
      ? `Map ${mapname} — total supplies ${formatCash(supplyTotal)}`
      : `Map ${mapname}`

  return (
    <Tooltip title={tooltipTitle}>
      <Card
        sx={{ minHeight: 300, minWidth: 300, position: "relative" }}
        onMouseEnter={
          props.deferData ? () => setDataRequested(true) : undefined
        }
      >
        {showPlaceholder ? (
          <Box
            sx={{
              minHeight: 300,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "action.hover",
              color: "text.secondary",
              gap: 1,
            }}
          >
            <Typography variant="h6">🗺️</Typography>
            <Typography
              variant="body2"
              sx={{
                textAlign: "center",
                px: 1,
              }}
            >
              {mapname || "Unknown Map"}
            </Typography>
          </Box>
        ) : (
          <Box
            ref={containerRef}
            sx={{
              position: "relative",
              lineHeight: 0,
              // Holds the card's height while the image is still in flight, so
              // a list of matches doesn't reflow as each map lands. Not an
              // aspect-ratio box on purpose: the overlay dots below are
              // positioned as a percentage of *this* element, so forcing a
              // ratio that differs from the image's own would move every dot.
              minHeight: 300,
            }}
          >
            <img
              src={mapUrl}
              alt={`Map: ${mapname}`}
              onError={() => setImgError(true)}
              // The landing page renders one of these per match; without this
              // an expanded game night fires a dozen full-size image requests
              // at once, all above the fold or not.
              loading="lazy"
              decoding="async"
              style={{ width: "100%", height: "auto", display: "block" }}
            />
            {mapData &&
              (Object.keys(BASE_STYLES) as PointCategory[]).flatMap(
                (category) => {
                  const points = mapData[category] ?? []
                  if (!points.length) return []
                  return points.map((pt, i) => {
                    const name = "name" in pt ? pt.name : ""
                    const { color, size, symbol, border } = pointStyle(
                      category,
                      name,
                    )
                    const playerEntry =
                      !symbol && "playerNumber" in pt
                        ? props.playerPositions?.[pt.playerNumber]
                        : undefined
                    const playerColor = playerEntry?.color
                      ? getColorHex(playerEntry.color)
                      : undefined
                    return (
                      <Tooltip
                        key={`${category}-${i}`}
                        title={
                          "name" in pt ? pt.name : `Player ${pt.playerNumber}`
                        }
                      >
                        <Box
                          sx={{
                            position: "absolute",
                            left: `${(pt.x / mapData.extent.width) * 100}%`,
                            top: `${(1 - pt.y / mapData.extent.height) * 100}%`,
                            transform: "translate(-50%, -50%)",
                            cursor: "default",
                            display: "flex",
                            flexDirection: "column",
                            alignItems: "center",
                            ...(symbol
                              ? {
                                  color,
                                  fontSize: size,
                                  lineHeight: 1,
                                  textShadow: "0 0 3px #000",
                                }
                              : {}),
                          }}
                        >
                          {playerEntry?.name && (
                            <Typography
                              sx={{
                                fontSize: 9,
                                lineHeight: 1.2,
                                color: playerColor ?? "white",
                                textShadow: "0 0 3px #000",
                                fontWeight: "bold",
                                whiteSpace: "nowrap",
                                mb: "1px",
                              }}
                            >
                              {playerEntry.name}
                            </Typography>
                          )}
                          {symbol ? (
                            symbol
                          ) : (
                            <Box
                              sx={{
                                width: size * 1.5,
                                height: size * 1.5,
                                borderRadius: "100%",
                                bgcolor: color,
                                border: playerColor
                                  ? `3px solid ${playerColor}`
                                  : (border ?? "2px solid white"),
                                boxShadow: "0 0 4px rgba(0,0,0,0.6)",
                                display: "flex",
                                alignItems: "center",
                                justifyContent: "center",
                                color: "white",
                                fontSize: size * 1.4,
                                fontWeight: "bold",
                                lineHeight: 1,
                              }}
                            >
                              {"playerNumber" in pt ? pt.playerNumber : ""}
                            </Box>
                          )}
                          {playerEntry?.general && (
                            <Typography
                              sx={{
                                fontSize: 9,
                                lineHeight: 1.2,
                                color: playerColor ?? "white",
                                textShadow: "0 0 3px #000",
                                fontWeight: "bold",
                                whiteSpace: "nowrap",
                                mt: "1px",
                              }}
                            >
                              {playerEntry.general}
                            </Typography>
                          )}
                        </Box>
                      </Tooltip>
                    )
                  })
                },
              )}
            {mapData &&
              props.eventDots?.map((dot, i) => {
                const size = dot.size ?? 8
                const common = {
                  position: "absolute" as const,
                  left: `${(dot.x / mapData.extent.width) * 100}%`,
                  top: `${(1 - dot.y / mapData.extent.height) * 100}%`,
                  transform: "translate(-50%, -50%)",
                  opacity: dot.opacity ?? 0.75,
                  pointerEvents: dot.tooltip
                    ? ("auto" as const)
                    : ("none" as const),
                }
                if (dot.shape === "x") {
                  return (
                    <Box
                      key={i}
                      component="span"
                      title={dot.tooltip}
                      sx={{
                        ...common,
                        color: dot.color,
                        fontSize: size,
                        lineHeight: 1,
                        fontWeight: "bold",
                        textShadow: "0 0 2px rgba(0,0,0,0.9)",
                        userSelect: "none",
                      }}
                    >
                      ✕
                    </Box>
                  )
                }
                return (
                  <Box
                    key={i}
                    component="span"
                    title={dot.tooltip}
                    sx={{
                      ...common,
                      width: size,
                      height: size,
                      borderRadius: dot.shape === "square" ? "2px" : "50%",
                      bgcolor: dot.color,
                      border: dot.borderColor
                        ? `1.5px solid ${dot.borderColor}`
                        : "none",
                      boxShadow:
                        dot.shape === "square"
                          ? "0 0 2px rgba(0,0,0,0.7)"
                          : "none",
                    }}
                  />
                )
              })}
          </Box>
        )}
        {props.showDownload && !showPlaceholder && (
          <Tooltip title="Download map image">
            <IconButton
              size="small"
              onClick={downloadScreenshot}
              sx={{
                position: "absolute",
                top: 4,
                right: 4,
                bgcolor: "rgba(0,0,0,0.45)",
                color: "white",
                "&:hover": { bgcolor: "rgba(0,0,0,0.7)" },
              }}
            >
              <DownloadIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        )}
      </Card>
    </Tooltip>
  )
}
