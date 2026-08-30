import { PlayersApi } from "../api/apis/PlayersApi"
import { apiConfig } from "../apiConfig"
export const PlayersClient = new PlayersApi(apiConfig)
