import { expect, test } from "@playwright/test"
import { heading } from "./harness"
import { mockApi } from "./mockApi"

/**
 * What the app does when something goes wrong, and what it does when nothing
 * has changed. Both used to be untested and both were wrong.
 */

test.describe("a failed read is shown, not swallowed", () => {
  test("shows the server's own message, with a retry", async ({ page }) => {
    // The old convention was `data === null means loading`, which had no room
    // for "failed": an errored request left the page in its skeleton forever,
    // and on four pages the early return sat above the snackbar that would have
    // reported it, so nobody ever saw the failure at all.
    // mockApi first: Playwright matches routes in reverse registration order,
    // so the catch-all has to be registered *before* the specific override or
    // it swallows it.
    await mockApi(page)
    await page.route("**/api/team_stats/**", (route) =>
      route.fulfill({
        status: 500,
        contentType: "application/json",
        body: JSON.stringify({ detail: "Simulated backend failure" }),
      }),
    )

    await page.goto("/team-stats")

    const alert = page.getByRole("alert")
    await expect(alert).toBeVisible()
    await expect(alert).toContainText("Couldn't load team stats")
    // FastAPI's `detail`, not the generated client's "Response returned an
    // error code" — see apiError.errorMessage.
    await expect(alert).toContainText("Simulated backend failure")
    await expect(page.getByRole("button", { name: /retry/i })).toBeVisible()
  })

  test("retry re-requests, and succeeds once the server recovers", async ({
    page,
  }) => {
    await mockApi(page)
    // Two failures, not one: the query client is configured with `retry: 1`, so
    // a single transient error is absorbed automatically and never reaches the
    // UI. Getting the panel to appear at all takes exhausting that retry —
    // which is itself a check that the retry is live.
    let failuresLeft = 2
    await page.route("**/api/team_stats/**", (route) => {
      if (failuresLeft > 0) {
        failuresLeft -= 1
        return route.fulfill({
          status: 503,
          contentType: "application/json",
          body: JSON.stringify({ detail: "Temporarily unavailable" }),
        })
      }
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({
          groups: [
            { size: 2, teams: [{ players: ["Skip"], wins: 1, losses: 0 }] },
          ],
        }),
      })
    })

    await page.goto("/team-stats")
    await expect(page.getByRole("alert")).toContainText(
      "Temporarily unavailable",
    )
    await page.getByRole("button", { name: /retry/i }).click()
    await expect(page.getByRole("alert")).toHaveCount(0)
    expect(await heading(page)).toBe("Team Stats")
  })

  test("a validation error names the field", async ({ page }) => {
    await mockApi(page)
    await page.route("**/api/team_stats/**", (route) =>
      route.fulfill({
        status: 422,
        contentType: "application/json",
        body: JSON.stringify({
          detail: [{ loc: ["query", "game_format"], msg: "Field required" }],
        }),
      }),
    )

    await page.goto("/team-stats")
    await expect(page.getByRole("alert")).toContainText(
      "game_format: Field required",
    )
  })
})

test("navigating back to a page serves it from cache", async ({ page }) => {
  // Before the query client, the router unmounting a page threw its data away,
  // so going away and back was a full refetch of something that had not changed.
  const mock = await mockApi(page)
  await page.goto("/team-stats")
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Team Stats")
  await page.waitForLoadState("networkidle")

  mock.calls.length = 0
  await page.locator('nav a[href="/map-stats"]').click()
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Map Stats")
  await page.locator('nav a[href="/team-stats"]').click()
  await expect(page.getByRole("heading", { level: 1 })).toHaveText("Team Stats")
  await page.waitForLoadState("networkidle")

  expect(
    mock.calls.filter((p) => p.startsWith("/api/team_stats")),
    "returning to a page inside staleTime must not refetch it",
  ).toEqual([])
})

test("a broken page keeps the rest of the app usable", async ({ page }) => {
  // There was no error boundary at all: one bad field on one card unmounted the
  // whole tree, nav included, and left a blank white page.
  await mockApi(page)
  await page.route("**/api/duration_distribution/**", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      // Well-formed enough to pass the converter, wrong enough to throw while
      // rendering — which is the class of bug a boundary exists for.
      body: JSON.stringify({ buckets: null, stats: null }),
    }),
  )

  await page.goto("/game-length")
  await expect(
    page.getByText("Something went wrong in this page"),
  ).toBeVisible()

  // The shell survived, so the visitor can leave.
  await page.locator('nav a[href="/team-stats"]').click()
  expect(await heading(page)).toBe("Team Stats")
  await expect(page.getByText("Something went wrong in this page")).toHaveCount(
    0,
  )
})
