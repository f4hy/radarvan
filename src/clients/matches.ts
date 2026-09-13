import { MatchesApi } from "../api/apis/MatchesApi"
import { apiConfig } from "../lib/apiConfig"

export const MatchesClient = new MatchesApi(apiConfig)
