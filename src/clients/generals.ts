import { GeneralsApi } from "../api/apis/GeneralsApi"
import { apiConfig } from "../lib/apiConfig"

export const GeneralsClient = new GeneralsApi(apiConfig)
