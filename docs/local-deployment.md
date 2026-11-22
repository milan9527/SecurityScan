# 本地部署与运行

本指南使用 Strix CLI 连接自建 GLM-5.3，支持本地源码、GitHub 仓库、Web 和 API 目标。Strix 在控制主机上运行，通过 Docker 沙箱执行工具；SGLang 可以部署在同一台 GPU 主机，也可以通过隧道连接远程 GPU。

## 1. 安装 Strix

控制主机需要 Linux、Git、uv、Python 3.12 或更新版本、Docker 和 curl。当前用户须能运行 `docker info`。首次扫描会自动下载工具沙箱镜像，需要网络和足够的磁盘空间。

```bash
git clone --recurse-submodules https://github.com/milan9527/SecurityScan.git
cd SecurityScan
bash setup-strix.sh
docker info
strix-src/.venv/bin/strix --help
```

安装脚本初始化固定版本的 Strix 子模块、应用仓库内的兼容补丁，并执行 `uv sync`。安装本身不会启动扫描。

## 2. 在 GPU 主机启动 GLM-5.3

已有兼容服务可跳到下一节。本项目验证过的硬件是 **8×NVIDIA B200（EC2 p6-b200.48xlarge）**；以下 TP=8 配置面向该级别硬件，不能直接用于普通笔记本或单张消费级 GPU。

GPU 主机需要 NVIDIA 驱动、Docker 和 NVIDIA Container Toolkit。模型权重约 704 GiB，建议准备至少 1 TiB 可用缓存空间，另留 Docker 镜像空间。首次启动包括下载权重和加载模型；历史一次冷启动约 25 分钟，并非所有环境的固定耗时。

在 GPU 主机运行：

```bash
nvidia-smi
mkdir -p "$HOME/glm53-cache"
export SGLANG_IMAGE='lmsysorg/sglang@sha256:f832b5c39559c9caa900b22ad37c76fcce66470676855c42052102c537812f1f'
docker run -d --name glm53-local --gpus all --ipc=host --network=host \
  --ulimit memlock=-1 --ulimit stack=67108864 \
  -v "$HOME/glm53-cache:/root/.cache/huggingface" \
  "$SGLANG_IMAGE" python3 -m sglang.launch_server \
  --model-path zai-org/GLM-5.3 \
  --revision ba32f8c19c8738e2c57c71798c601d477a7bf844 \
  --served-model-name glm-5.3 --tp-size 8 --trust-remote-code \
  --kv-cache-dtype fp8_e4m3 \
  --tool-call-parser glm47 --reasoning-parser glm45 \
  --context-length 262144 --max-running-requests 2 \
  --mem-fraction-static 0.85 --chunked-prefill-size 32768 \
  --watchdog-timeout 1800 --host 127.0.0.1 --port 8000
docker logs --tail 100 -f glm53-local
```

此命令使用基础推理配置，未开启 MTP；不能直接据此复现报告中的 MTP 性能。日志确认服务就绪后，用另一个终端检查：

```bash
curl --fail http://127.0.0.1:8000/v1/models
```

服务仅监听回环地址。控制主机与 GPU 分开时，在控制主机建立 SSH 隧道，将 `GPU_HOST` 替换成可 SSH 登录的地址：

```bash
ssh -N -L 18000:127.0.0.1:8000 ec2-user@GPU_HOST
```

保持隧道运行。已有 EC2 部署的 SSM、NVMe 缓存及启动故障说明见 [GPU 部署记录](../deploy/glm53-ec2/README.md)。不要把 EC2 的 `user-data.sh` 当成本地安装脚本执行：它包含磁盘初始化和关机逻辑。

## 3. 配置模型连接

回到控制主机的 `SecurityScan` 目录，在运行 Strix 的终端设置：

```bash
export STRIX_LLM=openai/glm-5.3
export STRIX_API_TYPE=chat_completions
export LLM_API_BASE=http://127.0.0.1:18000/v1
export LLM_API_KEY=EMPTY
export LLM_EXTRA_BODY='{"max_tokens":32768,"chat_template_kwargs":{"reasoning_effort":"low"}}'
export STRIX_PROMPT_CACHE=false
export LLM_DISABLE_STREAMING=true
export LLM_PREFLIGHT_TIMEOUT=180
export LLM_TIMEOUT=600
export STRIX_TELEMETRY=false
curl --fail "$LLM_API_BASE/models"
```

Strix 与模型在同一主机时，将端口改为 `8000`。`EMPTY` 仅适用于上文没有 API key 的回环服务；连接启用鉴权的服务应设置真实密钥。输出预算 32768 与上下文 262144 是不同限制，长任务仍可能耗尽上下文或执行轮数。非流式模式无法测量 TTFT。

## 4. 选择目标并扫描

以下命令在 `SecurityScan/strix-src` 目录执行。每次选择一个已获授权的目标；占位路径和域名需要替换成实际目标。

```bash
cd strix-src

# 本地源码：替换为实际绝对路径
.venv/bin/strix -n -t /absolute/path/to/repository \
  --scan-mode deep --scope-mode full --max-turns 150

# GitHub 仓库
.venv/bin/strix -n -t https://github.com/YOUR_ORG/YOUR_REPO \
  --scan-mode deep --scope-mode full --max-turns 150

# Web 或 API
.venv/bin/strix -n -t https://YOUR_AUTHORIZED_HOST \
  --scan-mode deep --max-turns 150
```

首次验证安装时可改为 `--scan-mode quick --max-turns 30`。API 测试可追加 `--instruction-file /absolute/path/to/scope.txt`，说明允许测试的路由、测试账户和业务流程；不要将凭据提交到 Git。容器中的 `localhost` 指向沙箱自身，Web/API 地址必须能从沙箱网络访问。

结果保存在当前目录下的 `strix_runs/<run-name>/`，包含报告和漏洞记录。发现需要复核；退出码 2 可能表示发现达到 fail-on 阈值，应结合日志与产物判断是否完成。终端被关闭可能中断本地扫描，长任务可在 tmux 会话中执行。

## 5. 网页控制台的本地开发范围

前端需要 Node.js 22 和 npm。在新的终端、从仓库根目录运行：

```bash
cd apps/security-console
npm ci
npm run dev
```

访问 Vite 输出的地址（通常为 `http://127.0.0.1:5173`）。这只启动前端开发服务器。完整登录、提交扫描和历史记录依赖 AWS 后端；仓库目前没有全离线的控制台部署方案。

后端 `npm start` 和 Worker `npm run worker` 还需要 AWS 身份、DynamoDB、SQS、S3、GPU 配置，以及同源 API 转发。登录使用 Secure Cookie，写请求校验 `APP_ORIGIN`，完整联调需要 HTTPS 与正确的同源配置，不能只启动 Vite 就完成。完整应用部署参见 [控制台说明](../apps/security-console/README.md)。

## 6. 结束运行与查看性能报告

本地 CLI 不包含演示控制台的“空闲 10 分钟停止 GPU”机制。停止模型容器：

```bash
docker stop glm53-local
```

此命令只停止容器，不停止 EC2；EC2 需单独执行 Stop，保留实例和 EBS。再次启动容器可用 `docker start glm53-local`，缓存目录保留时无需重新下载已有权重。

已有 [性能报告](../reports/glm53-superagent/RESULTS.md) 和 [HTML 报告](../reports/glm53-superagent/index.html) 可直接查看。重新生成 HTML，在仓库根目录执行：

```bash
uv run scripts/render_report.py
```

上述部署步骤依据仓库现有配置整理；本次文档更新未重新启动 GPU 或执行扫描。
