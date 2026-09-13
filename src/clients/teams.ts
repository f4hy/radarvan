import { TeamsApi } from "../api/apis/TeamsApi"
import { apiConfig } from "../lib/apiConfig"

export const TeamsClient = new TeamsApi(apiConfig)
