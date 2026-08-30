import { CommentaryApi } from "../api/apis/CommentaryApi"
import { apiConfig } from "../apiConfig"

export const CommentaryClient = new CommentaryApi(apiConfig)
