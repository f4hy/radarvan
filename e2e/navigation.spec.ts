import { expect, type Page, test } from "@playwright/test"
import { expectClean, heading, watchForProblems } from "./harness"
import { playerProfile } from "./fixtures"
import { mockApi } from "./mockApi"

/**
 * The router's contract with the outside world.
 *
 * Most of this exists because the app spent years routing on `?page=`, and those
 * links were built to be pasted into chat — so they are still in Discord
 * scrollback and have to keep resolving. The rest is the reason paths replaced
 * that scheme: a page you can link to is only useful if the link is a real one.
 */

test.describe("links already pasted into chat still work", () => {
  test("?page= redirects to the path form, carrying its params", async ({
    page,
  }) => {
    await mockApi(page)
    await page.goto("/?page=game-night&date=2026-08-28")
    await expect(page).toHaveURL("/game-night?date=2026-08-28")
    expect(await heading(page)).toBe("Game Night")
  })

  test("a two-parameter link survives intact", async ({ page }) => {
    await mockApi(page)
    await page.goto("/?page=head-to-head&player1=Skip&player2=CoreDawg")
    await expect(page).toHaveURL("/head-to-head?player1=Skip&player2=CoreDawg")
  })

  test("a retired ?page= value lands on the default page, not an error", async ({
    page,
  }) => {
    // Someone else wrote the link; a renamed slug is likelier than a typo, and
    // a not-found screen would be a dead end for a visitor who did nothing wrong.
    await mockApi(page)
    await page.goto("/?page=some-page-we-renamed")
    await expect(page).toHaveURL(/\/game-night(\?|$)/)
  })

  test("the bare root goes to the default page", async ({ page }) => {
    await mockApi(page)
    await page.goto("/")
    await expect(page).toHaveURL(/\/game-night(\?|$)/)
  })

  test("the legacy URL is replaced, not pushed, so Back doesn't re-redirect", async ({
    page,
  }) => {
    await mockApi(page)
    await page.goto("/team-stats")
    await page.goto("/?page=map-stats")
    await expect(page).toHaveURL("/map-stats")
    await page.goBack()
    await expect(page).toHaveURL("/team-stats")
  })
})

test.describe("navigation is real links", () => {
  test("sidebar items are anchors with hrefs", async ({ page }) => {
    await mockApi(page)
    await page.goto("/matches")
    const links = page.locator("nav a[href]")
    expect(await links.count()).toBeGreaterThan(5)
    // A real href is what makes ⌘-click and "copy link address" work; an
    // onClick handler on a ListItemButton offers neither.
    await expect(page.locator('nav a[href="/game-night"]')).toBeVisible()
  })

  test("player names are anchors to their profile", async ({ page }) => {
    await mockApi(page)
    await page.goto("/team-stats")
    const chips = page.locator('a[href^="/player-profile?player="]')
    await expect(chips.first()).toBeVisible()
    expect(await chips.first().evaluate((el) => el.tagName)).toBe("A")
  })
})

test.describe("the URL is the state", () => {
  test("picking a different player from a chip changes the page", async ({
    page,
  }) => {
    // This was broken before the URL became the single copy: the chip pushed a
    // new ?player= and the component kept rendering the old one, because its
    // state was seeded from the URL once at mount.
    const problems = watchForProblems(page)
    // Skip's profile names CoreDawg as their nemesis, so there is a link to
    // another player on the page you are already on.
    await mockApi(page, {
      "/api/player_profile/": playerProfile("Skip", "CoreDawg").body,
    })
    await page.goto("/player-profile?player=Skip")
    await page
      .locator('a[href="/player-profile?player=CoreDawg"]')
      .first()
      .click()
    await expect(page).toHaveURL("/player-profile?player=CoreDawg")
    expectClean(problems)
  })

  test("Back returns to the previous player", async ({ page }) => {
    await mockApi(page, {
      "/api/player_profile/": playerProfile("Skip", "CoreDawg").body,
    })
    await page.goto("/player-profile?player=Skip")
    await page
      .locator('a[href="/player-profile?player=CoreDawg"]')
      .first()
      .click()
    await expect(page).toHaveURL("/player-profile?player=CoreDawg")
    await page.goBack()
    await expect(page).toHaveURL("/player-profile?player=Skip")
  })
})

test.describe("a match has its own page", () => {
  test("an unknown ID says so instead of erroring", async ({ page }) => {
    const problems = watchForProblems(page)
    // The server answers an unknown ID with 200 and `null`.
    await mockApi(page, { "/api/match/": null })
    await page.goto("/match/999")
    expect(await heading(page)).toBe("Match")
    await expect(page.getByText("There's no match with ID")).toBeVisible()
    await expect(page.locator("header")).toContainText("Match")
    expectClean(problems)
  })

  test("a non-numeric ID never reaches the server", async ({ page }) => {
    const mock = await mockApi(page)
    await page.goto("/match/abc")
    await expect(page.getByText("There's no match with ID")).toBeVisible()
    expect(mock.calls.filter((p) => p.startsWith("/api/match/"))).toEqual([])
  })
})

test.describe("page views are reported", () => {
  // A view is entering a route. Query-only changes never count, whoever makes
  // them: the page writing its own default, the visitor picking another night,
  // a highlight focusing a game, a filter. See usePageViewBeacon.
  async function recordViews(page: Page): Promise<unknown[]> {
    const views: unknown[] = []
    page.on("request", (req) => {
      if (new URL(req.url()).pathname === "/api/page_view") {
        views.push(req.postDataJSON())
      }
    })
    return views
  }

  test("entering a route is one view, carrying where it came from", async ({
    page,
  }) => {
    await mockApi(page)
    const views = await recordViews(page)
    // "/" redirects to Game Night, which then writes ?date= in itself.
    await page.goto("/")
    await expect(page).toHaveURL(/\/game-night\?date=/)
    await page.locator('nav a[href="/team-stats"]').first().click()
    await expect(page).toHaveURL("/team-stats")
    await expect.poll(() => views.length).toBe(2)
    expect(views).toEqual([
      { path: "/game-night", query: "", referrer: null },
      { path: "/team-stats", query: "", referrer: "/game-night" },
    ])
  })

  test("changing nights or focusing a game is not a new view", async ({
    page,
  }) => {
    await mockApi(page)
    const views = await recordViews(page)
    await page.goto("/game-night?date=2026-08-29")
    await expect(page.getByText("Match of the night")).toBeVisible()
    await page.getByRole("button", { name: "Older night" }).click()
    await expect(page).toHaveURL(/date=2026-08-28/)
    await page.locator('[title="Show this game below"]').first().click()
    await expect(page).toHaveURL(/match=/)
    // Leave, so the assertion can't pass merely by checking too early.
    await page.locator('nav a[href="/team-stats"]').first().click()
    await expect.poll(() => views.length).toBe(2)
    expect(views[0]).toEqual({
      path: "/game-night",
      query: "date=2026-08-29",
      referrer: null,
    })
  })

  test("a filter is not a new view", async ({ page }) => {
    await mockApi(page)
    const views = await recordViews(page)
    await page.goto("/matches")
    await page.getByRole("button", { name: "2v2" }).click()
    await expect(page).toHaveURL(/format=2v2/)
    await page.locator('nav a[href="/team-stats"]').first().click()
    await expect.poll(() => views.length).toBe(2)
    expect(views.map((v) => (v as { path: string }).path)).toEqual([
      "/matches",
      "/team-stats",
    ])
  })

  test("API calls carry the page that made them", async ({ page }) => {
    await mockApi(page)
    const pages = new Set<string>()
    page.on("request", (req) => {
      if (new URL(req.url()).pathname === "/api/team_stats/") {
        pages.add(req.headers()["x-radarvan-page"] ?? "")
      }
    })
    await page.goto("/team-stats")
    await expect.poll(() => [...pages]).toEqual(["/team-stats"])
  })

  test("every API call from one browser carries the same visitor id", async ({
    page,
  }) => {
    await mockApi(page)
    const visitors = new Set<string>()
    page.on("request", (req) => {
      if (new URL(req.url()).pathname.startsWith("/api/")) {
        visitors.add(req.headers()["x-radarvan-visitor"] ?? "missing")
      }
    })
    await page.goto("/team-stats")
    await page.reload()
    await page.locator('nav a[href="/matches"]').first().click()
    await expect(page).toHaveURL("/matches")
    expect(visitors.size).toBe(1)
    expect([...visitors][0]).toMatch(/^[0-9a-f-]{36}$/)
  })
})
