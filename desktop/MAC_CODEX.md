# 给 macOS Codex CLI 的 OpenRosalind 开发交接说明

macOS 端与 Windows 端共用同一套 Web UI、Python API、Agent、Skills 和生物医学
工具。不要迁移聊天 session，也不要复制 Linux/Windows 的运行目录；从 Git 分支
重新获取代码即可。

## 1. 获取代码并创建 macOS 分支

在 Terminal 中执行：

```bash
cd "$HOME"
git clone --branch desktop-alpha https://github.com/maris205/open-rosalind.git
cd open-rosalind
git switch -c desktop-mac
codex
```

如果仓库已经存在：

```bash
cd "$HOME/open-rosalind"
git fetch origin
git switch desktop-alpha
git pull --ff-only origin desktop-alpha
git switch -c desktop-mac
codex
```

Codex 完成首次检查后，明确要求它创建远端分支：

```text
请确认当前是从 desktop-alpha 创建的 desktop-mac 分支。完成首轮检查后，
如果工作区干净，请执行 git push -u origin desktop-mac；后续 macOS 改动只在
desktop-mac 分支提交，不要修改 desktop-alpha。
```

## 2. macOS 开发环境

安装以下工具：

- Xcode 或 Xcode Command Line Tools；
- Homebrew（建议）；
- Node.js 20 LTS+；
- Python 3.10 或 3.11；
- Rust stable；
- macOS 使用系统 WebKit，不需要额外安装 WebView2。

检查 Xcode 工具链：

```bash
xcode-select --install
xcode-select -p
```

检查版本：

```bash
git --version
node --version
npm --version
python3 --version
rustc --version
cargo --version
```

Apple Silicon 和 Intel 都可以开发。Apple Silicon 建议使用 arm64 原生 Node、
Python 和 Rust，不要混用 Rosetta 与原生工具链。

## 3. 给 macOS Codex CLI 的初始化提示词

启动 Codex 后直接发送：

```text
你现在在 macOS 上维护 OpenRosalind 桌面版，请先阅读：

- desktop/README.md
- desktop/WINDOWS_DEVELOPMENT.md（了解共用桌面架构）
- desktop/MAC_CODEX.md
- README.md
- docs/safety.md

当前应在 desktop-mac 分支上工作，该分支从 desktop-alpha 创建。桌面版使用
Tauri 2，复用 web_app 的 Web UI、Python API、Agent、Skills 和生物医学工具。
sidecar 只监听 127.0.0.1:18765，默认使用进程内任务队列，不要求 Redis；
Docker 是可选能力。

规则：
1. 先检查 git status、分支、最近提交和 CPU 架构。
2. 不要迁移聊天 session，不要复制其他机器的运行目录或数据库。
3. 不要读取、提交或输出真实 API Key、密码、证书和用户数据。
4. 不要删除或回退已有修改，只改与当前任务相关的文件。
5. 修改后运行相关 Python 测试、cargo check 或 Playwright 测试。
6. 最后报告修改文件、测试结果、未解决问题和下一步建议。

开始前先给出检查结果和简短计划，不要立即大范围重构。
```

## 4. 配置 Python 和启动

macOS 通常使用 `python3`。如果有多个版本，明确指定：

```bash
export OPENROSALIND_PYTHON="$(which python3)"
"$OPENROSALIND_PYTHON" --version
```

安装 Node 依赖并准备 Python runtime：

```bash
npm ci
npm ci --prefix desktop
export OPENROSALIND_PYTHON="/absolute/path/to/python3.11"
npm --prefix desktop run runtime:prepare
```

runtime 准备脚本会拒绝 Python 3.9 及更旧版本，也会在 macOS 上拒绝 Node 与
Python 架构不一致的组合。缓存包含 Python 版本与 CPU 架构；切换 Rosetta、
Python 版本或 CPU 架构时会自动重建，避免遗留不兼容的原生模块。

启动桌面开发版：

```bash
npm run desktop:dev
```

本地 API 仍然是 `http://127.0.0.1:18765`。端口冲突时：

```bash
export OPENROSALIND_DESKTOP_PORT=18766
npm run desktop:dev
```

## 5. 测试和构建

```bash
export PYTHONPATH="$PWD:$PWD/desktop/python-packages"
"$OPENROSALIND_PYTHON" -m unittest discover -s tests/python -p 'test_*.py'

npx playwright install chromium
export ROSALIND_DESKTOP_TEST=1
export ROSALIND_WEB_BASE_URL=http://127.0.0.1:18765
npx playwright test tests/web/desktop.spec.js

cargo check --manifest-path desktop/src-tauri/Cargo.toml
npm run desktop:build:macos
```

分别构建原生架构：

```bash
# 在 Apple Silicon + arm64 Node/Python/Rust 上执行
npm run desktop:build:macos:arm64

# 在 Intel Mac + x86_64 Node/Python/Rust 上执行
npm run desktop:build:macos:x64
```

Tauri 壳支持 universal target，但当前 Alpha 打包的 Python 第三方模块仍可能含有
单架构二进制，因此 universal 命令只用于构建验证，不能替代 arm64 和 x86_64
真机包及真机测试：

```bash
rustup target add aarch64-apple-darwin x86_64-apple-darwin
npm run desktop:build:macos:universal
```

在无 Finder 会话的 CI 或自动化环境中，可把 `--ci` 传给底层 Tauri 命令，跳过
DMG 的 Finder 美化步骤：

```bash
npm --prefix desktop run build:macos -- --ci
```

构建产物通常位于：

```text
desktop/src-tauri/target/release/bundle/macos/*.app
desktop/src-tauri/target/release/bundle/dmg/*.dmg
```

当前 Alpha 仍需要系统 Python。正式发布前需要嵌入 macOS Python runtime、
处理 Apple 签名/公证，并分别验证 arm64 和 x86_64 包。

## 6. Apple 签名与公证

`tauri.macos.conf.json` 已启用 hardened runtime，并使用最小权限的空
`Entitlements.plist`。未签名本地构建仅用于开发测试，不能直接作为面向用户的
正式安装包分发。

签名与公证使用 Tauri/CI 环境变量注入，不写入仓库：

- 签名证书：`APPLE_CERTIFICATE`、`APPLE_CERTIFICATE_PASSWORD`，或本机
  Keychain 中证书对应的 `APPLE_SIGNING_IDENTITY`；
- App Store Connect API：`APPLE_API_ISSUER` 和 `APPLE_API_KEY` 或
  `APPLE_API_KEY_PATH`；
- Apple ID 方式：`APPLE_ID`、`APPLE_PASSWORD`、`APPLE_TEAM_ID`。

正式发布流水线必须对 `.app` 和 `.dmg` 执行 `codesign --verify`，提交 Apple
notary service，等待成功后 staple，并在未配置凭据时失败关闭。不要在命令输出、
GitHub Actions 日志或构建产物中暴露凭据。

## 7. 给 Codex 的 macOS 任务模板

```text
请在 desktop-mac 分支完成本次 macOS 任务。先检查 git status、CPU 架构、
Node/Python/Rust 版本和 18765 端口。只修改相关文件，完成后运行最小必要测试。
如果涉及桌面壳，请至少运行 cargo check；如果涉及登录、队列或本机执行，请运行
tests/web/desktop.spec.js。不要自动推送、创建 PR、签名或发布安装包，除非我明确授权。
```

任务结束时要求 Codex 输出：

```text
1. 结果：完成 / 部分完成 / 阻塞
2. 修改文件：相对路径
3. 验证：实际命令及通过/失败结果
4. 分支和提交：当前分支、commit；如已授权则说明 push 状态
5. 风险或未解决问题
6. 下一步建议
```

## 8. macOS 本地数据

桌面数据由 Tauri 写入 macOS 应用数据目录，通常位于：

```text
~/Library/Application Support/bio.openrosalind.desktop/
```

不要把该目录、聊天记录、真实密钥或 `desktop/src-tauri/target` 提交到 Git。
