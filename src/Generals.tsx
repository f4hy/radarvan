import Avatar from "@mui/material/Avatar"
import Badge from "@mui/material/Badge"
import china from "./img/Gen_China_Logo.webp"
import usa from "./img/Gen_USA_Logo.webp"
import gla from "./img/Gla.webp"
import { General } from "./General"

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

/** A general's faction logo on its own, sizable and with no name badge.
 *
 * `DisplayGeneral` below is this plus the badge, and is what most of the app
 * wants. This bare form is for places that already write the name themselves
 * and only need the icon to make a row scannable - a table's row labels, a
 * matrix header - where a badge would collide with the text beside it. */
export function GeneralAvatar(props: { general: General; size?: string }) {
  const size = props.size ?? "2rem"
  const known = General[props.general] !== "UNRECOGNIZED"
  const sx = { width: size, height: size, fontSize: "0.75rem" }
  return known ? (
    <Avatar src={sideImg[generalToSide(props.general)]} sx={sx} />
  ) : (
    <Avatar sx={sx}>?</Avatar>
  )
}

export default function DisplayGeneral(props: { general: General }) {
  const general: string | null =
    General[props.general] === "UNRECOGNIZED" ? null : General[props.general]
  return (
    <Badge badgeContent={general} color="primary" sx={{ fontSize: 1 }}>
      <GeneralAvatar general={props.general} size="2rem" />
    </Badge>
  )
}
