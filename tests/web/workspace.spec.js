const { test, expect } = require("@playwright/test");

test("agent plan approval is inline and does not block the composer", async ({ browser }) => {
  const context = await browser.newContext({ locale: "zh-CN" });
  const page = await context.newPage();
  const email = `agent-approval-${Date.now()}@openrosalind.bio`;
  const password = "Rosalind-E2E-2026";
  const projectIdPattern = /\/api\/projects\/[a-f0-9-]{36}\/plans\/generate$/;
  const planIds = [
    "11111111-1111-4111-8111-111111111111",
    "22222222-2222-4222-8222-222222222222"
  ];
  let generatedCount = 0;
  let confirmCount = 0;
  let runCount = 0;
  let dialogCount = 0;
  let taskFinished = false;
  let projectId = "";

  page.on("dialog", async (dialog) => {
    dialogCount += 1;
    await dialog.dismiss();
  });
  await page.route(projectIdPattern, async (route) => {
    projectId = route.request().url().match(/\/api\/projects\/([a-f0-9-]{36})\/plans\/generate$/)[1];
    const planId = planIds[Math.min(generatedCount, planIds.length - 1)];
    generatedCount += 1;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        summary: "测试计划摘要",
        plan: {
          id: planId,
          goal: "分析三个基因",
          status: "draft",
          steps: [{
            id: "33333333-3333-4333-8333-333333333333",
            position: 1,
            title: "整理基因证据",
            instruction: "整理三个基因的功能和证据边界。",
            skill: "evidence-manager",
            status: "pending",
            attempts: 0,
            output: "",
            error: ""
          }]
        }
      })
    });
  });
  await page.route(/\/api\/plans\/[a-f0-9-]{36}\/confirm$/, async (route) => {
    confirmCount += 1;
    await route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify({ ok: true, plan: {} }) });
  });
  await page.route(/\/api\/plans\/[a-f0-9-]{36}\/run-all$/, async (route) => {
    runCount += 1;
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        task: { jobId: "a".repeat(32), status: "queued", planId: planIds[1], mode: "all" }
      })
    });
  });
  await page.route(/\/api\/tasks\/[a-f0-9]{32}\/status$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        task: {
          jobId: "a".repeat(32),
          status: taskFinished ? "finished" : "started",
          error: "",
          plan: {
            projectId,
            status: taskFinished ? "completed" : "running",
            steps: [{
              position: 1,
              title: "整理基因证据",
              skill: "evidence-manager",
              status: "completed",
              attempts: 1,
              output: "## 完成：OpenHands 测试结果\n\n报告保存至 `/workspace/project/final_report.md`。\n\n```python\nprint('process only')\n```",
              error: ""
            }]
          }
        }
      })
    });
  });
  await page.route(/\/api\/projects\/[a-f0-9-]{36}\/artifacts$/, async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        artifacts: [{
          name: "final_report.md",
          path: "final_report.md",
          size: 2048,
          mime: "text/markdown",
          modifiedAt: "2026-08-05T00:00:00+00:00",
          url: projectId ? `/api/projects/${projectId}/artifacts/final_report.md` : ""
        }]
      })
    });
  });

  await page.goto("/app");
  await page.locator("#registerMode").click();
  await page.locator("#authEmail").fill(email);
  await page.locator("#authPassword").fill(password);
  await page.locator("#authSubmit").click();
  await expect(page.locator("#appShell")).toBeVisible();

  await page.locator("#taskInput").fill("第一次计划：测试取消");
  await page.locator("#sendButton").click();
  const firstCard = page.locator(".agent-plan-approval").last();
  await expect(firstCard).toContainText("等待你的确认");
  await expect(page.locator("#taskInput")).toBeEnabled();
  await expect(page.locator("#sendButton")).toBeEnabled();
  await firstCard.getByRole("button", { name: "取消" }).click();
  await expect(firstCard).toContainText("已取消");
  expect(confirmCount).toBe(0);
  expect(runCount).toBe(0);

  await page.locator("#taskInput").fill("第二次计划：测试确认");
  await page.locator("#sendButton").click();
  const secondCard = page.locator(".agent-plan-approval").last();
  await expect(secondCard).toContainText("等待你的确认");
  await secondCard.getByRole("button", { name: "确认并运行" }).click();
  await expect(secondCard).toContainText("后台任务运行中");
  await expect(page.locator("#taskInput")).toBeDisabled();
  await expect(page.locator("#sendButton")).toBeDisabled();
  await page.reload();
  await expect(page.locator("#appShell")).toBeVisible();
  const resumedCard = page.locator(".agent-plan-approval").last();
  await expect(resumedCard).toContainText("后台任务运行中");
  await expect(page.locator("#taskInput")).toBeDisabled();
  taskFinished = true;
  await expect(resumedCard).toContainText("后台任务已完成");
  await expect(page.locator("#taskInput")).toBeEnabled();
  const resultMessage = page.locator(".message.assistant").last();
  await expect(resultMessage).toContainText("OpenHands 测试结果");
  await expect(resultMessage).not.toContainText("process only");
  await expect(resultMessage.getByRole("link", { name: /下载报告/ })).toHaveAttribute("href", `/api/projects/${projectId}/artifacts/final_report.md`);
  await resultMessage.getByRole("button", { name: "查看 Agent 执行过程" }).click();
  await expect(page.locator("#detailPanelTitle")).toHaveText("执行过程 (1)");
  await expect(page.locator("#detailPanelContent")).toContainText("process only");
  await resultMessage.getByRole("button", { name: "查看 Agent 产物" }).click();
  await expect(page.locator("#detailPanelTitle")).toHaveText("产物文件 (1)");
  await expect(page.locator(".artifact-card")).toHaveAttribute("href", `/api/projects/${projectId}/artifacts/final_report.md`);
  expect(confirmCount).toBe(1);
  expect(runCount).toBe(1);
  expect(dialogCount).toBe(0);

  await page.evaluate(() => {
    const storageKey = Object.keys(localStorage).find((key) => key.startsWith("rosalind.chats."));
    const saved = JSON.parse(localStorage.getItem(storageKey));
    const chat = saved.chats.find((item) => item.id === saved.activeChatId);
    chat.messages.push({
      id: "legacy-expanded-result",
      role: "assistant",
      content: "# Agent 执行结果\n\n**计划状态：** completed\n\n## 1. Python 分析\n\n状态：completed · 尝试次数：1\n\n```python\nprint('legacy process')\n```\n\n## 2. 综合报告\n\n状态：completed · 尝试次数：1\n\n## 已完成：历史报告\n\n最终结论已生成。\n\n---\n\n请核验结果。"
    });
    localStorage.setItem(storageKey, JSON.stringify(saved));
  });
  await page.reload();
  const migratedResult = page.locator(".message.assistant").last();
  await expect(migratedResult).toContainText("已完成：历史报告");
  await expect(migratedResult).not.toContainText("legacy process");
  await migratedResult.getByRole("button", { name: "查看 Agent 执行过程" }).click();
  await expect(page.locator("#detailPanelContent")).toContainText("legacy process");

  await page.evaluate(() => {
    const storageKey = Object.keys(localStorage).find((key) => key.startsWith("rosalind.chats."));
    const saved = JSON.parse(localStorage.getItem(storageKey));
    const chat = saved.chats.find((item) => item.id === saved.activeChatId);
    chat.messages.push({
      id: "legacy-background-task",
      role: "assistant",
      content: `任务已提交后台执行。\n\n任务 ID：\`${"b".repeat(32)}\`\n\n可稍后刷新页面继续查看。`
    });
    localStorage.setItem(storageKey, JSON.stringify(saved));
  });
  await page.reload();
  const recoveredLegacyCard = page.locator(".agent-plan-approval").last();
  await expect(recoveredLegacyCard).toContainText("后台任务已完成");
  await expect(page.locator(".message.assistant").last()).toContainText("OpenHands 测试结果");
  await expect(page.locator(".message.assistant").last()).not.toContainText("process only");

  await context.close();
});

test("registration, chat navigation, settings, login, and a real model response", async ({ browser }) => {
  const context = await browser.newContext({ locale: "zh-CN" });
  const page = await context.newPage();
  const email = `e2e-${Date.now()}@openrosalind.bio`;
  const password = "Rosalind-E2E-2026";

  await page.goto("/app");
  await expect(page.locator("#authScreen")).toBeVisible();

  await page.locator("#registerMode").click();
  await page.locator("#authEmail").fill(email);
  await page.locator("#authPassword").fill(password);
  const registerResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/auth/register"));
  await page.locator("#authSubmit").click();
  expect((await registerResponsePromise).status()).toBe(200);
  await page.waitForFunction(() => (
    !document.querySelector("#authSubmit").disabled && !document.querySelector("#appShell").hidden
  ));

  await expect(page.locator("#appShell")).toBeVisible();
  await expect(page.locator("#newChat")).toBeVisible();
  await expect(page.locator("#currentUser")).toHaveText(email);
  await expect(page.locator(".chat-history-item")).toHaveCount(1);

  await page.locator("#newChat").click();
  await page.locator("#newChat").click();
  await page.locator("#newChat").click();
  await expect(page.locator(".chat-history-item")).toHaveCount(1);

  await page.locator('[data-function-id="paper_summary"]').click();
  await expect(page.locator("#selectedSkill")).toHaveText("论文精读");
  await expect(page.locator("#uploadStatus")).toContainText("PDF");

  await page.locator('[data-function-id="protein_analysis"]').click();
  await expect(page.locator("#selectedSkill")).toHaveText("蛋白质分析");
  await expect(page.locator("#uploadStatus")).toContainText("FASTA");
  await page.locator("#documentFile").setInputFiles("tests/fixtures/example.fasta");
  await expect(page.locator("#attachmentChip")).toBeVisible();
  await expect(page.locator("#attachmentName")).toHaveText("example.fasta");
  await page.locator("#removeAttachment").click();
  await expect(page.locator("#attachmentChip")).toBeHidden();

  await page.locator("#sidebarAccount").click();
  await expect(page.locator("#accountMenu")).toBeVisible();
  await page.locator("#openSettings").click();
  await expect(page.locator("#settingsDialog")).toBeVisible();
  await expect(page.locator("#model")).toHaveValue("qwen3.7-max");
  await expect(page.locator("#apiKey")).toHaveValue("");
  await expect(page.locator("#apiKey")).toHaveAttribute("readonly", "");
  await page.locator('#settingsDialog button[value="cancel"]').click();

  await page.locator("#sidebarAccount").click();
  await page.locator("#logout").click();
  await expect(page.locator("#authScreen")).toBeVisible();

  await page.locator("#loginMode").click();
  await page.locator("#authEmail").fill(email);
  await page.locator("#authPassword").fill(password);
  const loginResponsePromise = page.waitForResponse((response) => response.url().endsWith("/api/auth/login"));
  await page.locator("#authSubmit").click();
  expect((await loginResponsePromise).status()).toBe(200);
  await page.waitForFunction(() => (
    !document.querySelector("#authSubmit").disabled && !document.querySelector("#appShell").hidden
  ));
  await expect(page.locator("#appShell")).toBeVisible();

  const polishSkill = page.locator('[data-function-id="manuscript_polish"]');
  await expect(polishSkill).toBeVisible();
  await polishSkill.click();
  await expect(page.locator("#selectedSkill")).toHaveText("论文润色");
  const prompt = "请将这句话润色为简洁的学术中文：该基因可能和肿瘤进展有一定关系。";
  await page.locator("#taskInput").fill(prompt);
  const generateResponsePromise = page.waitForResponse((response) => (
    response.url().endsWith("/api/generate") && response.request().method() === "POST"
  ));
  await page.locator("#sendButton").click();

  await expect(page.locator(".message.pending")).toBeVisible();
  const generateResponse = await generateResponsePromise;
  expect(generateResponse.status()).toBe(200);
  const generateBody = await generateResponse.json();
  expect(generateBody.ok).toBe(true);
  expect(String(generateBody.content || "").length).toBeGreaterThan(40);
  await expect(page.locator(".message.pending")).toBeHidden({ timeout: 90_000 });
  await expect(page.locator(".message.user").last()).toContainText("该基因可能和肿瘤进展");
  const answer = page.locator(".message.assistant .markdown-body").last();
  await expect(answer).toBeVisible();
  await expect(answer).not.toBeEmpty();
  const answerMessage = page.locator(".message.assistant").last();
  const feedbackResponsePromise = page.waitForResponse((response) => (
    response.url().endsWith("/api/messages/feedback") && response.request().method() === "POST"
  ));
  await answerMessage.getByRole("button", { name: "这个回答有帮助" }).click();
  const feedbackResponse = await feedbackResponsePromise;
  expect(feedbackResponse.status()).toBe(200);
  expect((await feedbackResponse.json()).feedback.rating).toBe("like");
  await expect(answerMessage.getByRole("button", { name: "这个回答有帮助" })).toHaveClass(/active/);
  await answerMessage.getByRole("button", { name: "查看分析与工具过程" }).click();
  await expect(page.locator("#detailPanel")).toBeVisible();
  await expect(page.locator("#detailPanelTitle")).toContainText("分析与工具过程");
  await expect(page.locator(".confidence-badge").first()).toContainText("%");
  await page.locator("#closeDetailPanel").click();
  await expect(page.locator("#detailPanel")).toBeHidden();
  await expect(page.locator(".chat-history-title").first()).toContainText("请将这句话润色");

  await page.reload();
  await expect(page.locator("#appShell")).toBeVisible();
  await expect(page.locator(".chat-history-title").first()).toContainText("请将这句话润色");
  await expect(page.locator(".message.assistant .markdown-body").last()).toBeVisible();

  await page.locator('[data-function-id="peer_review"]').click();
  await expect(page.locator("#selectedSkill")).toHaveText("论文评审");
  await expect(page.locator(".chat-history-item")).toHaveCount(2);
  await expect(page.locator(".chat-history-meta").nth(1)).toContainText("论文润色");
  await expect(page.locator(".message")).toHaveCount(0);

  await page.locator("#sidebarAccount").click();
  await page.locator("#openSettings").click();
  await page.locator("#apiKey").click();
  await page.locator("#apiKey").fill("invalid-e2e-key");
  await page.locator('#settingsDialog button[value="done"]').click();
  await page.locator("#taskInput").fill("请简要评审这项研究。" );
  const invalidKeyResponsePromise = page.waitForResponse((response) => (
    response.url().endsWith("/api/generate") && response.request().method() === "POST"
  ));
  await page.locator("#sendButton").click();
  const invalidKeyResponse = await invalidKeyResponsePromise;
  const invalidKeyBody = await invalidKeyResponse.json();
  expect(invalidKeyBody.ok).toBe(false);
  expect(invalidKeyBody.status).toBe(401);
  expect(invalidKeyBody.error).toContain("模型服务认证失败");
  expect(invalidKeyBody.error).not.toContain("invalid_api_key");
  await expect(page.locator(".message.assistant").last()).toContainText("模型服务认证失败");
  await expect(page.locator(".message.assistant").last()).not.toContainText("invalid_api_key");

  await page.locator(".chat-history-item").nth(1).click();
  await expect(page.locator("#selectedSkill")).toHaveText("论文润色");
  await expect(page.locator(".message.assistant .markdown-body").last()).toBeVisible();

  await page.locator('[data-function-id="protein_analysis"]').click();
  await expect(page.locator("#selectedSkill")).toHaveText("蛋白质分析");
  let biologyRequestCount = 0;
  const countBiologyRequests = (request) => {
    if (request.url().endsWith("/api/biology/analyze")) biologyRequestCount += 1;
  };
  page.on("request", countBiologyRequests);
  await page.locator("#taskInput").fill(">bad_sequence\nATGCXYZ123");
  await page.locator("#sendButton").click();
  const validationMessage = page.locator(".message.assistant").last();
  await expect(validationMessage).toContainText("无法可靠判定序列类型");
  await expect(validationMessage).toContainText("X、Y、Z、1、2、3");
  await expect(validationMessage).toContainText("本次未执行 BLAST");
  await expect(validationMessage).not.toContainText("HTTP Error 400");
  expect(biologyRequestCount).toBe(0);
  page.off("request", countBiologyRequests);
  await expect(page.locator("#taskInput")).toBeEnabled();

  const backendValidationResponse = await context.request.post("https://openrosalind.bio/api/biology/analyze", {
    data: {
      tool: "protein_analysis",
      input: ">bad_sequence\nATGCXYZ123",
      attachment: ""
    }
  });
  expect(backendValidationResponse.status()).toBe(400);
  const backendValidationBody = await backendValidationResponse.json();
  expect(backendValidationBody.error).toContain("X、Y、Z、1、2、3");
  expect(backendValidationBody.error).toContain("本次未执行 BLAST");

  await page.locator("#sidebarAccount").click();
  await page.locator("#clearChat").click();
  await page.route("**/api/biology/analyze", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        ok: true,
        mode: "tool",
        content: "# 蛋白质分析\n\n混合输入解析测试通过。\n\n## 参考来源\n\n- [UniProt P02768](https://rest.uniprot.org/uniprotkb/P02768.json)",
        sources: [{ title: "UniProt P02768", url: "https://rest.uniprot.org/uniprotkb/P02768.json", provider: "UniProt" }],
        trace: [
          { title: "解析并校验 FASTA", kind: "tool", confidence: 99, detail: "本地确定性序列校验。" },
          { title: "汇总工具证据", kind: "reasoning", confidence: 62, detail: "基于工具结果组织解释。" }
        ]
      })
    });
  });
  const mixedInput = ">test_protein\nMKWVTFISLLFLFSSAYSRGVFRRDTHKSEIAHRFKDLGE\n请检查序列类型、长度，并给出下一步分析建议。";
  await page.locator("#taskInput").fill(mixedInput);
  const mixedInputRequestPromise = page.waitForRequest((request) => request.url().endsWith("/api/biology/analyze"));
  await page.locator("#sendButton").click();
  const mixedInputRequest = await mixedInputRequestPromise;
  expect(mixedInputRequest.postDataJSON().input).toBe(mixedInput);
  await expect(page.locator(".message.assistant").last()).toContainText("混合输入解析测试通过");
  await expect(page.locator(".message.assistant").last()).not.toContainText("非法或不兼容字符");
  await expect(page.locator(".message.assistant .markdown-body").last()).not.toContainText("参考来源");
  await page.locator(".message.assistant").last().getByRole("button", { name: "查看参考来源" }).click();
  await expect(page.locator("#detailPanelTitle")).toHaveText("参考来源 (1)");
  await expect(page.locator(".source-card")).toHaveCount(1);
  await expect(page.locator(".source-card")).toContainText("UniProt P02768");
  await page.locator(".message.assistant").last().getByRole("button", { name: "查看分析与工具过程" }).click();
  await expect(page.locator(".trace-step")).toHaveCount(2);
  await expect(page.locator(".confidence-badge").first()).toHaveText("高 99%");

  await context.close();
});
