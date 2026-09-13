import { PlayersApi } from "../api/apis/PlayersApi"
import { apiConfig } from "../lib/apiConfig"
export const PlayersClient = new PlayersApi(apiConfig)
