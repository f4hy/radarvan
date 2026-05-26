import { DefaultApi, Configuration } from "./api"

const apiKey = import.meta.env.VITE_API_KEY as string | undefined
const headers: Record<string, string> = { "X-Client-Id": "react-frontend" }
if (apiKey) {
  headers["X-API-Key"] = apiKey
}

function getConfig(): Configuration {
  // Using a framework-agnostic check for NODE_ENV
  if (import.meta.env.MODE === "development") {
    return new Configuration({
      basePath: "http://localhost:8000",
      headers,
    })
  }
  // This will be used in production
  return new Configuration({
    basePath: "https://radarvan-5e9c302c60e6.herokuapp.com",
    headers,
  })
}
const config = getConfig()
export const Client = new DefaultApi(config)
