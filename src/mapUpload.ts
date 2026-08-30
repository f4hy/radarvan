// Map-upload helper. Same-origin multipart POST so the session cookie
// authenticates the uploader (login required server-side).
//
// This is the one route that does NOT go through the generated client: the
// generator mishandles a multipart body with binary fields — it hardcodes
// `useForm = false` in `uploadMapsApiMapUploadPost`, so it would send the files
// as a URLSearchParams body and the upload would fail. The response *types* and
// the JSON converter are still the generated ones, so the shape stays tied to
// the backend even though the request is hand-built.

import { type MapUploadResponse, MapUploadResponseFromJSON } from "./api"
import { responseErrorMessage } from "./apiError"

export type { MapUploadResponse, MapUploadItem } from "./api"

export interface MapUploadFiles {
  tga?: File
  map?: File
  zip?: File
}

export async function uploadMaps(
  files: MapUploadFiles,
  commit: boolean,
): Promise<MapUploadResponse> {
  const fd = new FormData()
  fd.append("commit", String(commit))
  if (files.zip) fd.append("zip_file", files.zip)
  if (files.tga) fd.append("tga", files.tga)
  if (files.map) fd.append("map_file", files.map)

  const resp = await fetch("/api/map_upload", {
    method: "POST",
    credentials: "same-origin",
    body: fd,
  })
  if (!resp.ok) {
    throw new Error(await responseErrorMessage(resp))
  }
  return MapUploadResponseFromJSON(await resp.json())
}
