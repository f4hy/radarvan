import { defineConfig } from "vite"
import { configDefaults } from "vitest/config"
import react from "@vitejs/plugin-react"

// Where the dev server proxies /api. Defaults to the backend running on the
// host; docker compose sets this to http://backend:8000, where the API lives
// inside the compose network.
const apiTarget = process.env.VITE_API_PROXY_TARGET ?? "http://localhost:8000"

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api": {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
  test: {
    globals: true,
    environment: "jsdom",
    passWithNoTests: true,
    exclude: [...configDefaults.exclude, "e2e/**"],
  },
})
