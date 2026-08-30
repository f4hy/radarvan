import { ProfileApi } from "../api/apis/ProfileApi"
import { apiConfig } from "../apiConfig"

export const ProfileClient = new ProfileApi(apiConfig)
