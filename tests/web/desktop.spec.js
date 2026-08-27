const { test, expect } = require("@playwright/test");

test.skip(process.env.ROSALIND_DESKTOP_TEST !== "1", "Runs only against the local desktop sidecar");

test("desktop sidecar opens the shared app without Redis", async ({ browser }) => {
  const context = await browser.newContext({ locale: "zh-CN" });
  const page = await context.newPage();
  const email = `desktop-alpha-${Date.now()}@openrosalind.local`;
  const desktopToken = process.env.OPENROSALIND_DESKTOP_TEST_TOKEN;

  await page.addInitScript(() => {
    window.__desktopArtifactInvocations = [];
    window.__TAURI__ = {
      core: {
        invoke: async (command, args = {}) => {
          window.__desktopArtifactInvocations.push({ command, args });
          if (command === "desktop_credential_vault_status") return { backend: "Test Vault" };
          if (command === "desktop_list_provider_profiles") {
            return [{
              id: "test-provider",
              isDefault: true,
              baseUrl: "https://example.invalid/v1",
              model: "test-model",
              hasCredential: false
            }];
          }
          if (command === "desktop_read_tool_artifact") {
            return {
              previewable: true,
              content: "artifact preview from Desktop Core",
              truncated: false
            };
          }
          if (command === "desktop_reveal_tool_artifact") return null;
          if (command === "desktop_export_tool_artifact") {
            return { fileName: "result.txt", sizeBytes: 36 };
          }
          throw new Error(`Unexpected desktop command: ${command}`);
        }
      }
    };
  });

  expect(desktopToken).toBeTruthy();
  await page.goto(`/desktop/bootstrap?token=${encodeURIComponent(desktopToken)}`);

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

  await page.evaluate(() => {
    const storageKey = Object.keys(localStorage).find((key) => key.startsWith("rosalind.chats."));
    const saved = JSON.parse(localStorage.getItem(storageKey));
    const chat = saved.chats.find((item) => item.id === saved.activeChatId);
    chat.messages.push({
      id: "desktop-tool-artifact",
      role: "assistant",
      content: "Python 生成了一个本地产物。",
      toolArtifacts: [{
        artifactId: "artifact-123",
        name: "result.txt",
        size: 36,
        sha256: "a".repeat(64),
        kind: "text"
      }]
    });
    localStorage.setItem(storageKey, JSON.stringify(saved));
  });
  await page.reload();
  const artifactMessage = page.locator(".message.assistant").last();
  await artifactMessage.getByRole("button", { name: "查看本地 ToolRun 产物" }).click();
  await expect(page.locator("#detailPanelTitle")).toHaveText("本地产物 (1)");
  await page.locator(".tool-artifact-card").getByRole("button", { name: "预览" }).click();
  await expect(page.locator(".tool-artifact-preview")).toHaveText("artifact preview from Desktop Core");
  await page.locator(".tool-artifact-card").getByRole("button", { name: "显示文件" }).click();
  await expect.poll(() => page.evaluate(() => window.__desktopArtifactInvocations
    .filter((item) => item.command === "desktop_reveal_tool_artifact").length)).toBe(1);
  await page.locator(".tool-artifact-card").getByRole("button", { name: "另存为" }).click();
  await expect(page.locator(".tool-artifact-card").getByRole("button", { name: "已保存" })).toBeVisible();
  await expect.poll(() => page.evaluate(() => window.__desktopArtifactInvocations
    .filter((item) => item.command === "desktop_export_tool_artifact").length)).toBe(1);

  await context.close();
});
