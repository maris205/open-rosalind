const { defineConfig } = require("@playwright/test");

module.exports = defineConfig({
  testDir: "./tests/web",
  fullyParallel: false,
  timeout: 120_000,
  expect: {
    timeout: 15_000
  },
  retries: 0,
  reporter: [["list"], ["html", { open: "never" }]],
  use: {
    baseURL: process.env.ROSALIND_WEB_BASE_URL || "https://openrosalind.bio",
    headless: true,
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure"
  }
});
