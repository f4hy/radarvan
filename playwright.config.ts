import { defineConfig, devices } from "@playwright/test"

/**
 * End-to-end tests for the built frontend.
 *
 * What this replaced: the unmodified `npm init playwright` scaffold, which
 * navigated to playwright.dev and asserted things about *their* documentation.
 * It ran on every push and PR across three browsers, so CI carried a permanently
 * green end-to-end job that had never once loaded this app.
 *
 * Firefox only, deliberately — the repo's Chromium build isn't installed (see
 * the root CLAUDE.md), and three engines for a small internal app buys
 * repetition rather than coverage.
 *
 * The API is mocked at the network layer (`e2e/mockApi.ts`), so these tests need
 * no database and no backend. That is a real division of labour, not a shortcut:
 * the server's own behaviour — including the SPA fallback that makes these URLs
 * work at all — is covered by `tests/test_spa_fallback.py`, and the payload
 * shapes are pinned to the generated client's types, so a backend schema change
 * breaks `tsc` rather than drifting silently.
 */
export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: process.env.CI ? [["html"], ["list"]] : "list",
  // Generous but finite: a hung page should fail the run, not hold it for the
  // job's whole 60-minute budget the way the old config allowed.
  timeout: 30_000,
  expect: { timeout: 10_000 },

  use: {
    baseURL: "http://localhost:4173",
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },

  projects: [{ name: "firefox", use: { ...devices["Desktop Firefox"] } }],

  // `vite preview` serves the production build — the same bundle that ships,
  // with the same code-splitting, rather than the dev server's module graph.
  webServer: {
    command: "npm run build && npm run preview -- --port 4173 --strictPort",
    url: "http://localhost:4173",
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
  },
})
