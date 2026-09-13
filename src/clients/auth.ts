import { AuthApi } from "../api/apis/AuthApi"
import { apiConfig } from "../lib/apiConfig"
export const AuthClient = new AuthApi(apiConfig)
