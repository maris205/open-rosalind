# 给 Windows Codex CLI 的 OpenRosalind 开发交接说明

这份文件用于直接交给 Windows 上运行的 Codex CLI。不要迁移服务器上的聊天
session，也不要复制 Linux 工作目录；只需要 clone `desktop-alpha` 分支，
让 Codex 读取仓库中的代码、测试和本文档即可。

## 启动 Codex CLI

在 PowerShell 中执行：

```powershell
cd $HOME
git clone --branch desktop-alpha https://github.com/maris205/open-rosalind.git
cd open-rosalind
codex
```

如果仓库已经存在：

```powershell
cd $HOME\open-rosalind
git fetch origin
git switch desktop-alpha
git pull --ff-only origin desktop-alpha
codex
```

建议从仓库根目录启动 Codex CLI，这样它可以同时看到 `web_app`、`desktop`、
`.openhands/skills` 和 `tests`。

## 第一次发给 Codex 的上下文

启动后，把下面这段直接发送给 Windows Codex CLI：

```text
你现在在 Windows 上维护 OpenRosalind 桌面版，请先阅读：

- desktop/README.md
- desktop/WINDOWS_DEVELOPMENT.md
- desktop/WINDOWS_CODEX.md
- README.md
- docs/safety.md

当前工作分支是 desktop-alpha。桌面版使用 Tauri 2，复用 web_app 的 Web UI、
Python API、Agent、Skills 和生物医学工具。桌面 sidecar 只绑定
127.0.0.1 的随机端口，并使用每次启动随机生成的传输令牌；默认使用进程内任务队列，不要求 Redis；Docker 是可选能力。

请遵守以下规则：

1. 先检查 git status、当前分支和最近提交，再开始修改。
2. 不要迁移聊天 session，不要复制 Linux 服务器工作目录。
3. 不要读取、提交或输出真实 API Key、密码、证书和用户数据。
4. 不要删除或回退已有用户修改；只修改与当前任务相关的文件。
5. 使用 apply_patch 或等价的安全补丁方式编辑文件。
6. 修改后运行相关 Python 测试、cargo check 或 Playwright 测试。
7. 报告中明确列出修改文件、测试结果、未解决问题和下一步建议。

开始前先给出简短检查结果和实施计划，不要立即大范围重构。
```

## Windows 环境变量

如果机器上有多个 Python，先在 Codex 所在的 PowerShell 窗口设置：

```powershell
$env:OPENROSALIND_PYTHON = "C:\Path\To\Python311\python.exe"
& $env:OPENROSALIND_PYTHON --version
```

桌面开发端口默认随机分配。仅在调试或自动化测试需要固定地址时设置：

```powershell
$env:OPENROSALIND_DESKTOP_PORT = "18765"
$env:OPENROSALIND_DESKTOP_TEST_TOKEN = "desktop-e2e-only-not-for-production"
```

需要强制重新准备 Python 依赖时：

```powershell
npm --prefix desktop run runtime:force
```

## 给 Codex 的常用任务模板

### 启动并做基础检查

```text
请先检查当前分支、git status、Node/Python/Rust 版本和 loopback 端口。
然后安装缺失的 Node 依赖，准备桌面 Python runtime，运行 cargo check 和
Python 单测。不要修改业务代码，只报告问题。
```

### 启动桌面版

```text
请启动 OpenRosalind Tauri 桌面开发版。使用当前 PowerShell 中的
OPENROSALIND_PYTHON，确保 sidecar 只监听 127.0.0.1。启动后检查
/api/config、/api/desktop/status 和 /api/queue/status，并报告窗口和端口状态。
```

对应命令通常是：

```powershell
npm install
npm install --prefix desktop
npm run desktop:dev
```

### 运行自动化测试

```text
请运行与本次修改相关的最小测试集合；如果涉及桌面启动、登录、任务队列或
本机 Python 执行，再运行 tests/web/desktop.spec.js。不要因为测试失败就删除
测试或放宽断言，先定位原因。
```

命令：

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m unittest discover -s tests/python -p "test_*.py"

# 启动桌面 Debug 进程的终端也必须使用下面两个 OPENROSALIND 变量
$env:OPENROSALIND_DESKTOP_PORT = "18765"
$env:OPENROSALIND_DESKTOP_TEST_TOKEN = "desktop-e2e-only-not-for-production"
$env:ROSALIND_DESKTOP_TEST = "1"
$env:ROSALIND_WEB_BASE_URL = "http://127.0.0.1:18765"
npx playwright test tests/web/desktop.spec.js
```

### 构建 Windows 安装包

```text
请在确认测试通过后构建 Windows MSI/NSIS 安装包。先运行 cargo check，
再执行 npm run desktop:build。报告安装包路径、大小，以及当前仍需要系统
Python 的限制。不要签名或发布安装包，除非我明确授权。
```

## Codex 工作边界

Windows Codex 可以直接修改仓库代码、运行本地测试、启动桌面 sidecar 和生成
本地构建产物。以下内容需要先得到明确授权：

- 推送远端分支、创建 Pull Request 或发布 Release；
- 修改服务器部署、域名、证书和生产环境变量；
- 访问用户真实数据或复制生产数据库；
- 执行可能影响系统或其他项目的高权限命令；
- 把 Python 本机执行扩展到用户未明确授权的目录。

## 每次任务结束时让 Codex 输出

```text
请用以下格式收尾：

1. 结果：完成 / 部分完成 / 阻塞
2. 修改文件：列出相对路径
3. 验证：列出实际运行的命令和通过/失败结果
4. 风险或未解决问题：简短说明
5. 下一步：只给一到三项建议
```

## 当前开发顺序

1. 在 Windows 验证 Tauri 开发启动、登录、Agent 和生物医学工具。
2. 验证 MSI/NSIS 安装、升级、卸载和 `%APPDATA%` 数据保留。
3. 嵌入 Windows Python runtime，移除最终用户的 Python 前置要求。
4. 增加原生项目目录选择和逐次权限确认。
5. 完成代码签名后再发布 ToC 内测包。
