import { General } from "./General"

export function toGeneralName(n: number): string {
  return General[n] ?? "UNKNOWN"
}
