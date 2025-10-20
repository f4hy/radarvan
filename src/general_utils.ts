import { General } from "./proto/match"

type Side = "GLA" | "CHINA" | "USA"



export function toGeneralName(n : number): string{
	return General[n]
}
