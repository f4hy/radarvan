// TS twin of radarvan/replay_files.py's map_display_name / map_key.
// tests/map_name_cases.json holds the shared cases; mapName.test.ts asserts
// this side, tests/test_map_key_parity.py the other. Change one, change both.

const MAP_SUFFIX = /\.map$/i

/** The map as a human reads it: path and `.map` suffix off, case kept. */
export function mapDisplayName(name: string): string {
  // "Unknown" for the empty string mirrors map_basename — a match with no
  // recorded map still has to render something.
  if (!name) return "Unknown"
  const base = name.split("/").pop() ?? name
  return base.replace(MAP_SUFFIX, "")
}

/** Join key between a stored map path and a map name held as a literal. */
export function mapKey(name: string): string {
  return mapDisplayName(name).replace(/\s+/g, "").toLowerCase()
}
