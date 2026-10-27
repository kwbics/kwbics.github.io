const path = require("node:path");
const fs = require("node:fs");
const { defineConfig } = require("@playwright/test");

const root = path.resolve(__dirname, "..");
const manifest = path.join(root, "output/site/site-manifest.json");
if (!fs.existsSync(manifest)) throw new Error("Run npm run check:site before responsive tests.");

module.exports = defineConfig({
  testDir: __dirname,
  testMatch: "site_ui.spec.js",
  timeout: 60000,
  expect: { timeout: 10000 },
  workers: 2,
  retries: 0,
  outputDir: path.join(root, "output/site/test-results"),
  reporter: [["line"], ["html", { open: "never", outputFolder: path.join(root, "output/site/playwright-report") }]],
  use: {
    browserName: "chromium",
    baseURL: "http://127.0.0.1:4444",
    screenshot: { mode: "only-on-failure", fullPage: true },
    trace: "retain-on-failure",
  },
  webServer: {
    command: "bin/site preview --port 4444",
    cwd: root,
    url: "http://127.0.0.1:4444/",
    reuseExistingServer: false,
    timeout: 30000,
  },
  projects: [
    { name: "desktop", use: { viewport: { width: 1280, height: 900 } } },
    { name: "mobile", use: { viewport: { width: 375, height: 812 }, isMobile: true, hasTouch: true } },
    { name: "narrow", use: { viewport: { width: 320, height: 740 }, isMobile: true, hasTouch: true } },
  ],
});
