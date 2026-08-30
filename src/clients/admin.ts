import { AdminApi } from "../api/apis/AdminApi"
import { apiConfig } from "../apiConfig"

export const AdminClient = new AdminApi(apiConfig)
