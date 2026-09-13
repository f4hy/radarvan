import { BracketApi } from "../api/apis/BracketApi"
import { apiConfig } from "../lib/apiConfig"

export const BracketClient = new BracketApi(apiConfig)
