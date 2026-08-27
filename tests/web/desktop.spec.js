const { test, expect } = require("@playwright/test");

test.skip(process.env.ROSALIND_DESKTOP_TEST !== "1", "Runs only against the local desktop sidecar");

test("desktop sidecar opens the shared app without Redis", async ({ browser }) => {
  const context = await browser.newContext({ locale: "zh-CN" });
  const page = await context.newPage();
  const email = `desktop-alpha-${Date.now()}@openrosalind.local`;
  const desktopToken = process.env.OPENROSALIND_DESKTOP_TEST_TOKEN;

  await page.addInitScript(() => {
    window.__desktopArtifactInvocations = [];
    window.__desktopContainerReady = false;
    window.__desktopProjectAuthorization = null;
    window.__desktopWriteScenario = false;
    window.__desktopWriteRun = null;
    window.__desktopConfirmResult = true;
    window.__desktopBackups = [{
      fileName: "desktop-core-initial.db",
      createdAt: Date.now() - 1000,
      sizeBytes: 4096
    }];
    window.__TAURI__ = {
      dialog: {
        confirm: async () => window.__desktopConfirmResult
      },
      core: {
        invoke: async (command, args = {}) => {
          window.__desktopArtifactInvocations.push({ command, args });
          if (command === "desktop_credential_vault_status") return { backend: "Test Vault" };
          if (command === "desktop_data_backup_status") {
            return {
              available: true,
              backupDirectory: "/Users/tester/Library/Application Support/OpenRosalind/backups",
              backups: window.__desktopBackups
            };
          }
          if (command === "desktop_create_data_backup") {
            const backup = {
              fileName: `desktop-core-${Date.now()}.db`,
              createdAt: Date.now(),
              sizeBytes: 8192
            };
            window.__desktopBackups.unshift(backup);
            return backup;
          }
          if (command === "desktop_reveal_data_backups") return null;
          if (command === "desktop_restore_data_backup") {
            return {
              restoredBackup: args.fileName,
              safetyBackup: window.__desktopBackups[0]
            };
          }
          if (command === "desktop_container_capability") {
            return {
              installed: true,
              available: window.__desktopContainerReady,
              image: "docker.io/library/python@sha256:test",
              imageAvailable: window.__desktopContainerReady,
              reason: window.__desktopContainerReady
                ? null
                : "Docker Desktop is installed but its daemon is not running."
            };
          }
          if (command === "desktop_list_provider_profiles") {
            return [{
              id: "test-provider",
              isDefault: true,
              baseUrl: "https://example.invalid/v1",
              model: "test-model",
              hasCredential: false
            }];
          }
          if (command === "desktop_load_ui_chat_state") {
            const override = sessionStorage.getItem("__openRosalindDesktopChatLoadOverride");
            if (override) return JSON.parse(override);
            return JSON.parse(sessionStorage.getItem("__openRosalindDesktopChatState") || '{"activeChatId":"","chats":[]}');
          }
          if (command === "desktop_replace_ui_chat_state") {
            const snapshot = { activeChatId: args.activeChatId, chats: args.chats };
            sessionStorage.setItem("__openRosalindDesktopChatState", JSON.stringify(snapshot));
            return snapshot;
          }
          if (command === "desktop_get_project_directory_authorization") {
            return window.__desktopProjectAuthorization;
          }
          if (command === "desktop_authorize_project_directory") {
            window.__desktopProjectAuthorization = {
              projectId: args.projectId,
              displayName: "TP53-study",
              displayPath: "/Users/tester/Documents/TP53-study",
              read: true,
              write: true,
              available: true,
              persistence: "macos-path-policy",
              authorizedAt: Date.now(),
              updatedAt: Date.now()
            };
            return window.__desktopProjectAuthorization;
          }
          if (command === "desktop_reveal_project_directory") return null;
          if (command === "desktop_list_tool_runs") {
            return window.__desktopWriteRun ? [window.__desktopWriteRun] : [];
          }
          if (command === "desktop_revoke_project_directory") {
            window.__desktopProjectAuthorization = null;
            return true;
          }
          if (command === "desktop_run_low_risk_tool" && args.toolName === "project.files.list") {
            return {
              id: "project-list-run",
              status: "succeeded",
              output: {
                projectId: window.__desktopProjectAuthorization.projectId,
                files: [
                  { path: "README.md", sizeBytes: 25, kind: "text", readable: true },
                  { path: "data/variants.csv", sizeBytes: 120, kind: "text", readable: true }
                ],
                truncated: false
              }
            };
          }
          if (command === "desktop_run_low_risk_tool" && args.toolName === "project.file.read") {
            return {
              id: "project-read-run",
              status: "succeeded",
              output: {
                projectId: window.__desktopProjectAuthorization.projectId,
                path: args.input.path,
                content: "# TP53 study\nLocal project preview",
                sizeBytes: 34,
                truncated: false
              }
            };
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
          if (command === "desktop_create_conversation") return { id: "conversation-123" };
          if (command === "desktop_create_agent_job") return { id: "agent-job-123" };
          if (command === "desktop_start_agent_job") {
            if (window.__desktopWriteScenario) {
              window.__desktopWriteRun = {
                id: "project-write-run",
                toolName: "project.file.write",
                status: "awaiting_approval",
                input: { path: "notes/agent-result.md", content: "# Agent result\nVerified content." },
                permissionSnapshot: { filesystem: [{ scope: "project-root", mode: "write" }], network: "none", secrets: [] }
              };
              return { job: { id: "agent-job-123", status: "running" }, events: [] };
            }
            return {
              job: {
                id: "agent-job-123",
                status: "completed",
                result: {
                  content: "共有 3 个单词。",
                  model: "test-model",
                  toolRuns: [{
                    toolRunId: "automatic-tool-run-123",
                    toolName: "text.statistics",
                    status: "succeeded",
                    output: { words: 3 }
                  }]
                }
              },
              events: [
                { kind: "model_requested" },
                { kind: "tool_requested" },
                { kind: "tool_completed" },
                { kind: "completed" }
              ]
            };
          }
          if (command === "desktop_refresh_agent_job") {
            if (window.__desktopWriteRun?.status === "denied") {
              window.__desktopWriteScenario = false;
              return {
                job: {
                  id: "agent-job-123",
                  status: "completed",
                  result: {
                    content: "用户拒绝了项目文件写入，未修改文件。",
                    model: "test-model",
                    toolRuns: [{
                      toolRunId: "project-write-run",
                      toolName: "project.file.write",
                      status: "failed",
                      error: "project.file.write ended with status denied"
                    }]
                  }
                },
                events: [{ kind: "tool_requested" }, { kind: "tool_completed" }]
              };
            }
            if (window.__desktopWriteRun?.status === "succeeded") {
              window.__desktopWriteScenario = false;
              return {
                job: {
                  id: "agent-job-123",
                  status: "completed",
                  result: {
                    content: "项目文件已由 Desktop Core 写入。",
                    model: "test-model",
                    toolRuns: [{
                      toolRunId: "project-write-run",
                      toolName: "project.file.write",
                      status: "succeeded",
                      output: { path: "notes/agent-result.md", rollbackArtifact: false }
                    }]
                  }
                },
                events: [{ kind: "tool_requested" }, { kind: "tool_completed" }]
              };
            }
            return { job: { id: "agent-job-123", status: "running" }, events: [] };
          }
          if (command === "desktop_propose_tool_run") {
            return {
              id: "tool-run-123",
              permissionSnapshot: {
                filesystem: [{ scope: "host", mode: "read-write" }],
                network: "host",
                secrets: []
              }
            };
          }
          if (command === "desktop_decide_tool_run") {
            if (typeof args.approved !== "boolean") throw new Error("approved must be a boolean");
            if (args.toolRunId === "project-write-run") {
              window.__desktopWriteRun.status = args.approved ? "approved" : "denied";
            }
            return { id: args.toolRunId, status: args.approved ? "approved" : "denied" };
          }
          if (command === "desktop_execute_approved_project_write") {
            window.__desktopWriteRun.status = "succeeded";
            window.__desktopWriteRun.output = { path: "notes/agent-result.md", rollbackArtifact: false };
            return window.__desktopWriteRun;
          }
          if (command === "desktop_execute_approved_python_tool") {
            return {
              id: args.toolRunId,
              status: "succeeded",
              output: {
                ok: true,
                status: "succeeded",
                jobId: "native-python-123",
                stdout: "sandbox",
                files: []
              }
            };
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

  await page.locator("#sidebarAccount").click();
  await page.locator("#openSettings").click();
  await expect(page.locator("#desktopDataBackupSection")).toBeVisible();
  await expect(page.locator("#desktopDataBackupStatus")).toContainText("已有 1 份已验证备份");
  await page.locator("#createDesktopDataBackup").click();
  await expect(page.locator("#desktopDataBackupStatus")).toContainText("已有 2 份已验证备份");
  await page.locator("#revealDesktopDataBackups").click();
  await expect.poll(() => page.evaluate(() => window.__desktopArtifactInvocations
    .filter((item) => item.command === "desktop_reveal_data_backups").length)).toBe(1);
  await page.locator("#restoreDesktopDataBackup").click();
  await expect.poll(() => page.evaluate(() => window.__desktopArtifactInvocations
    .filter((item) => item.command === "desktop_restore_data_backup").length)).toBe(1);
  await expect(page.locator("#desktopDataBackupStatus")).toContainText("客户端正在重启");
  await page.locator('#settingsDialog button[value="cancel"]').click();

  await page.locator("#sidebarAccount").click();
  await page.locator("#openProject").click();
  await expect(page.locator("#projectDialog")).toBeVisible();
  await expect(page.locator("#projectDirectoryStatus")).toContainText("尚未授权目录");
  await page.locator("#authorizeProjectDirectory").click();
  await expect(page.locator("#projectDirectoryStatus")).toContainText("已授权读取和写入");
  await expect(page.locator("#projectDirectoryPath")).toHaveText("/Users/tester/Documents/TP53-study");
  await page.locator("#revealProjectDirectory").click();
  await expect.poll(() => page.evaluate(() => window.__desktopArtifactInvocations
    .filter((item) => item.command === "desktop_reveal_project_directory").length)).toBe(1);
  await page.locator("#scanProjectFiles").click();
  await expect(page.locator("#projectFilesStatus")).toContainText("已发现 2 个非敏感文件");
  await expect(page.locator("#projectFileList")).toContainText("data/variants.csv");
  await page.locator("#projectFileList article").filter({ hasText: "README.md" }).getByRole("button", { name: "预览" }).click();
  await expect(page.locator("#projectFileList article").filter({ hasText: "README.md" }).locator("pre"))
    .toContainText("Local project preview");
  await page.locator("#revokeProjectDirectory").click();
  await expect(page.locator("#projectDirectoryStatus")).toContainText("尚未授权目录");
  await page.locator("#projectDialog [aria-label='关闭']").click();

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
    const saved = JSON.parse(sessionStorage.getItem("__openRosalindDesktopChatState"));
    const chat = saved.chats.find((item) => item.id === saved.activeChatId);
    chat.messages.push({
      id: "desktop-tool-artifact",
      role: "assistant",
      content: "Python 生成了一个本地产物。\n\n```python\nprint('sandbox')\n```",
      toolArtifacts: [{
        artifactId: "artifact-123",
        name: "result.txt",
        size: 36,
        sha256: "a".repeat(64),
        kind: "text"
      }]
    });
    sessionStorage.setItem("__openRosalindDesktopChatLoadOverride", JSON.stringify(saved));
  });
  await page.reload();
  const artifactMessage = page.locator(".message.assistant").last();
  await expect(artifactMessage.getByRole("button", { name: "运行 Python" })).toBeVisible();
  await expect(artifactMessage.getByRole("button", { name: "Docker 未就绪" })).toBeDisabled();
  await page.evaluate(() => {
    window.__desktopContainerReady = true;
    window.dispatchEvent(new Event("focus"));
  });
  await expect(artifactMessage.getByRole("button", { name: "Docker 沙箱" })).toBeEnabled();
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

  await page.locator("#closeDetailPanel").click();
  await artifactMessage.getByRole("button", { name: "运行 Python" }).click();
  await expect(page.locator(".message.assistant").last()).toContainText("Python 本地执行结果");
  const approval = await page.evaluate(() => window.__desktopArtifactInvocations
    .find((item) => item.command === "desktop_decide_tool_run"));
  expect(approval.args).toEqual({ toolRunId: "tool-run-123", approved: true });

  await page.locator("#taskInput").fill("统计 a b c 的单词数");
  await page.locator("#sendButton").click();
  const agentAnswer = page.locator(".message.assistant").last();
  await expect(agentAnswer).toContainText("共有 3 个单词");
  await expect(agentAnswer.getByRole("button", { name: "查看 Agent 执行过程" })).toBeVisible();
  await agentAnswer.getByRole("button", { name: "查看 Agent 执行过程" }).click();
  await expect(page.locator("#detailPanelTitle")).toHaveText("执行过程 (1)");
  await expect(page.locator("#detailPanelContent")).toContainText("text.statistics");

  await page.evaluate(() => { window.__desktopWriteScenario = true; });
  await page.locator("#taskInput").fill("在当前项目创建 notes/agent-result.md");
  await page.locator("#sendButton").click();
  await expect(page.locator(".message.assistant").last()).toContainText("项目文件已由 Desktop Core 写入");
  await expect.poll(() => page.evaluate(() => window.__desktopArtifactInvocations
    .filter((item) => item.command === "desktop_execute_approved_project_write").length)).toBe(1);

  await page.evaluate(() => {
    window.__desktopWriteScenario = true;
    window.__desktopConfirmResult = false;
  });
  await page.locator("#taskInput").fill("在当前项目创建 notes/denied.md");
  await page.locator("#sendButton").click();
  await expect(page.locator(".message.assistant").last()).toContainText("用户拒绝了项目文件写入");
  await expect.poll(() => page.evaluate(() => window.__desktopArtifactInvocations
    .filter((item) => item.command === "desktop_execute_approved_project_write").length)).toBe(1);
  const deniedDecision = await page.evaluate(() => window.__desktopArtifactInvocations
    .filter((item) => item.command === "desktop_decide_tool_run").at(-1));
  expect(deniedDecision.args).toEqual({ toolRunId: "project-write-run", approved: false });

  await context.close();
});
