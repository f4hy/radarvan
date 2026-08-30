import { FilesApi } from "../api/apis/FilesApi"
import { apiConfig } from "../apiConfig"

export const FilesClient = new FilesApi(apiConfig)
