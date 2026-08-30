import { expect, test } from "@playwright/test"
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
    await expect(page).toHaveURL("/matches")
  })

  test("the bare root goes to the default page", async ({ page }) => {
    await mockApi(page)
    await page.goto("/")
    await expect(page).toHaveURL("/matches")
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
