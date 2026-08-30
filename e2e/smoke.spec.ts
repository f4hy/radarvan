import { expect, test } from "@playwright/test"
import {
  expectClean,
  expectNoErrorBoundary,
  heading,
  watchForProblems,
} from "./harness"
import { mockApi, unmockedReport } from "./mockApi"

/**
 * Every page renders, and renders without incident.
 *
 * The slug/title pairs are duplicated from `src/routes.tsx` on purpose: a test
 * that imported the route table would agree with it by construction and could
 * never catch a page being renamed, regrouped, or dropped.
 */
const PAGES: [slug: string, title: string][] = [
  ["matches", "Matches"],
  ["game-night", "Game Night"],
  ["tournaments", "Tournaments"],
  ["bracket", "1v1 Bracket"],
  ["balance-teams", "Balance Teams"],
  ["draft", "Map Draft"],
  ["superlatives", "Records"],
  ["team-stats", "Team Stats"],
  ["general-stats", "General Stats"],
  ["powers", "Generals Powers"],
  ["game-length", "Game Length"],
  ["ffa", "Free-For-All"],
  ["player-stats", "Player Stats"],
  ["player-profile", "Player Profile"],
  ["head-to-head", "Head to Head"],
  ["player-rating-trend", "Rating Trend"],
  ["map-stats", "Map Stats"],
  ["map-voting", "Map Voting"],
  ["choose-map", "Choose Map"],
  ["map-upload", "Upload Map"],
  ["account", "Account"],
]

/**
 * Routes that are gated out of the sidebar but still reachable by URL — which is
 * deliberate (see the rating-levels note in the root CLAUDE.md), so they still
 * have to render.
 *
 * Checked separately because these four predate `Page` and render their own
 * headings, so they have no `<h1>` to assert on. That is worth fixing, but the
 * assertion that matters here is the one that would have caught a crash on
 * Player Ratings reaching a user: no error boundary, no console errors.
 */
const GATED_PAGES = [
  "player-rating",
  "player-synergy",
  "debug-data",
  "admin-panel",
]

for (const [slug, title] of PAGES) {
  test(`/${slug} renders "${title}"`, async ({ page }) => {
    const problems = watchForProblems(page)
    const mock = await mockApi(page)

    await page.goto(`/${slug}`)

    expect(await heading(page)).toBe(title)
    // After the heading, not instead of it: the heading can render a frame
    // before a chart below it throws.
    await page.waitForLoadState("networkidle")
    await expectNoErrorBoundary(page)
    expectClean(problems)
    expect(
      mock.unmocked,
      `page called endpoints with no fixture: ${unmockedReport(mock)}`,
    ).toEqual([])
  })
}

for (const slug of GATED_PAGES) {
  test(`/${slug} renders without incident`, async ({ page }) => {
    const problems = watchForProblems(page)
    const mock = await mockApi(page)

    await page.goto(`/${slug}`)
    await page.waitForLoadState("networkidle")

    await expectNoErrorBoundary(page)
    expectClean(problems)
    expect(
      mock.unmocked,
      `page called endpoints with no fixture: ${unmockedReport(mock)}`,
    ).toEqual([])
  })
}

test("an unknown path renders the in-app not-found page", async ({ page }) => {
  const problems = watchForProblems(page)
  await mockApi(page)

  await page.goto("/no-such-page")

  expect(await heading(page)).toBe("Page not found")
  await expect(page.getByText("/no-such-page")).toBeVisible()
  await expectNoErrorBoundary(page)
  expectClean(problems)
})
