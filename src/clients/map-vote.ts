import { MapVoteApi } from "../api/apis/MapVoteApi"
import { apiConfig } from "../lib/apiConfig"

export const MapVoteClient = new MapVoteApi(apiConfig)
