# Open-Rosalind Edu 部署说明

本文说明如何在 Windows、本地 Linux 和阿里云 ECS 上部署 Open-Rosalind Edu Web UI。

## 1. 部署范围

当前 Edu Web 服务包含：

- 单聊天框科研助手界面
- 生物医学论文工作流 Skills
- PDF、DOCX、BibTeX 和文本文件解析
- DOI、PMID 与参考文献元数据核验
- OpenAI 兼容模型接口，默认使用 Qwen

当前服务基于 Python `ThreadingHTTPServer`，适合本地使用、开发和小范围内测。面向公网正式运营前，应补充用户认证、数据库、限流、文件隔离、审计、任务队列和更完整的应用服务器架构。

## 2. 环境要求

- Python 3.10 或更高版本
- Git
- 可访问 Qwen OpenAI 兼容接口的网络
- Windows、Linux 或 macOS

推荐服务器环境：

- Ubuntu 22.04/24.04 LTS
- 2 核 CPU、4 GB 内存起步
- 40 GB 以上磁盘
- Nginx
- 域名与 HTTPS 证书（公网部署时）

模型推理通过 API 完成，因此 Edu Web 服务不需要 GPU。

## 3. 本地部署

### Windows PowerShell

```powershell
git clone -b edu https://github.com/maris205/open-rosalind.git
cd open-rosalind

python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt

$env:DASHSCOPE_API_KEY="your_dashscope_api_key"
$env:QWEN_BASE_URL="https://llm-jl24o09ebj303z4e.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
$env:QWEN_MODEL="qwen3.7-max"

.\scripts\start_web.ps1
```

访问：

```text
http://127.0.0.1:8765/
```

### Linux/macOS

```bash
git clone -b edu https://github.com/maris205/open-rosalind.git
cd open-rosalind

python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt

export DASHSCOPE_API_KEY="your_dashscope_api_key"
export QWEN_BASE_URL="https://llm-jl24o09ebj303z4e.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
export QWEN_MODEL="qwen3.7-max"

python web_app/server.py --host 127.0.0.1 --port 8765
```

未配置 API Key 时，页面仍可启动，但模型调用进入 Prompt-only 模式。

## 4. 阿里云 ECS 部署

### 4.1 安装系统依赖

以下命令以 Ubuntu 为例：

```bash
sudo apt update
sudo apt install -y git python3 python3-venv python3-pip nginx
```

创建独立服务用户：

```bash
sudo useradd --system --create-home --shell /usr/sbin/nologin rosalind
sudo mkdir -p /opt/open-rosalind
sudo chown rosalind:rosalind /opt/open-rosalind
```

### 4.2 获取 Edu 分支

```bash
sudo -u rosalind git clone -b edu https://github.com/maris205/open-rosalind.git /opt/open-rosalind
cd /opt/open-rosalind

sudo -u rosalind python3 -m venv .venv
sudo -u rosalind .venv/bin/python -m pip install --upgrade pip
sudo -u rosalind .venv/bin/pip install -r requirements.txt
```

### 4.3 配置模型密钥

创建仅 root 可读的环境文件：

```bash
sudo install -m 600 -o root -g root /dev/null /etc/open-rosalind-edu.env
sudo nano /etc/open-rosalind-edu.env
```

写入：

```dotenv
DASHSCOPE_API_KEY=replace_with_new_key
QWEN_BASE_URL=https://llm-jl24o09ebj303z4e.cn-beijing.maas.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen3.7-max
```

不要把真实 Key 写入 Git、README、Docker 镜像、前端代码或聊天记录。已经公开过的 Key 应立即撤销并重新生成。

### 4.4 创建 systemd 服务

创建 `/etc/systemd/system/open-rosalind-edu.service`：

```ini
[Unit]
Description=Open-Rosalind Edu Web UI
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=rosalind
Group=rosalind
WorkingDirectory=/opt/open-rosalind
EnvironmentFile=/etc/open-rosalind-edu.env
ExecStart=/opt/open-rosalind/.venv/bin/python /opt/open-rosalind/web_app/server.py --host 127.0.0.1 --port 8765
Restart=on-failure
RestartSec=3
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=full
ProtectHome=true

[Install]
WantedBy=multi-user.target
```

启动服务：

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now open-rosalind-edu
sudo systemctl status open-rosalind-edu
```

本机验证：

```bash
curl -I http://127.0.0.1:8765/
curl http://127.0.0.1:8765/api/config
```

### 4.5 配置 Nginx

创建 `/etc/nginx/sites-available/open-rosalind-edu`：

```nginx
server {
    listen 80;
    server_name edu.example.com;

    client_max_body_size 12m;

    location / {
        proxy_pass http://127.0.0.1:8765;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 180s;
    }
}
```

启用配置：

```bash
sudo ln -s /etc/nginx/sites-available/open-rosalind-edu /etc/nginx/sites-enabled/open-rosalind-edu
sudo nginx -t
sudo systemctl reload nginx
```

阿里云安全组只需开放：

- `22/tcp`：SSH，建议限制来源 IP
- `80/tcp`：HTTP
- `443/tcp`：HTTPS

不要向公网开放 `8765`。应用只监听 `127.0.0.1:8765`，由 Nginx 反向代理。

### 4.6 配置 HTTPS

域名解析到 ECS 公网 IP 后，可以使用 Certbot：

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d edu.example.com
sudo certbot renew --dry-run
```

## 5. 更新部署

```bash
cd /opt/open-rosalind
sudo -u rosalind git fetch origin
sudo -u rosalind git checkout edu
sudo -u rosalind git pull --ff-only origin edu
sudo -u rosalind .venv/bin/pip install -r requirements.txt
sudo systemctl restart open-rosalind-edu
```

验证：

```bash
sudo systemctl status open-rosalind-edu
curl -I http://127.0.0.1:8765/
```

## 6. 日志与排障

查看服务日志：

```bash
sudo journalctl -u open-rosalind-edu -f
```

查看 Nginx 日志：

```bash
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

常见问题：

| 现象 | 检查项 |
| --- | --- |
| 页面可访问但不能生成 | 检查 `DASHSCOPE_API_KEY` 和 `/api/config` |
| 返回 502 | 检查 systemd 服务和 `127.0.0.1:8765` |
| PDF 无法提取文本 | 扫描 PDF 需要先做 OCR |
| 上传返回 413 | 检查 Nginx `client_max_body_size` |
| 模型请求超时 | 检查 ECS 外网访问、Base URL 和 `proxy_read_timeout` |

## 7. 安全边界

- Edu 版本不应接收包含可识别患者身份的信息。
- 当前上传内容由 Web 进程解析，正式多用户服务前必须增加用户级文件隔离和生命周期清理。
- 浏览器中临时填写的 API Key 会随请求发送到服务端；公网部署应只使用服务端环境变量，并隐藏或禁用前端 Key 输入。
- 参考文献存在性验证不等于论文支持特定医学论点，关键结论仍需阅读原文。
- 当前 Edu 服务不执行用户提交的 Python、R 或 Shell 代码。代码执行能力应放在 Research Agent 分支的受限 Docker/ECI 沙箱中。

