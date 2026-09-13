import { GameNightApi } from "../api/apis/GameNightApi"
import { apiConfig } from "../lib/apiConfig"

export const GameNightClient = new GameNightApi(apiConfig)
