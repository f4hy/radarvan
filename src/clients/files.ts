import { FilesApi } from "../api/apis/FilesApi"
import { apiConfig } from "../lib/apiConfig"

export const FilesClient = new FilesApi(apiConfig)
