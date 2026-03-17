import Card from "@mui/material/Card"
import Tooltip from "@mui/material/Tooltip"
import Box from "@mui/material/Box"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { MAPLIST } from "./maplist"
import { Client } from "./Client"
import type { MapDataPayload } from "./api"

type PointCategory = "playerStarts" | "supply" | "tech"

type PointStyle = { color: string; size: number; symbol?: string }

const BASE_STYLES: Record<PointCategory, PointStyle> = {
  playerStarts: { color: "#000000", size: 12 },
  supply: { color: "#32CD32", size: 14, symbol: "$" },
  tech: { color: "#ffdd00", size: 14, symbol: "★" },
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

function getMapUrl(mapname: string) {
  return process.env.PUBLIC_URL + "/maps/" + mapname
}

function resolveMap(mapname: string) {
  const direct = MAPLIST.find((m) => m.includes(mapname))
  if (direct) {
    return direct
  }
  const underscored = MAPLIST.find((m) =>
    m.includes(mapname.replaceAll(" ", "_")),
  )
  return underscored
}

const mapDataResolved: Record<string, MapDataPayload> = {}
const mapDataInFlight: Record<string, Promise<MapDataPayload>> = {}

function fetchMapData(mapname: string): Promise<MapDataPayload> {
  const resolved = mapDataResolved[mapname]
  if (resolved) return Promise.resolve(resolved)
  if (!mapDataInFlight[mapname]) {
    const promise = Client.getMapDataApiMapDataMapNameGet({ mapName: mapname })
      .then((data) => {
        mapDataResolved[mapname] = data
        delete mapDataInFlight[mapname]
        return data
      })
      .catch((err) => {
        delete mapDataInFlight[mapname]
        return Promise.reject(err)
      })
    mapDataInFlight[mapname] = promise
  }
  return mapDataInFlight[mapname]
}

export type EventDot = {
  x: number
  y: number
  color: string
  tooltip?: string
}

export default function GameMap(props: {
  mapname: string
  playerPositions?: Record<number, string>
  eventDots?: EventDot[]
}) {
  const [imgError, setImgError] = React.useState(false)
  const [mapData, setMapData] = React.useState<MapDataPayload | null>(null)

  const mapname = props.mapname.split("/").slice(-1).pop() ?? ""
  const mapmatch = resolveMap(mapname)
  const mapUrl = mapmatch ? getMapUrl(mapmatch) : ""

  React.useEffect(() => {
    if (!mapname) {
      setMapData(null)
      return
    }
    const resolved = mapDataResolved[mapname]
    if (resolved) {
      setMapData(resolved)
      return
    }
    setMapData(null)
    let cancelled = false
    fetchMapData(mapname).then(
      (data) => {
        if (!cancelled) setMapData(data)
      },
      () => {
        if (!cancelled) setMapData(null)
      },
    )
    return () => {
      cancelled = true
    }
  }, [mapname])

  const showPlaceholder = !mapUrl || imgError

  return (
    <Tooltip title={"Map " + mapname}>
      <Card sx={{ minHeight: 300, minWidth: 300 }}>
        {showPlaceholder ? (
          <Box
            sx={{
              minHeight: 300,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              bgcolor: "grey.200",
              color: "text.secondary",
              gap: 1,
            }}
          >
            <Typography variant="h6">🗺️</Typography>
            <Typography variant="body2" textAlign="center" sx={{ px: 1 }}>
              {mapname || "Unknown Map"}
            </Typography>
          </Box>
        ) : (
          <Box sx={{ position: "relative", lineHeight: 0 }}>
            <img
              src={mapUrl}
              alt={"Map: " + mapname}
              onError={() => setImgError(true)}
              style={{ width: "100%", height: "auto", display: "block" }}
            />
            {mapData &&
              (Object.keys(BASE_STYLES) as PointCategory[]).flatMap(
                (category) => {
                  const points = mapData[category]
                  if (!points.length) return []
                  return points.map((pt, i) => {
                    const name = "name" in pt ? pt.name : ""
                    const { color, size, symbol } = pointStyle(category, name)
                    const playerName =
                      !symbol && "playerNumber" in pt
                        ? props.playerPositions?.[pt.playerNumber]
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
                          {symbol ? (
                            symbol
                          ) : (
                            <Box
                              sx={{
                                width: size * 1.5,
                                height: size * 1.5,
                                borderRadius: "100%",
                                bgcolor: color,
                                border: "2px solid white",
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
                          {playerName && (
                            <Typography
                              sx={{
                                fontSize: 9,
                                lineHeight: 1.2,
                                color: "white",
                                textShadow: "0 0 3px #000",
                                fontWeight: "bold",
                                whiteSpace: "nowrap",
                                mt: "1px",
                              }}
                            >
                              {playerName}
                            </Typography>
                          )}
                        </Box>
                      </Tooltip>
                    )
                  })
                },
              )}
            {mapData &&
              props.eventDots?.map((dot, i) => (
                <Box
                  key={i}
                  component="span"
                  title={dot.tooltip}
                  sx={{
                    position: "absolute",
                    left: `${(dot.x / mapData.extent.width) * 100}%`,
                    top: `${(1 - dot.y / mapData.extent.height) * 100}%`,
                    transform: "translate(-50%, -50%)",
                    width: 8,
                    height: 8,
                    borderRadius: "50%",
                    bgcolor: dot.color,
                    opacity: 0.75,
                    pointerEvents: dot.tooltip ? "auto" : "none",
                  }}
                />
              ))}
          </Box>
        )}
      </Card>
    </Tooltip>
  )
}
