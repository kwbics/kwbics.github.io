// CI-runner browser checks only. Local interactive verification is performed separately.
const fs = require("node:fs");
const path = require("node:path");
const { test, expect } = require("@playwright/test");
const manifest = JSON.parse(fs.readFileSync(path.join(__dirname, "../output/site/site-manifest.json"), "utf8"));
const routeFor = (source) => {
  const page = manifest.pages.find((item) => item.source === source);
  if (!page) throw new Error(`Required public page missing from source manifest: ${source}`);
  return page.route;
};

async function noOverflow(page) {
  await expect.poll(() => page.evaluate(() => document.documentElement.scrollWidth - document.documentElement.clientWidth)).toBeLessThanOrEqual(1);
}

for (const item of manifest.pages.filter((item) => item.route !== "/404.html")) {
  test(`renders ${item.route} with responsive navigation and images`, async ({ page }) => {
    const response = await page.goto(item.route);
    expect(response.status()).toBe(200);
    await expect(page.locator("[role=main], main").first()).toBeVisible();
    await expect(page.locator("#navbar")).toBeVisible();
    // Scroll to load lazy member/profile images before testing their natural size.
    for (const image of await page.locator("main img, [role=main] img").all()) {
      await image.scrollIntoViewIfNeeded();
      await expect.poll(() => image.evaluate((img) => img.complete && img.naturalWidth > 0)).toBeTruthy();
    }
    await page.evaluate(() => window.scrollTo(0, 0));
    await noOverflow(page);
  });
}

test("menu opens, closes, and navigates to members", async ({ page }, info) => {
  await page.goto("/");
  const toggle = page.getByRole("button", { name: "Toggle navigation" });
  if (info.project.name !== "desktop") {
    await expect(toggle).toBeVisible();
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "true");
    await toggle.click();
    await expect(toggle).toHaveAttribute("aria-expanded", "false");
    await toggle.click();
  }
  for (const item of manifest.navigation) {
    await expect(page.locator(`#navbar a[href="${manifest.baseurl}${item.route}"]`).first()).toBeVisible();
  }
  await page
    .locator(`#navbar a[href="${manifest.baseurl}${routeFor("_pages/profiles.md")}"]`)
    .first()
    .click();
  await expect(page).toHaveURL(new RegExp(`${routeFor("_pages/profiles.md")}$`));
  await expect(page.locator(".bics-roster").first()).toBeVisible();
  const photos = page.locator("img.bics-member-photo");
  expect(await photos.count()).toBeGreaterThan(0);
  for (const photo of await photos.all()) await expect(photo).toHaveAttribute("alt", /\S/);
  await noOverflow(page);
});

test("publication filter uses rendered data and restores entries", async ({ page }) => {
  await page.goto(routeFor("_pages/publications.md"));
  const entries = page.locator("ol.bibliography > li");
  await expect(entries).toHaveCount(manifest.publications.length);
  const title = (await entries.first().locator(".title").innerText()).trim();
  const search = page.locator("#bibsearch");
  await search.fill(title.toLowerCase());
  await expect.poll(() => page.locator("ol.bibliography > li:not(.unloaded)").count()).toBeGreaterThan(0);
  await expect(entries.first()).not.toHaveClass(/unloaded/);
  await search.fill("bics-no-publication-matches-this-search-9f84d2");
  await expect(page.locator("ol.bibliography > li:not(.unloaded)")).toHaveCount(0);
  await search.fill("");
  await expect(page.locator("ol.bibliography > li:not(.unloaded)")).toHaveCount(manifest.publications.length);
  await noOverflow(page);
});
