import { expect, test } from "@playwright/test"
import { expectClean, watchForProblems } from "./harness"
import { MATCH_OF_THE_NIGHT_BLURB } from "./fixtures"
import { mockApi } from "./mockApi"

test("the match of the night card shows its written blurb", async ({
  page,
}) => {
  const problems = watchForProblems(page)
  await mockApi(page)
  await page.goto("/game-night?date=2026-08-28")
  await expect(page.getByText("Match of the night")).toBeVisible()
  await expect(page.getByText(MATCH_OF_THE_NIGHT_BLURB)).toBeVisible()
  expectClean(problems)
})

test("the match of the night is featured above the smaller cards", async ({
  page,
}) => {
  await mockApi(page)
  await page.goto("/game-night?date=2026-08-28")
  const featured = await page.getByText("Match of the night").boundingBox()
  const tile = await page.getByText("Longest game").boundingBox()
  if (!featured || !tile) throw new Error("both cards should be on the page")
  expect(featured.y).toBeLessThan(tile.y)
})
