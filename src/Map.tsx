import Card from "@mui/material/Card"
import CardMedia from "@mui/material/CardMedia"
import Tooltip from "@mui/material/Tooltip"
import Box from "@mui/material/Box"
import Typography from "@mui/material/Typography"
import * as React from "react"
import { MAPLIST } from "./maplist"

function getMapUrl(mapname: string) {
  return process.env.PUBLIC_URL + "/maps/" + mapname
}

export default function Map(props: { mapname: string }) {
  const [imgError, setImgError] = React.useState(false)
  const mapname = props.mapname.split("/").slice(-1).pop() ?? ""
  const mapmatch = MAPLIST.find((m) => m.includes(mapname))
  const mapUrl = mapmatch ? getMapUrl(mapmatch) : ""

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
          <CardMedia
            component="img"
            image={mapUrl}
            height="99%"
            alt={"Map: " + mapname}
            onError={() => setImgError(true)}
          />
        )}
      </Card>
    </Tooltip>
  )
}
