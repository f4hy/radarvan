import { General } from "./proto/match"

export function toGeneralName(n: number): string {
  return General[n]
}
