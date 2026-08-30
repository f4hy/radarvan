import { MatchesApi } from "../api/apis/MatchesApi"
import { apiConfig } from "../apiConfig"

export const MatchesClient = new MatchesApi(apiConfig)
