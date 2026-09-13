import { TournamentsApi } from "../api/apis/TournamentsApi"
import { apiConfig } from "../lib/apiConfig"

export const TournamentsClient = new TournamentsApi(apiConfig)
