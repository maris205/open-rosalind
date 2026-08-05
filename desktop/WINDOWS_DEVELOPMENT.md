# OpenRosalind Windows 开发说明

桌面版使用 Tauri 2 作为桌面壳，复用仓库中的 Web UI、Python API、Agent、Skills
和生物医学工具。开发时本地服务只监听 `127.0.0.1:18765`，不依赖 Redis，
Docker 也是可选能力。

当前 Alpha 仍调用 Windows 上已经安装的 Python。面向普通用户发布前，会将
Python 解释器一并打入安装包，最终用户不需要单独配置开发环境。

## 是否需要迁移聊天 Session

不需要迁移当前与开发助手的聊天 session。开发上下文通过以下内容传递：

- Git 的 `desktop-alpha` 分支和提交记录；
- 本文档及 `desktop/README.md`；
- 仓库中的测试用例；
- Issue 或开发日志中尚未完成的任务。

Web 站点中的用户聊天记录也不建议复制到开发机。桌面开发环境使用独立的
SQLite 数据库，避免真实用户数据进入本地调试环境。

## 1. 安装开发环境

建议使用 Windows 11，并安装以下工具：

1. Git for Windows。
2. Node.js 20 LTS 或更高版本。
3. Python 3.10 或 3.11，安装时勾选 `Add python.exe to PATH`。
4. Rust stable MSVC 工具链。
5. Visual Studio 2022 Build Tools，勾选 `Desktop development with C++`，
   并确保包含 MSVC v143 和 Windows 10/11 SDK。
6. Microsoft Edge WebView2 Runtime。Windows 11 通常已预装。

安装 Rust 后，在 PowerShell 中确认使用 MSVC 工具链：

```powershell
rustup default stable-msvc
rustc --version
cargo --version
```

确认其他工具：

```powershell
git --version
node --version
npm --version
python --version
```

## 2. 获取代码

待 `desktop-alpha` 分支推送到远端后执行：

```powershell
git clone git@github.com:maris205/open-rosalind.git
Set-Location open-rosalind
git fetch origin
git switch --track origin/desktop-alpha
```

如果本地已经有仓库：

```powershell
git fetch origin
git switch desktop-alpha
git pull --ff-only
```

不要在 Windows 与服务器之间复制整个工作目录，也不要复制 `node_modules`、
Rust `target`、SQLite 数据库或聊天 session。这些内容均应在 Windows 本机生成。

## 3. 安装依赖

在仓库根目录打开 PowerShell：

```powershell
npm install
npm install --prefix desktop
```

桌面启动和构建命令会自动执行 `npm --prefix desktop run runtime:prepare`，将
`requirements.txt` 中的 Python 包安装到 `desktop/python-packages`。

如果机器上存在多个 Python，明确指定解释器：

```powershell
$env:OPENROSALIND_PYTHON = "C:\Users\your-name\AppData\Local\Programs\Python\Python311\python.exe"
& $env:OPENROSALIND_PYTHON --version
```

这个环境变量只在当前 PowerShell 窗口生效，适合开发调试。

## 4. 启动桌面开发版

```powershell
$env:OPENROSALIND_PYTHON = "C:\Path\To\python.exe"
npm run desktop:dev
```

启动后 Tauri 会拉起本地 Python sidecar，并打开桌面窗口。API 地址为：

```text
http://127.0.0.1:18765
```

关闭桌面窗口后，sidecar 应同步退出并释放端口。

模型配置可以在应用的“设置”中填写；该方式输入的临时 API Key 只保存在当前
桌面进程中。开发环境也可沿用仓库 `.env.example` 中列出的环境变量，但不要
把真实密钥提交到 Git。

## 5. 构建 Windows 安装包

```powershell
$env:OPENROSALIND_PYTHON = "C:\Path\To\python.exe"
npm run desktop:build
```

构建产物位于：

```text
desktop\src-tauri\target\release\bundle\msi\
desktop\src-tauri\target\release\bundle\nsis\
```

Alpha 安装包目前仍要求目标机器安装 Python 3.10+。公开分发前还需要完成
Windows Python 嵌入、代码签名和干净虚拟机安装测试。

## 6. 运行测试

先安装 Playwright 浏览器：

```powershell
npx playwright install chromium
```

运行 Python 测试：

```powershell
$env:PYTHONPATH = (Get-Location).Path
python -m unittest discover -s tests/python -p "test_*.py"
```

运行桌面交互测试时，先在一个 PowerShell 窗口保持 `npm run desktop:dev`
运行，再在另一个窗口执行：

```powershell
$env:ROSALIND_DESKTOP_TEST = "1"
$env:ROSALIND_WEB_BASE_URL = "http://127.0.0.1:18765"
npx playwright test tests/web/desktop.spec.js
```

构建前也建议执行：

```powershell
Set-Location desktop\src-tauri
cargo check
Set-Location ..\..
```

## 7. 本地数据和安全边界

桌面数据默认位于：

```text
%APPDATA%\bio.openrosalind.desktop\
```

其中包括 `rosalind.db`、任务产物和 Agent workspace。开发时可以使用测试账号，
但不要把该目录提交到 Git。当前 Agent 默认只能使用应用自己的 workspace；
原生项目目录选择和逐次权限授权仍属于后续桌面里程碑。

无 Docker 模式下，经过用户确认的 Python 代码会由本机 Python 执行。这不是
操作系统级沙箱，执行界面必须保留确认提示。Docker 可作为需要更强隔离时的
可选增强，但不影响普通桌面启动。

## 8. 常见问题

### `python` 找不到或版本不对

用 `where.exe python` 查看解释器，并通过 `OPENROSALIND_PYTHON` 指向 Python
3.10/3.11 的完整路径。

### 端口 18765 已被占用

```powershell
Get-NetTCPConnection -LocalPort 18765 -ErrorAction SilentlyContinue
```

先关闭旧的 OpenRosalind 进程。临时调试也可换端口：

```powershell
$env:OPENROSALIND_DESKTOP_PORT = "18766"
npm run desktop:dev
```

### Rust 链接失败或找不到 Windows SDK

重新打开 Visual Studio Installer，确认安装了 `Desktop development with C++`、
MSVC v143 和 Windows SDK，然后重启 PowerShell。

### WebView2 缺失或窗口空白

安装 Microsoft Edge WebView2 Evergreen Runtime，重启应用后再试。

### Python 依赖安装失败

```powershell
$env:OPENROSALIND_PYTHON = "C:\Path\To\python.exe"
npm --prefix desktop run runtime:prepare
```

先看 pip 输出中的具体包和网络错误。`desktop/python-packages` 是生成目录，失败后
可以删除该目录并重新执行准备命令。

## 下一阶段开发顺序

1. 将 Python 解释器嵌入 Windows 安装包，移除最终用户的 Python 前置要求。
2. 增加原生目录选择，只向 Agent 授权用户明确选择的项目目录。
3. 完善无 Docker 本机工具执行器、权限确认和审计记录。
4. 在干净 Windows 虚拟机验证安装、升级、卸载和数据保留。
5. 配置 Windows 代码签名，再发放 ToC 内测安装包。
