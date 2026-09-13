import { OpeningBookApi } from "../api/apis/OpeningBookApi"
import { apiConfig } from "../lib/apiConfig"

export const OpeningBookClient = new OpeningBookApi(apiConfig)
