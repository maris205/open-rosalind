# Open-Rosalind Agent 典型测试案例

本文用于验证当前 ECS 开发版的核心链路：用户登录、科研项目、项目记忆、自动任务、Redis Worker、Docker Python 沙箱、参考文献验证和任务恢复。

访问地址：

```text
http://服务器公网IP:8765/
```

测试结果应以状态、审计记录和实际输出为准，不要求 Qwen 返回完全相同的措辞。

## 测试前检查

在服务器执行：

```bash
systemctl is-active redis-server
systemctl is-active open-rosalind-worker
systemctl is-active open-rosalind-agent
redis-cli ping
```

预期结果：

```text
active
active
active
PONG
```

## 案例一：创建项目并建立研究记忆

### 操作

1. 使用邮箱和至少 8 位密码注册。
2. 新建项目：`肿瘤免疫生物标志物探索`。
3. 添加以下项目记忆。

事实：

```text
当前只有研究设想，没有患者数据、实验结果或已核验参考文献。
```

限制：

```text
不得生成患者级数据，不得虚构样本量、P 值、DOI、PMID 或实验结果。
```

开放问题：

```text
应该优先验证候选标志物的预后价值、治疗响应价值，还是机制关联？
```

### 预期结果

- 刷新页面后项目仍存在。
- 三条记忆仍显示在项目记忆列表中。
- 记忆类型分别为 `fact`、`constraint` 和 `open_question`。
- 不同登录账户不能读取该项目。

## 案例二：生成并执行生物医学研究计划

### 任务目标

```text
围绕肿瘤免疫微环境中的候选生物标志物，设计一个不依赖虚构数据的前期研究流程。需要包括研究问题定义、证据检索规划、候选标志物筛选原则、可行的数据分析方案、偏倚与伦理风险，以及最终需要人工确认的事项。当前没有真实数据，不得声称已经完成检索、实验或统计分析。
```

### 操作

1. 点击“生成任务计划”。
2. 检查每个步骤的标题、执行说明和 skill。
3. 点击“确认计划”。
4. 先点击“运行下一步”。
5. 刷新页面，确认第一步结果仍然存在。
6. 点击“连续运行”完成剩余步骤。

### 预期结果

- 新计划初始状态为 `draft`。
- 未确认时不能执行。
- 确认后状态为 `approved`。
- 提交后台任务后页面显示 `queued` 或 `started`。
- Worker 逐步将状态更新为 `running` 和 `completed`。
- 最终计划状态为 `completed`。
- 每一步包含实际 Qwen 输出，但不能声称执行了不存在的检索、实验或统计工具。
- 页面刷新不会丢失计划、步骤状态或步骤输出。

## 案例三：验证关闭页面后后台继续运行

### 任务目标

```text
为一个观察性生物医学研究制定四步质量审查流程：研究问题和人群定义、变量与混杂因素检查、统计分析前提检查、结果报告与局限性检查。每一步都列出输入、输出、风险和需要人工确认的内容。
```

### 操作

1. 生成并确认计划。
2. 点击“连续运行”。
3. 页面显示后台任务已排队后，关闭浏览器标签页。
4. 等待约 1-3 分钟。
5. 重新打开页面并登录。
6. 选择原项目。

### 预期结果

- 浏览器关闭后 `open-rosalind-worker` 继续执行。
- 重新打开项目后可以看到已完成步骤和输出。
- Redis 队列最终回到空闲状态。

服务器检查：

```bash
redis-cli llen rq:queue:rosalind
journalctl -u open-rosalind-worker --since "10 minutes ago" --no-pager
```

日志中应出现任务接收和 `Job OK`；队列完成后长度应为 `0`。

## 案例四：把任务结果保存为项目记忆

### 操作

1. 在已完成的任务步骤中选择一个具有长期价值的结果。
2. 点击“保存到记忆”。
3. 刷新项目。
4. 再生成一个与原目标相关的新任务计划。

### 预期结果

- 项目记忆中出现新的 `conclusion` 条目。
- 该条目的来源类型为 `task_step`。
- 新计划生成时会读取这条项目记忆。
- 记忆内容仍应被视为 Agent 结果，而不是自动升级为已验证科学事实。

## 案例五：运行受限 Python 分析

### Python 代码

将以下代码粘贴到 Python Sandbox：

```python
import csv
import hashlib
from pathlib import Path

rows = [
    {"marker": "Marker_A", "effect": 1.25, "p_value": 0.031},
    {"marker": "Marker_B", "effect": 0.91, "p_value": 0.420},
    {"marker": "Marker_C", "effect": 1.48, "p_value": 0.008},
]

significant = [row for row in rows if row["p_value"] < 0.05]

with Path("screening_result.csv").open("w", newline="", encoding="utf-8") as handle:
    writer = csv.DictWriter(handle, fieldnames=["marker", "effect", "p_value"])
    writer.writeheader()
    writer.writerows(significant)

payload = Path("screening_result.csv").read_bytes()
print(f"rows={len(rows)}")
print(f"selected={len(significant)}")
print(f"sha256={hashlib.sha256(payload).hexdigest()}")
```

### 操作

1. 逐行检查代码。
2. 勾选权限等级 3 执行确认。
3. 点击“Run in Docker”。
4. 下载 `screening_result.csv`。

### 预期结果

标准输出应包含：

```text
rows=3
selected=2
```

输出 CSV 应只包含 `Marker_A` 和 `Marker_C`。任务审计中应记录：

- Docker 镜像
- 代码 SHA-256
- 退出码 `0`
- 网络状态 `disabled`
- CPU、内存和超时限制
- 输出文件大小和 SHA-256

该数据为功能测试数据，不能作为真实生物医学证据。

## 案例六：验证 Docker 隔离边界

### Python 代码

```python
import socket
from pathlib import Path

checks = {}

try:
    socket.create_connection(("1.1.1.1", 53), timeout=2)
    checks["network"] = "unexpectedly available"
except Exception as exc:
    checks["network"] = type(exc).__name__

try:
    Path("/blocked.txt").write_text("x", encoding="utf-8")
    checks["rootfs"] = "unexpectedly writable"
except Exception as exc:
    checks["rootfs"] = type(exc).__name__

print(checks)
```

### 预期结果

- `network` 应返回异常类型，而不是 `unexpectedly available`。
- `rootfs` 应返回异常类型，而不是 `unexpectedly writable`。
- 执行结束后不存在残留任务容器。

服务器检查：

```bash
docker ps -a --filter name=rosalind-python
```

## 案例七：参考文献验证

### 操作

1. 选择 Reference Verifier。
2. 上传仓库中的测试文件：

```text
examples/reference_verification_example.bib
```

3. 执行参考文献验证。

### 预期结果

- 每条文献单独显示核验状态。
- DOI、PMID、标题、年份等元数据分开检查。
- 没有可靠匹配的条目不能标记为 Verified。
- 系统明确区分“文献真实存在”和“文献支持当前 claim”。
- 高风险条目进入人工核验清单。

外部 Crossref 或 PubMed 暂时不可用时，结果可以失败或保持未验证，但不能生成伪造的成功结果。

## 案例八：任务失败与重试

正常用户测试可以等待模型接口暂时失败，或由管理员在测试环境中重启 Worker 模拟执行中断：

```bash
systemctl restart open-rosalind-worker
```

### 预期结果

- Worker 启动后把中断的 `running` 步骤标记为 `failed`。
- 计划状态变为 `failed`。
- 页面显示“重试此步骤”。
- 点击重试后步骤恢复为 `pending`，计划恢复为 `approved`。
- 再次运行时 attempts 计数增加。
- 系统不能把中断步骤误记为成功。

不要在其他用户正在运行任务时执行该测试。

## 验收清单

- [ ] 注册、登录和退出正常
- [ ] 未登录不能调用模型、上传或执行代码
- [ ] 项目和记忆刷新后保留
- [ ] 计划必须确认后才能执行
- [ ] 后台任务提交立即返回
- [ ] 关闭页面后 Worker 继续运行
- [ ] 同一计划不能重复入队
- [ ] 步骤结果和失败状态写入 SQLite
- [ ] 完成结果可以写入项目记忆
- [ ] Python 必须人工确认后执行
- [ ] Docker 无网络、只读根文件系统和资源限制生效
- [ ] 输出文件可以下载且带 SHA-256
- [ ] 参考文献不能被无依据标记为已验证
- [ ] Redis、Worker 和 Web 服务均为 active

## 当前限制

- 自动任务由单个 Worker 串行执行。
- 尚未提供任务取消和定时执行。
- Docker Python 任务仍是单独确认后的同步请求。
- 当前没有邮箱验证、密码找回、多因素认证和管理员后台。
- 通过公网 HTTP 测试时 Cookie 尚未启用 Secure；切换 HTTPS 后必须设置 `ROSALIND_COOKIE_SECURE=1`。
