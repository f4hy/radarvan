import { ProfileApi } from "../api/apis/ProfileApi"
import { apiConfig } from "../lib/apiConfig"

export const ProfileClient = new ProfileApi(apiConfig)
