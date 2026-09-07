import { OpeningBookApi } from "../api/apis/OpeningBookApi"
import { apiConfig } from "../apiConfig"

export const OpeningBookClient = new OpeningBookApi(apiConfig)
