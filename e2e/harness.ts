import { expect, type Page } from "@playwright/test"

/**
 * Collects the things a passing-looking page can still be doing wrong.
 *
 * A Playwright assertion only checks what it was told to look at, so a page can
 * render its heading perfectly while throwing in a chart below the fold. Every
 * spec installs this and asserts it is empty, which is what turns "the h1 says
 * Matches" into "the page rendered without incident".
 */
export interface PageProblems {
  consoleErrors: string[]
  pageErrors: string[]
}

export function watchForProblems(page: Page): PageProblems {
  const problems: PageProblems = { consoleErrors: [], pageErrors: [] }
  page.on("console", (msg) => {
    if (msg.type() === "error") problems.consoleErrors.push(msg.text())
  })
  page.on("pageerror", (err) => problems.pageErrors.push(err.message))
  return problems
}

export function expectClean(problems: PageProblems) {
  expect(problems.pageErrors, "uncaught exceptions").toEqual([])
  expect(problems.consoleErrors, "console errors").toEqual([])
}

/**
 * The routed page did not fall into its error boundary.
 *
 * Worth asserting separately from the console: a caught render error is handled
 * — React logs it, the boundary draws a panel, the shell survives — so a test
 * that only waits for an `<h1>` can pass on the frame before the throw and go
 * green on a page that is actually broken. That happened while writing this
 * suite, and this is the check that caught it.
 */
export async function expectNoErrorBoundary(page: Page) {
  await expect(page.getByText("Something went wrong in this page")).toHaveCount(
    0,
  )
}

/** Wait for the routed page to have settled onto its heading. */
export async function heading(page: Page): Promise<string> {
  const h1 = page.locator("h1").first()
  await h1.waitFor({ state: "visible" })
  return (await h1.textContent()) ?? ""
}
