import { GeneralsApi } from "../api/apis/GeneralsApi"
import { apiConfig } from "../apiConfig"

export const GeneralsClient = new GeneralsApi(apiConfig)
