const { test, expect } = require("@playwright/test");

test("HTTP redirects to HTTPS", async ({ page }) => {
  await page.goto("http://openrosalind.bio/");
  await expect(page).toHaveURL("https://openrosalind.bio/");
});

test("Chinese browser receives the Chinese landing page", async ({ browser }) => {
  const context = await browser.newContext({ locale: "zh-CN" });
  const page = await context.newPage();
  await page.goto("/");

  await expect(page).toHaveTitle("Open-Rosalind · 生物医学科研智能体");
  await expect(page.getByRole("link", { name: "为什么选择我们" })).toBeVisible();
  await expect(page.getByText("提出生物学问题。")).toBeVisible();
  await expect(page.getByRole("link", { name: "进入工作台 →" }).first()).toHaveAttribute("href", "/app");

  await context.close();
});

test("Non-Chinese browser receives the English landing page", async ({ browser }) => {
  const context = await browser.newContext({ locale: "en-US" });
  const page = await context.newPage();
  await page.goto("/");

  await expect(page).toHaveTitle("Open-Rosalind · Biomedical Research Agent");
  await expect(page.getByRole("link", { name: "Why" })).toBeVisible();
  await expect(page.getByText("Ask biology.")).toBeVisible();
  await expect(page.getByRole("link", { name: "Launch App →" })).toHaveAttribute("href", "/app");

  await context.close();
});
