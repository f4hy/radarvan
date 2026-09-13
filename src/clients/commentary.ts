import { CommentaryApi } from "../api/apis/CommentaryApi"
import { apiConfig } from "../lib/apiConfig"

export const CommentaryClient = new CommentaryApi(apiConfig)
