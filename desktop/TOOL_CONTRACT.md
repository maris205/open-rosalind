# OpenRosalind Desktop Tool Contract v1

Tool Contract 是 Agent 与本地能力之间的唯一扩展边界。Docker、Compose、原生进程
和远程计算只是不同 Executor，不允许各自定义一套绕过权限和审计的调用方式。

正式 JSON Schema 位于 [`tool-contract.schema.json`](./tool-contract.schema.json)。macOS
和 Windows 使用同一 Schema、风险等级、ToolRun 状态和审计字段。

## 当前实现

Desktop Core 已提供 Tool Contract 注册表，以及以下 Tauri 命令：

- `desktop_list_tool_contracts`：返回已安装工具及其权限和资源声明；
- `desktop_run_low_risk_tool`：只运行 `risk=low` 且 `approval=automatic` 的工具；
- `desktop_list_tool_runs`：读取一个 AgentJob 的持久化 ToolRun 记录。

首个工具是 `text.statistics@1.0.0`。它在 Rust Desktop Core 内执行，没有文件系统、
网络或 Secret 权限。输入、输出、Executor、权限快照、状态和时间线都会写入本地
`desktop-core.db`，从而验证完整的低风险自动执行链路。

## 权限规则

| 风险 | 示例 | v1 行为 |
|---|---|---|
| low | 纯文本统计、已加载数据的确定性转换 | 可按 Contract 自动执行 |
| medium | 写入 Job 输出、生成报告 | 需要按任务授权 |
| high | Python、Shell、安装依赖、网络 | 每次明确确认 |
| critical | 项目外目录、上传敏感数据、系统配置 | 逐次确认，默认拒绝 |

ToolRun 创建时必须冻结权限快照。后续工具升级不能改变历史记录的权限含义。Secret
只允许以凭据引用声明，由 Desktop Core 在获批的 Executor 边界解析；API Key、登录
Token 或密码不得出现在 Tool input、命令行、日志或 Agent Worker 消息中。

## Executor 扩展

- Native Executor：固定可执行文件、环境白名单、工作目录、进程组、超时和输出上限；
- Container Executor：镜像必须固定 digest，默认无网络、只读根文件系统、非 root；
- Compose Executor：独立项目名、网络和 Volume，由 Tool Manager 管理健康状态；
- Remote Executor：必须声明 HTTPS 目标、上传数据范围、费用和数据处理政策。

下一步是实现高风险工具的“提出请求 → 展示权限 → 用户批准/拒绝 → 执行”状态机，
再把现有 Python 代码执行迁移为 `python.run` Tool Contract。未经这一步，不应让 Agent
自动调用本机 Python 或 Shell。
