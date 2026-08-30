import { TournamentsApi } from "../api/apis/TournamentsApi"
import { apiConfig } from "../apiConfig"

export const TournamentsClient = new TournamentsApi(apiConfig)
