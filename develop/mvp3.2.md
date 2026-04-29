对，这几个改动都值得做，而且会明显更像“可用产品”。

建议这样收敛：

## 1. 登录功能：做最简单的

MVP3 可以加一个轻量登录，目的不是权限复杂化，而是：

```text
保存 sessions
隔离用户历史
方便后续限流/反馈
```

先做：

```text
email + magic link / GitHub OAuth
```

不要一开始做复杂组织、角色、计费。

---

## 2. 单步 / 多步不要让用户选

这个你判断很对。科研用户不该理解“single-step / multi-step”。

改成：

```text
用户输入
→ 系统自动判断
→ 简单任务走 Agent
→ 复杂任务走 Harness
```

UI 上可以只显示：

```text
Mode: Auto
```

Trace 里再记录：

```json
{
  "execution_mode": "single_step | harness",
  "reason": "requires literature + annotation"
}
```

---

## 3. 做成聊天式界面更合适

是的，建议改成类似大模型服务的聊天形式。

但保留你的结构化内容：

```text
用户消息
AI 回复卡片：
- Summary
- Annotation
- Evidence
- Trace
- Confidence
```

也就是说，不是纯文本聊天，而是：

```text
Chat UI + structured scientific cards
```

这是最适合 Open-Rosalind 的形态。

---

## 4. 支持基本上下文

MVP3 做“会话内上下文”就够了：

```text
用户：分析这个蛋白序列
系统：返回结果
用户：再查一下相关文献
系统：自动使用上一轮识别到的 protein / accession
```

不要做长期记忆。

---

## 推荐 UI 改版

```text
左侧：Sessions
中间：Chat Timeline

User message
Assistant response
  Summary card
  Evidence card
  Annotation card
  Trace collapsible
  Confidence badge

底部：
[ 输入框 ]
[ Analyze ]
```

顶部不需要：

```text
Single-step / Multi-step
mode selector
```

可以保留一个高级选项：

```text
Advanced settings
- force sequence mode
- force mutation mode
```

默认隐藏。

---

## 给 Codex 的任务

```text
Task 1:
Refactor UI into chat timeline. Each user input and agent response becomes a message.

Task 2:
Remove visible single-step / multi-step selector. Add auto execution mode selection in backend.

Task 3:
Add execution_mode to API response and trace:
- single_step
- harness
- reason

Task 4:
Add session context:
- store last entities
- support follow-up queries like "find related papers"
- do not persist long-term memory beyond session history

Task 5:
Add simple auth:
- GitHub OAuth or email magic link
- associate sessions with user_id
- allow anonymous demo mode if possible
```

一句话：**聊天式入口 + 自动模式选择 + 结构化科研卡片，是你这个产品最合适的 UI。**
