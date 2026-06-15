// Map-upload helpers. Same-origin multipart POST so the session cookie
// authenticates the uploader (login required server-side).

export interface MapUploadItem {
  base_name: string
  image: string | null
  player_count: number | null
  already_exists: boolean
  saved: boolean
}

export interface MapUploadResponse {
  committed: boolean
  maps: MapUploadItem[]
  errors: string[]
}

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
    let detail = `Upload failed (${resp.status})`
    try {
      const body = (await resp.json()) as { detail?: string }
      if (body?.detail) detail = body.detail
    } catch {
      // non-JSON error body; keep the generic message
    }
    throw new Error(detail)
  }
  return (await resp.json()) as MapUploadResponse
}
