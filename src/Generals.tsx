import Avatar from "@mui/material/Avatar"
import Badge from "@mui/material/Badge"
import china from "./img/Gen_China_Logo.webp"
import usa from "./img/Gen_USA_Logo.webp"
import gla from "./img/Gla.webp"
import { General } from "./proto/match"

type Side = "GLA" | "CHINA" | "USA"

const sideImg: Record<Side, string> = {
  GLA: gla,
  CHINA: china,
  USA: usa,
}

function generalToSide(general: General): Side {
  switch (general) {
    case General.USA:
    case General.AIR:
    case General.LASER:
    case General.SUPER:
      return "USA"
    case General.CHINA:
    case General.NUKE:
    case General.TANK:
    case General.INFANTRY:
      return "CHINA"
    case General.GLA:
    case General.TOXIN:
    case General.STEALTH:
    case General.DEMO:
      return "GLA"
    default:
      return "USA"
  }
}

export default function DisplayGeneral(props: { general: General }) {
  let general: string | null = General[props.general]
  let avatar = (<Avatar
    key={props.general}
    src={sideImg[generalToSide(props.general)]}
    sx={{ width: "2rem", height: "2.1rem" }}
  />
  )
  if (general == "UNRECOGNIZED") {
    general = null
    avatar = (<Avatar
      key={props.general}
      sx={{ width: "2rem", height: "2.1rem" }}
    >?</Avatar>
    )
  }
  return (
    <>
      <Badge
        badgeContent={general}
        color="primary"
        sx={{ fontSize: 1 }}
      >
        {avatar}
      </Badge>
    </>
  )
}
