import { General } from "./General"

export function toGeneralName(n: number): string {
  return General[n] ?? "UNKNOWN"
}

export type Faction = "USA" | "CHINA" | "GLA"

export const FACTIONS: {
  faction: Faction
  name: string
  generals: General[]
}[] = [
  {
    faction: "USA",
    name: "USA",
    generals: [General.USA, General.AIR, General.LASER, General.SUPER],
  },
  {
    faction: "CHINA",
    name: "China",
    generals: [General.CHINA, General.NUKE, General.TANK, General.INFANTRY],
  },
  {
    faction: "GLA",
    name: "GLA",
    generals: [General.GLA, General.TOXIN, General.STEALTH, General.DEMO],
  },
]

export function generalFaction(general: General): Faction | undefined {
  return FACTIONS.find((f) => f.generals.includes(general))?.faction
}
