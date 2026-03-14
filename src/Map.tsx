import Card from "@mui/material/Card"
import Tooltip from "@mui/material/Tooltip"
import Box from "@mui/material/Box"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { MAPLIST } from "./maplist"

export interface MapPoint {
  x: number
  y: number
}

export interface MapPoints {
  extent: { width: number; height: number }
  player_starts?: MapPoint[]
  supply?: MapPoint[]
  tech?: MapPoint[]
}

const POINT_STYLES: Record<
  keyof Omit<MapPoints, "extent">,
  { color: string; size: number; label: string; symbol?: string }
> = {
  player_starts: { color: "#000000", size: 12, label: "Player start" },
  supply: { color: "#32CD32", size: 14, label: "Supply", symbol: "$" },
  tech: { color: "#ffdd00", size: 14, label: "Tech", symbol: "★" },
}

function getMapUrl(mapname: string) {
  return process.env.PUBLIC_URL + "/maps/" + mapname
}

const DEFCON_MAP_POINTS: MapPoints = {
  extent: {
    width: 3750,
    height: 3250,
  },
  player_starts: [
    {
      x: 3067.866,
      y: 2241.3677,
    },
    {
      x: 3081.7488,
      y: 783.14655,
    },
    {
      x: 610.3256,
      y: 805.0246,
    },
    {
      x: 557.3841,
      y: 2236.8733,
    },
    {
      x: 1758.0177,
      y: 402.17758,
    },
    {
      x: 1853.9447,
      y: 2753.7576,
    },
  ],
  supply: [
    {
      x: 1700.9873,
      y: 1666.29,
    },
    {
      x: 1736.4211,
      y: 1688.5862,
    },
    {
      x: 1819.8716,
      y: 1703.9249,
    },
    {
      x: 1885.8558,
      y: 1668.5663,
    },
    {
      x: 3428.2344,
      y: 1488.7258,
    },
    {
      x: 3499.1892,
      y: 1487.8044,
    },
    {
      x: 3479.719,
      y: 1465.3461,
    },
    {
      x: 3448.2815,
      y: 1461.485,
    },
    {
      x: 3462.7039,
      y: 1492.6294,
    },
    {
      x: 257.13385,
      y: 1489.3641,
    },
    {
      x: 328.08856,
      y: 1488.4427,
    },
    {
      x: 308.61835,
      y: 1465.9844,
    },
    {
      x: 277.181,
      y: 1462.1233,
    },
    {
      x: 291.60342,
      y: 1493.2677,
    },
    {
      x: 1101.8022,
      y: 350.7629,
    },
    {
      x: 1097.8093,
      y: 392.03888,
    },
    {
      x: 1133.688,
      y: 399.18613,
    },
    {
      x: 2457.9453,
      y: 353.9462,
    },
    {
      x: 2475.5537,
      y: 387.82382,
    },
    {
      x: 2492.3381,
      y: 345.10306,
    },
    {
      x: 2464.1719,
      y: 2675.1323,
    },
    {
      x: 2457.3794,
      y: 2731.2388,
    },
    {
      x: 2488.501,
      y: 2709.292,
    },
    {
      x: 1061.6813,
      y: 2734.642,
    },
    {
      x: 1041.0679,
      y: 2773.7258,
    },
    {
      x: 1076.3376,
      y: 2775.8782,
    },
    {
      x: 1783.9077,
      y: 1703.7163,
    },
    {
      x: 1842.03,
      y: 1348.1294,
    },
    {
      x: 1780.7373,
      y: 1336.1243,
    },
    {
      x: 1694.5245,
      y: 1372.4247,
    },
    {
      x: 1877.4639,
      y: 1370.4255,
    },
    {
      x: 1792.2961,
      y: 1580.8661,
    },
    {
      x: 1744.5372,
      y: 1343.7979,
    },
    {
      x: 1871.8635,
      y: 249.34592,
    },
    {
      x: 1752.6342,
      y: 2891.942,
    },
    {
      x: 2078.8198,
      y: 1523.7842,
    },
    {
      x: 1497.7148,
      y: 1523.012,
    },
    {
      x: 3208.493,
      y: 662.77496,
    },
    {
      x: 438.53052,
      y: 2375.9048,
    },
    {
      x: 457.8335,
      y: 677.25226,
    },
    {
      x: 3202.077,
      y: 2363.3538,
    },
  ],
  tech: [
    {
      x: 1550.0525,
      y: 209.17157,
    },
    {
      x: 1629.9352,
      y: 136.12279,
    },
    {
      x: 1990.2568,
      y: 2986.2546,
    },
    {
      x: 1908.0801,
      y: 3061.6506,
    },
    {
      x: 3219.9058,
      y: 2750.1802,
    },
    {
      x: 3300.6104,
      y: 2673.911,
    },
    {
      x: 3181.418,
      y: 352.36,
    },
    {
      x: 3107.792,
      y: 277.35568,
    },
    {
      x: 545.8004,
      y: 341.6529,
    },
    {
      x: 465.1367,
      y: 417.18484,
    },
    {
      x: 407.1521,
      y: 2758.929,
    },
    {
      x: 321.44733,
      y: 2672.034,
    },
    {
      x: 1788.4635,
      y: 1516.2352,
    },
  ],
}

export default function Map(props: { mapname: string; mapPoints?: MapPoints }) {
  const [imgError, setImgError] = React.useState(false)
  const mapname = props.mapname.split("/").slice(-1).pop() ?? ""
  const mapmatch = MAPLIST.find((m) => m.includes(mapname))
  const mapUrl = mapmatch ? getMapUrl(mapmatch) : ""

  const mapPoints =
    props.mapPoints ?? (mapname == "defcon6" ? DEFCON_MAP_POINTS : undefined)

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
            {mapPoints &&
              (
                Object.keys(POINT_STYLES) as (keyof Omit<MapPoints, "extent">)[]
              ).flatMap((category, i) => {
                const points = mapPoints[category]
                if (!points) return []
                const { color, size, label, symbol } = POINT_STYLES[category]
                return points.map((pt, i) => (
                  <Tooltip key={`${category}-${i}`} title={`${label} ${i}`}>
                    <Box
                      sx={{
                        position: "absolute",
                        left: `${(pt.x / mapPoints.extent.width) * 100}%`,
                        top: `${(pt.y / mapPoints.extent.height) * 100}%`,
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
              })}
          </Box>
        )}
      </Card>
    </Tooltip>
  )
}
