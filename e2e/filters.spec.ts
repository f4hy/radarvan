import { expect, test } from "@playwright/test"
import { expectClean, expectNoErrorBoundary, watchForProblems } from "./harness"
import { mockApi } from "./mockApi"

/**
 * Filters live in the URL, and the four consequences of that.
 *
 * Every control on these pages used to be `useState`, which made a filtered
 * view the one thing on the site you couldn't send anyone: the link you copied
 * was the unfiltered page. Reload lost it too, and Back left the page.
 *
 * The tests are grouped by the property rather than by page, because the point
 * is that all of them hold for every control — a new filter that only satisfies
 * some of them is the regression worth catching.
 */

test.describe("choosing a filter puts it in the URL", () => {
  test("a format toggle names itself, and the default names nothing", async ({
    page,
  }) => {
    const problems = watchForProblems(page)
    await mockApi(page)
    await page.goto("/game-length")

    // The default is absent on purpose: a URL that spelled out every default
    // would be mostly noise, and the parts that differ are the parts worth
    // sending. See useUrlState.
    await expect(page).toHaveURL("/game-length")

    await page.getByRole("button", { name: "3v3", exact: true }).click()
    await expect(page).toHaveURL("/game-length?format=3v3")

    // ...and going back to the default clears it rather than pinning "All".
    await page.getByRole("button", { name: "All", exact: true }).click()
    await expect(page).toHaveURL("/game-length")
    expectClean(problems)
  })

  test("two filters on one page both survive", async ({ page }) => {
    await mockApi(page)
    await page.goto("/game-length")
    await page.getByRole("button", { name: "2v2", exact: true }).click()
    await page.getByRole("button", { name: "5 min bars" }).click()

    const url = new URL(page.url())
    expect(url.searchParams.get("format")).toBe("2v2")
    expect(url.searchParams.get("bars")).toBe("5")
  })
})

test.describe("a filtered URL is the filtered page", () => {
  test("the control opens on the value the link named", async ({ page }) => {
    const problems = watchForProblems(page)
    await mockApi(page)
    await page.goto("/game-length?format=2v2&bars=5")

    await expect(
      page.getByRole("button", { name: "2v2", exact: true }),
    ).toHaveAttribute("aria-pressed", "true")
    await expect(
      page.getByRole("button", { name: "5 min bars" }),
    ).toHaveAttribute("aria-pressed", "true")
    expectClean(problems)
  })

  test("and the server is asked for it", async ({ page }) => {
    // The half that a rendered-control assertion can't see: a page can show the
    // right toggle while querying the unfiltered endpoint.
    const mock = await mockApi(page)
    await page.goto("/game-length?format=2v2&bars=5")
    await page.waitForLoadState("networkidle")

    const asked = mock.urls.filter((u) =>
      u.startsWith("/api/duration_distribution"),
    )
    expect(asked.length).toBeGreaterThan(0)
    expect(asked.at(-1)).toContain("game_format=2v2")
    expect(asked.at(-1)).toContain("bucket_minutes=5")
  })
})

test("Back undoes a filter instead of leaving the page", async ({ page }) => {
  await mockApi(page)
  await page.goto("/game-length")
  await page.getByRole("button", { name: "2v2", exact: true }).click()
  await expect(page).toHaveURL("/game-length?format=2v2")

  await page.goBack()
  await expect(page).toHaveURL("/game-length")
  await expect(
    page.getByRole("button", { name: "All", exact: true }),
  ).toHaveAttribute("aria-pressed", "true")
})

test.describe("a URL is untrusted input", () => {
  test("an unknown choice falls back instead of reaching the server", async ({
    page,
  }) => {
    // `format` goes out as an API query parameter, so this is validation, not
    // tidiness — and the fallback has to be silent, because the visitor pasting
    // a stale link did nothing wrong.
    const problems = watchForProblems(page)
    const mock = await mockApi(page)
    await page.goto("/game-length?format=9v9&bars=nonsense")
    await page.waitForLoadState("networkidle")

    await expect(
      page.getByRole("button", { name: "All", exact: true }),
    ).toHaveAttribute("aria-pressed", "true")
    const asked = mock.urls.filter((u) =>
      u.startsWith("/api/duration_distribution"),
    )
    expect(
      asked.join(" "),
      "the bad value must not be forwarded",
    ).not.toContain("9v9")
    // Two minutes is the default bucket, so an unparseable one lands there.
    expect(asked.at(-1)).toContain("bucket_minutes=2")
    await expectNoErrorBoundary(page)
    expectClean(problems)
  })

  test("a valid id is fetched", async ({ page }) => {
    // The control for the test below: without it, that one passes on any typo
    // in the endpoint path, since nothing would ever match it.
    const mock = await mockApi(page)
    await page.goto("/superlatives?match=12345")
    await page.waitForLoadState("networkidle")

    expect(mock.calls).toContain("/api/match/12345")
  })

  test("a garbage id selects nothing rather than being fetched", async ({
    page,
  }) => {
    const mock = await mockApi(page)
    await page.goto("/superlatives?match=notanumber")
    await page.waitForLoadState("networkidle")

    expect(
      mock.calls.filter((p) => p.startsWith("/api/match/")),
      "a non-numeric id must not become a request path",
    ).toEqual([])
    await expectNoErrorBoundary(page)
  })
})

test.describe("the matches filter bar", () => {
  test("a link naming two filters asks the server for both", async ({
    page,
  }) => {
    const mock = await mockApi(page)
    await page.goto("/matches?player=Skip&format=2v2")
    await page.waitForLoadState("networkidle")

    const asked = mock.urls.filter((u) => u.startsWith("/api/dates"))
    expect(asked.at(-1)).toContain("player=Skip")
    expect(asked.at(-1)).toContain("game_format=2v2")
    await expectNoErrorBoundary(page)
  })

  test("Clear removes every filter, not just the last one written", async ({
    page,
  }) => {
    // The case useUrlPatch exists for, and the one a two-clicks-two-ticks test
    // can't reach: three keys written in a single tick, each *removing* one.
    // As three separate setters they would each start from this render's
    // params — so the last navigation would carry the two the others had just
    // deleted, and Clear would clear one filter out of three. Setting three
    // values looks fine under the same bug (each write lands on params that
    // already hold the rest), which is why this is the removal.
    const problems = watchForProblems(page)
    await mockApi(page)
    await page.goto("/matches?player=Skip&map=Tournament%20Desert&format=2v2")
    await expect(page.getByLabel("Player")).toHaveValue("Skip")

    await page.getByRole("button", { name: "Clear" }).click()

    await expect(page).toHaveURL("/matches")
    await expect(page.getByLabel("Player")).toHaveValue("")
    expectClean(problems)
  })
})

test.describe("the map a page is pointed at", () => {
  // `?map=` is the one link on Map Stats worth sending, and until now the one
  // it couldn't produce: clicking a general's best/worst badge expanded and
  // scrolled to a map while leaving the URL on the bare page.

  test("a link opens the map it names, past the min-games floor", async ({
    page,
  }) => {
    const problems = watchForProblems(page)
    await mockApi(page)
    // `thin desert` has 2 games, under the default floor of 10, so it isn't on
    // the page at all until the link pins it. That is the case the pin exists
    // for — a badge pointing at a map the floor is hiding.
    await page.goto("/map-stats?map=thin%20desert")

    const target = page.locator("#map-thin-desert")
    await expect(target).toBeVisible()
    await expect(target).toHaveClass(/Mui-expanded/)
    expectClean(problems)
  })

  test("without the link that map is hidden and closed", async ({ page }) => {
    // The control: otherwise the test above passes on a page that shows every
    // map expanded regardless.
    await mockApi(page)
    await page.goto("/map-stats")

    await expect(page.locator("#map-thin-desert")).toHaveCount(0)
    // The first three open by default, so a target outside that set is what
    // makes "expanded" mean the link did it.
    await expect(page.locator("#map-final-crusade")).not.toHaveClass(
      /Mui-expanded/,
    )
  })
})
