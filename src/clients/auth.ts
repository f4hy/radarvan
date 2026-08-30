import { AuthApi } from "../api/apis/AuthApi"
import { apiConfig } from "../apiConfig"
export const AuthClient = new AuthApi(apiConfig)
