const { test, expect } = require("@playwright/test");

test.skip(process.env.ROSALIND_DESKTOP_TEST !== "1", "Runs only against the local desktop sidecar");

test("desktop sidecar opens the shared app without Redis", async ({ browser }) => {
  const context = await browser.newContext({ locale: "zh-CN" });
  const page = await context.newPage();
  const email = `desktop-alpha-${Date.now()}@openrosalind.local`;

  const configResponse = await context.request.get("/api/config");
  expect(configResponse.ok()).toBe(true);
  expect((await configResponse.json()).desktopMode).toBe(true);

  await page.goto("/");
  await expect(page.locator("#authScreen")).toBeVisible();
  await page.locator("#registerMode").click();
  await page.locator("#authEmail").fill(email);
  await page.locator("#authPassword").fill("RosalindDesktopAlpha2026!");
  await page.locator("#authSubmit").click();

  await expect(page.locator("#appShell")).toBeVisible();
  await expect(page.locator("#desktopRuntime")).toBeVisible();
  await expect(page.locator("#desktopRuntime")).toHaveText("本地执行");

  const queueResponse = await context.request.get("/api/queue/status");
  expect(queueResponse.ok()).toBe(true);
  const queue = await queueResponse.json();
  expect(queue.queue).toBe("local-desktop");
  expect(queue.redis).toBe("not-required");

  const executionResponse = await context.request.post("/api/execute/python", {
    data: {
      confirmed: true,
      code: "from pathlib import Path\nPath('desktop-alpha.txt').write_text('local execution', encoding='utf-8')\nprint('desktop python ready')"
    }
  });
  expect(executionResponse.ok()).toBe(true);
  const execution = await executionResponse.json();
  expect(execution.ok).toBe(true);
  expect(execution.stdout).toContain("desktop python ready");
  expect(execution.audit.image).toBe("host-python");
  expect(execution.audit.network).toBe("host");
  expect(execution.files).toHaveLength(1);

  const outputResponse = await context.request.get(execution.files[0].url);
  expect(outputResponse.ok()).toBe(true);
  expect(await outputResponse.text()).toBe("local execution");

  await context.close();
});
