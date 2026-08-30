import { PredictApi } from "../api/apis/PredictApi"
import { apiConfig } from "../apiConfig"

export const PredictClient = new PredictApi(apiConfig)
