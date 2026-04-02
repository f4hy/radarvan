import { DefaultApi, Configuration } from "./api"

const apiKey = import.meta.env.VITE_API_KEY as string | undefined
const authHeaders = apiKey ? { "X-API-Key": apiKey } : undefined

function getConfig(): Configuration {
  // Using a framework-agnostic check for NODE_ENV
  if (import.meta.env.MODE === "development") {
    return new Configuration({
      basePath: "http://localhost:8000",
      headers: authHeaders,
    })
  }
  // This will be used in production
  return new Configuration({
    basePath: "https://radarvan-5e9c302c60e6.herokuapp.com",
    headers: authHeaders,
  })
}
const config = getConfig()
export const Client = new DefaultApi(config)
