import { AdminApi } from "../api/apis/AdminApi"
import { apiConfig } from "../lib/apiConfig"

export const AdminClient = new AdminApi(apiConfig)
