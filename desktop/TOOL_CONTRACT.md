# OpenRosalind Desktop Tool Contract v1

Tool Contract 是 Agent 与本地能力之间的唯一扩展边界。Docker、Compose、原生进程
和远程计算只是不同 Executor，不允许各自定义一套绕过权限和审计的调用方式。

正式 JSON Schema 位于 [`tool-contract.schema.json`](./tool-contract.schema.json)。macOS
和 Windows 使用同一 Schema、风险等级、ToolRun 状态和审计字段。

## 当前实现

Desktop Core 已提供 Tool Contract 注册表，以及以下 Tauri 命令：

- `desktop_list_tool_contracts`：返回已安装工具及其权限和资源声明；
- `desktop_run_low_risk_tool`：只运行 `risk=low` 且 `approval=automatic` 的工具；
- `desktop_execute_approved_python_tool`：在 Rust Tool Manager 内运行已逐次批准的 Python；
- `desktop_execute_approved_container_tool`：运行已逐次批准的 Docker Python 沙箱；
- `desktop_container_capability`：检测 Docker CLI、Daemon 和固定镜像状态；
- `desktop_prepare_container_image`：经 Desktop Core 原生系统对话框确认后下载固定摘要镜像；
- `desktop_cancel_tool_run`：请求取消正在运行的原生进程组；
- `desktop_list_tool_artifacts`：读取一个 ToolRun 的持久化产物索引；
- `desktop_read_tool_artifact`：按 Artifact ID 校验后读取最多 512 KiB 文本预览；
- `desktop_reveal_tool_artifact`：校验后在 Finder 或 Windows 文件资源管理器中显示文件；
- `desktop_export_tool_artifact`：校验后通过系统保存对话框显式导出文件；
- `desktop_list_tool_runs`：读取一个 AgentJob 的持久化 ToolRun 记录。

首个工具是 `text.statistics@1.0.0`。它在 Rust Desktop Core 内执行，没有文件系统、
网络或 Secret 权限。输入、输出、Executor、权限快照、状态和时间线都会写入本地
`desktop-core.db`，从而验证完整的低风险自动执行链路。

`python.run@1.0.0-alpha.1` 已接入逐次批准状态机。Desktop Core 先创建
`awaiting_approval` ToolRun 并冻结权限快照，UI 展示权限后记录批准或拒绝；只有
`approved` 才能进入 `running`，最终写入 `succeeded`、`failed`、`cancelled` 或
`timed_out`。Python 由 Rust Tool Manager 以固定解释器和 `-I -B` 启动；每次运行使用
独立 input/output 目录、环境变量白名单和跨平台进程组，并限制 60 秒运行时间、日志、
输出文件总量和文件数。Contract 仍按最坏情况声明为 `critical`：主机文件读写、主机
网络、无托管 Secret 注入。该入口只能由用户点击模型回答中的“运行 Python”触发，
Agent Worker 无权自行批准或启动。Web 模式继续使用原有 Docker/本地执行接口。

原生 Python 输出会在执行结束后计算 SHA-256，并以相对 ToolRun 路径写入 Artifact 表。
UI 只持有 Artifact ID；预览或显示文件时，Desktop Core 会重新解析受控目录并核对文件
大小与 SHA-256，发生路径逃逸、符号链接替换或执行后篡改时拒绝访问。二进制文件不进入
WebView，文本预览上限为 512 KiB。显式导出只能由系统保存对话框选择目标位置；WebView
不能提交目标路径，复制完成后 Desktop Core 会再次核对大小和摘要。

`python.container@1.0.0-alpha.1` 是首个 Container Executor 工具。它使用固定摘要的
Docker Official Image `python:3.12.14-slim-bookworm`，运行时强制 `--pull=never`、
`--network=none`、只读根文件系统、非 root UID、丢弃全部 Linux capabilities、禁止提权，
并限制为 1 CPU、512 MiB 内存、64 个进程、60 秒和 20 MiB 输出。容器只挂载本次
ToolRun 的只读 input 与可写 output 目录，不继承主机代理、API Key 或其他环境变量。
首次使用的镜像下载必须通过 Desktop Core 的原生系统确认对话框；Docker 不存在或 Daemon 未启动时该工具
显示为不可用，但主 Agent、Native Executor 和应用启动不受影响。

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

下一步是增加镜像签名/升级清单、Container Executor 的真实 Docker Desktop 集成矩阵，
以及 Compose Executor。Agent 仍不能自动批准本机 Python、容器或 Shell。
