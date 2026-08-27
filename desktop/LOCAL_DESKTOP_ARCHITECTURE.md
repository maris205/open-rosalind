# OpenRosalind 本地桌面版架构设计

## 1. 文档状态

- 状态：Draft
- 目标版本：Desktop Local v1
- 适用平台：macOS、Windows
- 当前基础：Tauri 2、共享 Web UI、Python API、SQLite 和本地工具
- 核心方向：本地优先、云端轻量、工具可插拔、执行可审计

本文定义 OpenRosalind 从“Web 应用桌面封装”演进为“本地 Agent 工作台”的目标
架构。macOS 和 Windows 共用产品模型、Agent、Provider、工具协议和大部分实现；
操作系统差异通过平台适配层处理。

## 2. 背景与问题

当前 Desktop Alpha 已证明 Tauri、共享 Web UI、本地 Python sidecar、本地队列、
macOS 安装包和 Windows 桌面壳可以工作，Docker 与 Redis 也不再是桌面版启动
前置条件。

但当前形态仍接近 Web 应用封装，尚未完整发挥本地客户端价值：

1. 模型凭据和 Provider 缺少安全、统一的本地管理；
2. 云端认证、对话上下文和 Agent 任务的 Session 概念尚未分离；
3. 本地 Agent、权限系统和工具执行器缺少稳定契约；
4. 固定 loopback HTTP 端口不适合作为最终高权限接口；
5. Docker 尚未成为正式的可选工具执行后端；
6. 本地文件、代码、Git 和科研软件能力仍需系统化开放。

## 3. 产品目标

### 3.1 目标

- 用户只使用 OpenRosalind 服务完成登录、授权和订阅验证；
- 模型请求由客户端直接发送给用户配置的模型服务；
- 模型 API Key 只保存在操作系统安全凭据存储中；
- 对话、项目、任务、文件和审计数据默认保存在本地；
- 主 Agent 作为本地常驻 Worker 运行，不要求 Docker；
- 简单工具本机执行，复杂或高风险工具可以封装为 Docker；
- 支持单容器、常驻容器和 Docker Compose 工具包；
- 所有执行后端通过统一 Tool Contract 暴露给 Agent；
- macOS 与 Windows 共用核心实现，平台差异集中在适配层；
- Docker、网络或云端不可用时，基础客户端仍可使用。

### 3.2 非目标

- 不把整个 Agent 默认运行在 Docker 中；
- 不为每个对话 Session 创建进程或容器；
- 不默认把对话、项目文件或 Prompt 上传到 OpenRosalind 服务；
- 不让 WebView 直接持有模型 API Key；
- 不给予 Agent 整个 Home 或用户目录的默认访问权；
- 不把 Docker 作为唯一工具扩展协议；
- 不在第一阶段实现完整云同步。

## 4. 核心原则

1. **本地优先**：用户数据、Agent 和工具默认在本机运行。
2. **云端轻量**：服务端主要承担身份、授权、更新和可选同步。
3. **凭据隔离**：模型 Key 不进入 WebView、Prompt、日志和工具容器。
4. **能力与执行解耦**：Tool Contract 描述能力，Executor 决定运行方式。
5. **最小权限**：工具只获得完成任务所需的目录、网络和 Secret。
6. **显式授权**：高风险写入、命令、网络和目录扩展必须确认。
7. **可审计**：模型调用、工具调用、用户确认和文件变更均可追踪。
8. **跨平台核心**：macOS、Windows 共用业务核心。
9. **失败关闭**：权限、镜像校验或凭据缺失时不得静默降级。
10. **可选增强**：Docker、远程算力和同步不能成为基础能力前置条件。

## 5. 总体架构

~~~mermaid
flowchart LR
    UI["Tauri / WebKit 或 WebView2 UI"] --> IPC["Tauri IPC"]
    IPC --> Core["Desktop Core（Rust）"]
    Core --> Auth["Auth Client"]
    Core --> Vault["Credential Vault"]
    Core --> Provider["Provider Broker"]
    Core --> Agent["Local Agent Worker"]
    Core --> Tools["Tool Manager"]
    Core --> Store["Local SQLite / Artifact Store"]

    Auth --> Cloud["OpenRosalind Control Plane"]
    Provider --> Models["用户配置的模型服务"]
    Agent --> Provider
    Agent --> Tools

    Tools --> Native["Native Executor"]
    Tools --> Container["Container Executor"]
    Tools --> Compose["Compose Executor"]
    Tools --> Remote["Remote Executor"]
~~~

高权限操作必须经过 Desktop Core。WebView 和 Agent Worker 都不能绕过 Desktop
Core 直接访问凭据、任意目录或 Docker daemon。

## 6. 组件职责

### 6.1 Tauri UI

负责登录、模型设置、项目、对话、任务、权限确认、进度、文件变更和审计界面。
UI 不保存或直接使用模型 API Key，不直接执行 Shell、Docker 或高权限文件操作。

### 6.2 Desktop Core

建议继续使用 Rust/Tauri 实现，作为客户端可信控制边界：

- Tauri IPC；
- 登录 Token 和模型凭据访问；
- 项目目录授权；
- Agent Worker 生命周期；
- Tool Contract 校验；
- 权限策略和用户确认；
- 子进程、容器、超时和资源限制；
- 本地数据库和 Artifact 索引；
- 日志脱敏、崩溃恢复和应用更新。

### 6.3 Local Agent Worker

主 Agent 建议继续使用 Python，以复用现有生物医学能力和 Skills。它是一个由
Desktop Core 管理的本地常驻 Worker，而不是每个 Session 一个进程。

它负责上下文、任务规划、Skill 选择、Tool Contract 调用和结果总结，但不能读取
真实模型 Key、自行扩大目录权限、绕过 Tool Manager 执行高风险命令或直接控制
Docker Socket。

推荐使用 stdio JSON-RPC、Unix Domain Socket 或 Windows Named Pipe 与 Desktop
Core 通信。若保留 loopback HTTP，必须使用随机端口、每次启动随机 Token、严格
Origin 校验和最小接口，不再固定使用未认证的高权限端口。

当前 macOS alpha.6 已落地 stdio JSON-RPC v4：Worker 可以在最多四轮的
模型/工具循环中请求 `text.statistics`、`project.files.list` 和
`project.file.read`。Worker 只提出结构化请求，Desktop Core 负责检查项目目录
授权、Tool Contract 风险和自动批准策略，并持久化 ToolRun；工具结果会被标记为
不可信数据后再交回模型。Python、Shell、Docker、网络和写入操作仍不能自动执行，
必须继续走用户可见的提案和批准流程。

### 6.4 Provider Broker

Provider Broker 统一支持 OpenAI-compatible、Anthropic、OpenRouter、阿里云百炼
及后续 Provider，负责凭据读取、认证头、流式响应、取消、超时、重试和限流。

推荐调用链：

    UI / Agent Worker
      -> Desktop Core
      -> Provider Broker
      -> Model Provider

WebView、Agent 和工具容器都不获得真实模型 Key。

### 6.5 Tool Manager

Tool Manager 是所有本地能力的唯一入口：注册工具、校验 Schema、计算权限、选择
Executor、请求确认、注入最小目录和临时 Secret、收集结果、清理环境并记录审计。

## 7. 身份、Session 与本地数据

必须拆分以下概念：

| 概念 | 存储位置 | 用途 |
|---|---|---|
| AuthSession | 系统凭据存储 + 内存 | OpenRosalind 登录状态 |
| Project | 本地 SQLite | 项目、授权目录和默认配置 |
| Conversation | 本地 SQLite | 对话消息和上下文 |
| AgentJob | 本地 SQLite | 一次 Agent 任务及步骤状态 |
| ToolRun | 本地 SQLite | 一次工具执行和审计记录 |
| Artifact | 本地文件 + SQLite 索引 | 报告、代码、数据和结果 |

服务端不需要为每个 Conversation 或 AgentJob 建立业务 Session。OpenRosalind
Control Plane 第一阶段只提供登录、Token、用户、组织、订阅、设备授权、客户端
版本和可选同步。访问 Token 短期有效，刷新凭据存入系统凭据存储。

当前 macOS 实现已将 UI 对话和消息从 WebKit `localStorage` 迁入 Desktop Core
SQLite schema v5。UI Chat 与执行审计使用的 Conversation 分表保存，避免清理聊天
时级联删除 AgentJob。写入采用按用户隔离的完整快照事务；首次升级会只读扫描本
应用自己的旧 WebKit LocalStorage，按 Chat ID 合并最新记录，成功导入后不再重复
覆盖。`localStorage` 仅保留当前来源的容灾副本，不是桌面版权威数据源。

## 8. 模型配置与凭据

Provider Profile 包含 Provider 类型、Base URL、Model、API Key 引用、模型能力、
默认设置和连接状态。SQLite 只保存 Key 的引用 ID，不保存 Key 明文。

| 能力 | macOS | Windows |
|---|---|---|
| 模型 Key | Keychain | Credential Manager / DPAPI |
| Auth Token | Keychain | Credential Manager / DPAPI |
| 临时 Secret | 内存或受控管道 | 内存或受控管道 |

Secret 不通过命令行参数传递，不输出到日志，不永久写入容器环境。

## 9. Agent 与任务生命周期

Conversation 只是逻辑上下文，不对应进程或容器。

~~~mermaid
sequenceDiagram
    participant U as User
    participant UI as UI
    participant C as Desktop Core
    participant A as Agent Worker
    participant T as Tool Manager

    U->>UI: 提交任务
    UI->>C: 创建 AgentJob
    C->>A: 上下文与能力列表
    A->>C: 任务计划
    C->>UI: 展示计划
    A->>T: 调用 Tool Contract
    T->>UI: 必要时请求权限
    U->>UI: 允许 / 拒绝
    T->>T: 选择 Executor 并执行
    T->>A: 结构化结果和 Artifact
    A->>C: 最终结果
    C->>UI: 展示并持久化
~~~

Agent Worker 在应用生命周期内复用。每个 AgentJob 拥有独立的取消信号、工作目录、
权限快照、临时文件、工具记录、Artifact 和资源预算。

## 10. Tool Contract

Docker 是 Executor，不是扩展协议。所有工具统一使用 Tool Contract。

示例：

    {
      "schemaVersion": 1,
      "name": "blast.search",
      "version": "1.0.0",
      "executor": {
        "type": "container",
        "image": "ghcr.io/openrosalind/blast@sha256:REQUIRED_DIGEST"
      },
      "inputSchema": "schemas/input.json",
      "outputSchema": "schemas/output.json",
      "permissions": {
        "filesystem": [
          {"scope": "job-input", "mode": "read"},
          {"scope": "job-output", "mode": "write"}
        ],
        "network": "none",
        "secrets": []
      },
      "resources": {
        "timeoutSeconds": 600,
        "memoryMb": 4096,
        "cpu": 4,
        "maxOutputMb": 1024
      }
    }

正式 Schema 还应支持平台、CPU、入口、健康检查、数据包、Artifact、域名白名单、
GPU、许可证、镜像签名、升级和回滚策略。

## 11. Executor 设计

### 11.1 Native Executor

适合文件转换、Git、轻量 Python/R/Node 和可信本地科研工具。必须使用独立进程组、
固定工作目录、环境变量白名单、超时、取消、输出限制和目录权限检查。

### 11.2 Container Executor

适合不可信代码、强依赖科研软件和可复现任务。默认策略：

- 非 privileged、非 root；
- 不挂载 Docker Socket 和整个 Home；
- 只读根文件系统；
- 输入只读，输出可写；
- 默认无网络；
- 限制 CPU、内存、进程数、磁盘和时间；
- 镜像固定 digest；
- 任务完成后删除容器。

当前 alpha 已实现首个 `python.container`：Desktop Core 只接受注册表内固定 digest，
容器启动参数由 Rust 生成而不是由 WebView 或 Agent 拼接；镜像缺失时必须先经过 Rust
触发的原生系统确认对话框，实际运行使用 `--pull=never`。输入目录只读、输出目录可写，不挂载项目目录、
Home、Docker Socket 或系统凭据。macOS 与 Windows 共用该策略，Docker Desktop 仅是
可选能力。

### 11.3 Compose Executor

适合 analysis-worker、数据库、向量服务等多服务工具包。每个 Compose 项目使用
独立名称、网络、Volume 和资源限制，由 Tool Manager 负责健康检查和生命周期。

### 11.4 Remote Executor

用于可选远程算力或机构计算节点。执行前必须展示上传数据、目标服务、费用和数据
处理政策。

## 12. Docker 工具生命周期

| 类型 | 生命周期 | 示例 |
|---|---|---|
| 一次性容器 | 单个 ToolRun | 用户代码、一次性分析 |
| 项目容器 | Project 打开期间 | Jupyter Kernel、项目数据库 |
| 常驻服务 | 用户显式启用期间 | BLAST 服务、向量索引 |
| Compose 工具包 | 工具包启用期间 | 多服务科研流水线 |

Docker 缺失时，登录、对话和 Native Tools 仍可使用；Container Tools 显示不可用
和安装说明，不静默改用风险更高的 Native Executor。

## 13. 权限模型

| 等级 | 示例 | 默认行为 |
|---|---|---|
| 低 | 读取已授权项目、解析文本 | 项目授权范围内自动执行 |
| 中 | 修改项目文件、创建报告 | 展示变更范围，可按任务授权 |
| 高 | Shell、安装依赖、访问网络 | 每次或按规则明确确认 |
| 极高 | 项目外目录、上传敏感数据 | 逐次确认并说明目标 |

用户通过原生目录选择器选择 Project Root：

| 能力 | macOS | Windows |
|---|---|---|
| 目录选择 | NSOpenPanel/Tauri Dialog | Windows Picker/Tauri Dialog |
| 持久授权 | Security-scoped bookmark | 路径授权 + ACL/应用策略 |
| 文件监控 | FSEvents/notify | ReadDirectoryChangesW/notify |

当前 alpha 已实现项目目录授权的第一阶段：目录只能经 Desktop Core 调起的原生选择器
授予，授权按 Project ID 写入本地 SQLite，并支持可用性检查、在系统文件管理器中显示和
撤销。磁盘根目录、整个用户主目录以及已绑定其他项目的目录会被拒绝。当前只有
`project.files.list` 和 `project.file.read` 两个低风险只读 Tool Contract 可以按
AgentJob 的项目关系消费授权；写入工具、Python 和 Agent Worker 不会因为目录已授权就
自动获得访问权。macOS 当前为非 App Sandbox 发行方式，使用持久路径策略；
进入 App Sandbox 发行渠道前需要升级为 security-scoped bookmark。

模型 Provider 网络权限和工具网络权限必须分开管理。

## 14. 本地存储

    Application Data/
    ├── openrosalind.db
    ├── projects/
    ├── jobs/
    ├── artifacts/
    ├── tool-cache/
    ├── container-state/
    └── logs/

- macOS：~/Library/Application Support/bio.openrosalind.desktop/
- Windows：%APPDATA%\bio.openrosalind.desktop\

数据库只保存必要索引和非 Secret 配置。用户项目保留在用户选择的目录中，日志默认
脱敏，并提供清理、导出和保留周期设置。

## 15. macOS 与 Windows 复用边界

| 模块 | 复用方式 |
|---|---|
| Web UI | 完全共享 |
| Agent Worker | 完全共享 |
| Skills 和 Tool Contract | 完全共享 |
| Provider Broker | 核心共享，凭据适配不同 |
| Tool Manager | 核心共享，进程和路径适配不同 |
| SQLite 和 Artifact | 完全共享 |
| Native Executor | 策略共享，命令和进程适配不同 |
| Container/Compose | 协议共享，Docker 探测适配不同 |
| 更新系统 | 流程共享，包格式和签名不同 |

建议目录：

    desktop/src-tauri/src/
    ├── core/
    ├── auth/
    ├── provider/
    ├── agent/
    ├── tools/
    ├── storage/
    └── platform/
        ├── macos/
        └── windows/

| 领域 | macOS | Windows |
|---|---|---|
| WebView | 系统 WebKit | WebView2 |
| 凭据 | Keychain | Credential Manager / DPAPI |
| 目录授权 | Security-scoped bookmark | Picker + ACL/策略 |
| IPC | Unix Socket/stdio | Named Pipe/stdio |
| 进程清理 | Process Group/Signal | Job Object |
| 包格式 | .app、.dmg | .msi、.exe |
| 签名 | Developer ID + notarization | Authenticode |
| CPU | arm64、x86_64 | x86_64，后续 arm64 |

Alpha 阶段可以继续使用 desktop-alpha 和 desktop-mac 并行验证；本地核心接口
稳定后，应合并到统一桌面主线，只保留平台配置、流水线和适配代码差异。

## 16. 安全与供应链

- Tool manifest、Skill 和镜像均需来源与版本信息；
- 官方镜像固定 digest，并考虑签名验证；
- 第三方工具安装前显示发布者、权限和数据范围；
- 工具更新不能自动扩大权限；
- Agent 不得修改权限数据库和确认记录；
- Docker daemon、Keychain 和 Auth Token 只由 Desktop Core 访问；
- Prompt 中的命令和权限要求不构成用户授权；
- 上传文件或远程执行必须在执行时确认；
- 审计记录包含计划、工具、参数摘要、确认、结果和文件变更；
- API Key、Token 和用户文件内容默认不进入遥测。

## 17. 发布与更新

macOS 分别构建 arm64、x86_64，处理 bundled Python、Developer ID、Hardened
Runtime、notarization、stapling、.app 和 .dmg。Windows 首发 x86_64，处理
WebView2、嵌入 Python、Authenticode、.msi/NSIS 和升级卸载验证。

更新清单由 OpenRosalind Control Plane 提供。客户端必须验证签名、版本、平台和
架构，更新失败时保留可回滚版本。

当前 macOS alpha.6 已将固定 SHA-256 的 arm64/x86_64 独立 CPython 3.11 与
哈希锁定的 Python wheels 纳入 `.app`/`.dmg`。Release 模式只接受签名包内与应用
架构匹配的解释器，缺失时失败关闭，不再搜索 Homebrew、Xcode Python、用户目录或
`PATH`。Desktop Core 同时提供事务迁移、启动完整性校验和最多五份经过完整性验证的
在线 SQLite 快照。正式发行仍需 Developer ID、公证、stapling、Intel 真机和干净
系统验证。

## 18. 从当前 Alpha 的迁移计划

### Phase 1：可信本地边界

- 将固定 loopback 高权限接口迁移到 Tauri IPC；
- 建立 Desktop Core 模块边界；
- 建立 Project、Conversation、AgentJob、ToolRun 数据模型；
- 建立 Agent Worker 受控通信和崩溃恢复；
- 保持当前 UI 和 Python 能力可运行。

### Phase 2：认证与模型直连

- 接入 OpenRosalind Control Plane 登录；
- Auth Token 存入系统凭据存储；
- 实现 Provider Profile、Credential Vault 和 Provider Broker；
- 移除对 OpenRosalind 模型代理服务的依赖；
- 增加离线和凭据失效行为。

### Phase 3：本地 Agent 与权限

- Agent Worker 改为本地常驻；
- Conversation 与 AgentJob 解耦；
- 实现项目目录原生授权；
- 实现权限确认、规则和审计；
- 实现进程组、取消、超时和资源限制。

### Phase 4：工具系统

- 定义 Tool Contract JSON Schema；
- 实现 Native、Container 和 Compose Executor；
- 建设官方科研工具包；
- 增加镜像、数据包和 Artifact 管理。

### Phase 5：发行质量

- 嵌入 Python runtime；
- 完成 macOS arm64/x86_64 和 Windows x86_64 验证；
- 完成 Apple 签名、公证和 Windows 签名；
- 建立更新、回滚、崩溃恢复和兼容性测试；
- 完成干净机器安装和卸载测试。

## 19. Desktop Local v1 验收标准

- 用户可以通过 OpenRosalind 账号登录；
- 用户可以配置模型 Provider，Key 存入系统凭据存储；
- 模型调用不经过 OpenRosalind 模型代理；
- 对话、项目和任务默认只保存在本地；
- 主 Agent 不依赖 Docker；
- Conversation 可执行多个 AgentJob，而不创建对应容器；
- 用户可以授权项目目录并撤销授权；
- Native Tool 和 Docker Tool 使用同一 Tool Contract；
- Docker 缺失时基础功能可用；
- 高风险工具执行前获得明确确认；
- 任务可以取消，退出后不残留进程和临时容器；
- 模型 Key、Auth Token 和敏感文件不出现在日志中；
- macOS 和 Windows 共享 Agent、Tool Contract 和数据模型测试；
- macOS arm64、x86_64 和 Windows x86_64 有独立构建验证结果。

## 20. 待决策事项

1. 登录首版使用邮箱密码 API、系统浏览器 OAuth/PKCE，还是两者兼容；
2. Agent Worker 与 Desktop Core 使用 stdio、Socket/Named Pipe 还是受保护 HTTP；
3. Provider Broker 完全由 Rust 实现，还是保留受控 Python Adapter；
4. Native Executor 首版允许的命令范围和默认网络策略；
5. 官方 Tool Pack 的签名、仓库、升级和审核机制；
6. Docker、OrbStack、Podman 的兼容范围；
7. 本地数据库是否提供用户可选加密；
8. 云同步的加密模型和默认关闭策略；
9. macOS 长期分别发布 arm64/x86_64，还是提供 Universal 包；
10. Windows arm64 的优先级。

以上待决策项不能阻塞 Phase 1 的可信本地边界建设。
