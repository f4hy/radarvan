import { TeamsApi } from "../api/apis/TeamsApi"
import { apiConfig } from "../apiConfig"

export const TeamsClient = new TeamsApi(apiConfig)
