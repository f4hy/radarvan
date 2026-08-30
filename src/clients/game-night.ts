import { GameNightApi } from "../api/apis/GameNightApi"
import { apiConfig } from "../apiConfig"

export const GameNightClient = new GameNightApi(apiConfig)
