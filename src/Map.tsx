import Card from "@mui/material/Card"
import Tooltip from "@mui/material/Tooltip"
import Box from "@mui/material/Box"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { MAPLIST } from "./maplist"
import { Client } from "./Client"
import type { MapDataPayload } from "./api"

type PointCategory = "playerStarts" | "supply" | "tech"

const POINT_STYLES: Record<
  PointCategory,
  { color: string; size: number; label: string; symbol?: string }
> = {
  playerStarts: { color: "#000000", size: 12, label: "Player start" },
  supply: { color: "#32CD32", size: 14, label: "Supply", symbol: "$" },
  tech: { color: "#ffdd00", size: 14, label: "Tech", symbol: "★" },
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

export default function Map(props: { mapname: string }) {
  const [imgError, setImgError] = React.useState(false)
  const [mapData, setMapData] = React.useState<MapDataPayload | null>(null)

  const mapname = props.mapname.split("/").slice(-1).pop() ?? ""
  const mapmatch = resolveMap(mapname)
  const mapUrl = mapmatch ? getMapUrl(mapmatch) : ""

  console.log(
    "Mapname:" + mapname + " mapmatch:" + mapmatch + " mapUrl" + mapUrl,
  )

  React.useEffect(() => {
    setMapData(null)
    if (!mapname) return
    Client.getMapDataApiMapDataMapNameGet({ mapName: mapname }).then(
      (data) => setMapData(data),
      () => setMapData(null),
    )
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
              (Object.keys(POINT_STYLES) as PointCategory[]).flatMap(
                (category) => {
                  const points = mapData[category]
                  if (!points.length) return []
                  const { color, size, label, symbol } = POINT_STYLES[category]
                  return points.map((pt, i) => (
                    <Tooltip key={`${category}-${i}`} title={`${label} ${i}`}>
                      <Box
                        sx={{
                          position: "absolute",
                          left: `${(pt.x / mapData.extent.width) * 100}%`,
                          top: `${(pt.y / mapData.extent.height) * 100}%`,
                          transform: "translate(-50%, -50%)",
                          cursor: "default",
                          ...(symbol
                            ? {
                                color,
                                fontSize: size,
                                lineHeight: 1,
                                textShadow: "0 0 3px #000",
                              }
                            : {
                                width: size,
                                height: size,
                                borderRadius: "50%",
                                bgcolor: color,
                                border: "2px solid white",
                                boxShadow: "0 0 4px rgba(0,0,0,0.6)",
                              }),
                        }}
                      >
                        {symbol ?? ""}
                      </Box>
                    </Tooltip>
                  ))
                },
              )}
          </Box>
        )}
      </Card>
    </Tooltip>
  )
}
