import { PredictApi } from "../api/apis/PredictApi"
import { apiConfig } from "../lib/apiConfig"

export const PredictClient = new PredictApi(apiConfig)
