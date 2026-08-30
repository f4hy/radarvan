import { expect, test } from "@playwright/test"
import { mockApi } from "./mockApi"

/**
 * Keyboard operability of the things that aren't ordinary buttons.
 *
 * The activity calendar is the case worth a test: it is an `<svg>`, so it can't
 * use a real `<button>`, and its first accessible version *looked* right —
 * role, tabIndex, aria-label, an onKeyDown — while doing nothing on Enter,
 * because the calendar library clones the returned element and spreads its own
 * props over the top. Nothing but pressing the key finds that.
 */

test("the activity calendar is operable by keyboard", async ({ page }) => {
  await mockApi(page)
  await page.goto("/game-night")

  await page.getByRole("button", { name: /All nights/i }).click()

  const cells = page.locator('svg g[role="button"]')
  await expect(cells.first()).toBeVisible()

  // Wait for the tooltip chunk to land before testing the key, and do not remove
  // this. react-activity-calendar renders
  // `<Suspense fallback={renderedBlock}>` around a lazily-loaded Tooltip, so
  // until that chunk lands the *uncloned* element is on screen with its handlers
  // intact — and only afterwards does cloneElement spread floating-ui's props
  // over them. The chunk is a network request, so settling on it is what makes
  // this deterministic — without the wait the test passes against a calendar
  // whose keyboard support breaks a few hundred milliseconds later, which is
  // exactly the bug it exists for.
  await page.waitForLoadState("networkidle")

  const first = cells.first()
  await expect(first).toHaveAttribute("tabindex", "0")
  // Screen readers get the count and the date, not "group".
  await expect(first).toHaveAttribute(
    "aria-label",
    /\d+ games? on \d{4}-\d{2}-\d{2}/,
  )

  // Deliberately a night other than the one already selected. Picking whichever
  // cell came first made the assertion trivially true when that cell *was* the
  // current night — the test then passed against a calendar with no working key
  // handler at all, which is how this was caught.
  const current = new URL(page.url()).searchParams.get("date")
  expect(current, "the page should have landed on a night").toBeTruthy()

  const labels = await cells.evaluateAll((els) =>
    els.map((e) => e.getAttribute("aria-label") ?? ""),
  )
  const otherIndex = labels.findIndex(
    (l) => l.includes("on ") && !l.includes(current as string),
  )
  expect(
    otherIndex,
    "need a second playable night to switch to",
  ).toBeGreaterThanOrEqual(0)
  const date = labels[otherIndex].match(/(\d{4}-\d{2}-\d{2})/)?.[1]

  await cells.nth(otherIndex).focus()
  // Focus alone must not select — otherwise the assertion below would pass on a
  // calendar whose key handler does nothing.
  await expect(page).toHaveURL(new RegExp(`date=${current}`))

  await page.keyboard.press("Enter")

  // Activating a night selects it — the same thing a click does.
  await expect(page).toHaveURL(new RegExp(`date=${date}`))
})

test("nights with no games are not keyboard targets", async ({ page }) => {
  // Only two nights in the fixtures have games, so most cells are empty. An
  // empty cell offering a tab stop would make the calendar 400 stops of nothing.
  await mockApi(page)
  await page.goto("/game-night")
  await page.getByRole("button", { name: /All nights/i }).click()

  const playable = page.locator('svg g[role="button"]')
  await expect(playable.first()).toBeVisible()
  const playableCount = await playable.count()
  const allCells = await page.locator("svg g rect[data-date]").count()

  expect(playableCount).toBeGreaterThan(0)
  expect(
    playableCount,
    "only nights with games should be focusable",
  ).toBeLessThan(allCells)
})

test("the page has one h1 and a labelled nav", async ({ page }) => {
  await mockApi(page)
  await page.goto("/matches")

  await expect(page.getByRole("heading", { level: 1 })).toHaveCount(1)
  await expect(
    page.getByRole("navigation", { name: "Primary navigation" }),
  ).toBeVisible()
})
