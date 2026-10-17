// Map-upload helper. A same-origin multipart POST, so the session cookie
// authenticates the uploader (login required server-side).

import { uploadMapsApiMapUploadPost } from "../../api/sdk.gen"
import type { MapUploadResponse } from "../../api/types.gen"

export type { MapUploadResponse, MapUploadItem } from "../../api/types.gen"

export interface MapUploadFiles {
  tga?: File
  map?: File
  zip?: File
}

export async function uploadMaps(
  files: MapUploadFiles,
  commit: boolean,
): Promise<MapUploadResponse> {
  const { data } = await uploadMapsApiMapUploadPost({
    body: {
      commit,
      ...(files.zip && { zip_file: files.zip }),
      ...(files.tga && { tga: files.tga }),
      ...(files.map && { map_file: files.map }),
    },
  })
  return data
}
