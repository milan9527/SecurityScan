# 部署与验证记录

验证日期：2026-11-21 UTC。区域：孟买 `ap-south-1`。

应用地址：**https://dddps7roghlvq.cloudfront.net/**

## 已部署资源

| 组件 | 资源 |
| --- | --- |
| 应用 CloudFormation | `strix-console`，`UPDATE_COMPLETE` |
| 构建 CloudFormation | `strix-console-build` |
| CloudFront | `ESZSZQZ3PKY9V` |
| 前端 S3 | `strix-console-frontend-izov8xvfn8xm` |
| CloudFront OAC | `E29F77H8XV4LI9` |
| 内部 ALB | `internal-strix-co-Alb-VnCpkKR4XTjm-1235807284.ap-south-1.elb.amazonaws.com` |
| ECS 集群 | `strix-console-Cluster-NAkrGqOpjr3O` |
| API 服务 | `strix-console-ApiService-JTgZzK7HWEjK`，Fargate |
| Strix Worker 服务 | `strix-console-WorkerService-bNMBwwu1DnhQ`，ECS EC2 |
| Worker EC2 | `i-0cd10816621667306`，`m7i.xlarge`，按需 |
| 模型 EC2 | `i-0b33a1d2ee1a2065f`，Spot `p6-b200.48xlarge`，8 × B200 |
| GPU 控制器 | `strix-console-Reaper-wtdAYT7wE9UA` |
| 用户认证 | 自建用户名密码，DynamoDB 保存 scrypt 密码哈希及服务端会话 |
| 报告 S3 | `strix-console-reports-bnnkwornrczw` |

API 和 Worker 镜像分别为 `632930644527.dkr.ecr.ap-south-1.amazonaws.com/strix-console-api:password-login` 和 `632930644527.dkr.ecr.ap-south-1.amazonaws.com/strix-console-worker:demo`。CodeBuild 构建成功。Worker 已预拉取 Strix 沙箱 `ghcr.io/usestrix/strix-sandbox:1.4.1`。

## 已验证

- 扫描工作台已移除部署架构入口，改为 GitHub、Web、API 分类与手动地址输入；已配置目标仅作为输入建议。线上 Chromium 验证三类地址输入、切换类型清空目标、登录门禁及 390px 手机布局通过，无脚本异常；此次界面验证未提交扫描或操作 GPU。
- 登录入口已部署到 CloudFront：验证会话时只显示加载状态，未登录时只显示独立登录页；退出或会话失效后隐藏工作台并返回登录页。Chromium 已验证登录前无工作台、未认证功能 GET/POST 返回 401、登录成功及清除 Cookie 后自动返回登录页。
- 本地 6 项测试通过，覆盖用户名密码认证、退出撤销、登录限流、会话租约、延迟停止、任务保护与目标校验；前端构建和 Lambda 打包成功。
- API 和 Worker 服务均为期望 1、运行 1，部署完成；ALB API 目标健康。
- CloudFront 首页和运行时配置返回 HTTP 200；未登录访问 `/api/config` 返回 HTTP 401。
- Chromium 打开页面无脚本异常；390px 手机视口无水平溢出；用户名密码登录、退出后旧会话失效及跨站登录请求拒绝均通过。会话 Cookie 设置 Secure、HttpOnly、SameSite=Strict。
- 登录后的扫描列表、配置和 GPU 状态接口均返回 HTTP 200；已修复扫描列表查询中 DynamoDB 保留字段 `owner` 的表达式别名。
- 从 Worker 可访问 GPU 私有地址的模型端点，返回 `glm-5.3`；Strix CLI 可以启动。
- Worker 主机已设置 EC2/ECS 元数据地址阻断规则。
- GPU 上 Docker 开机启动和模型容器 `unless-stopped` 重启策略已配置。
- 部署后读取控制器记录为 `unmanaged`，无会话、无任务、无停止时间；GPU 为 `running`、`spot`。本次部署没有停止或重启 GPU。

## 尚待验证与配置

2026-11-21 已部署闲置自动停止与历史扫描记录更新：API ECS 任务修订版 2 部署完成，GPU 控制器 Lambda 更新成功，CloudFront 缓存失效完成。8 项本地测试通过；线上 Chromium 验证历史接口返回 200、当前账号显示 1 条历史记录、目标搜索生效，停止操作并等待事件防抖结束后观察 35 秒，没有发送续期心跳，页面无错误提示。真实 GPU 十分钟闲置停止仍待观察验证。

已创建管理员 `admin`。随机密码保存在部署主机 `/home/ec2-user/.codex/credentials/strix-console-admin.txt`（权限 0600），未写入仓库。Cognito 资源已移除。

尚未完成登录后的真实扫描、报告下载及真实 GPU 停止/重启全流程验证。基础设施健康、模型可达和单元测试通过，不代表这些端到端流程已验证。

默认代码目标为 `milan9527/AgentcoreShell` 和 `milan9527/agentcore-superagent-update`。前端允许手动输入目标，服务端仍校验授权范围。Web/API 测试界面与任务执行路径已实现，但 `AllowedHosts` 初始为空，需要配置授权 HTTPS 主机后使用。

## 在前端管理授权目标

管理员登录后进入侧栏 **授权目标**，分别填写 GitHub 仓库和 Web/API 主机，每行一个，也支持逗号分隔：

- GitHub：`milan9527/AgentcoreShell`，使用 `owner/repository` 格式。
- Web/API：`test.example.com` 或 `api.example.com:8443`，不带协议、路径或通配符；扫描时输入完整 HTTPS URL。

点击 **保存授权目标** 后，新扫描立即使用保存的配置，不需要重新部署。主机按完整名称和端口匹配，子域名需要单独添加。每类最多 100 项；清空某类列表将禁止该类新扫描，不会取消已经提交的任务。

配置保存在 DynamoDB 的 `CONFIG#TARGETS` 中，首次保存前回退到部署环境变量；首次保存后以数据库配置为准。页面显示最后修改人及时间，多人同时编辑时拒绝覆盖过期版本，需重新加载。

仅用户记录具有 `role: admin` 的账号能够修改配置；界面隐藏和后端权限校验同时生效。现有 `admin` 账号已设置此角色，普通账号只能使用已授权目标。

2026-11-21 已部署授权目标管理：API 镜像 `strix-console-api:targets-admin`，ECS 任务修订版 3，前端 CloudFront 缓存失效完成。11 项本地测试及前端构建通过；线上 Chromium 验证管理员登录、保存现有授权列表、刷新后持久化、过期版本保存返回 409、未登录配置请求返回 401，页面无脚本错误。验证未提交扫描或操作 GPU。

首次点击“启动演示”才接管 GPU。所有会话和扫描结束后等待 600 秒，由每分钟运行的控制器执行 **StopInstances**，不执行 TerminateInstances。用户点击、键盘输入或滚动才续期 600 秒；后台轮询不会续期。关闭页面或无操作满 10 分钟后，由每分钟运行的控制器触发停止（通常约 10–11 分钟，另加 EC2 状态转换时间）；有活动扫描时继续保留 GPU。此逻辑已通过单元测试，尚未用真实 GPU 停机验证。

GPU 冷启动包含模型加载，不能保证即时就绪；Spot 再次启动取决于容量。ECS Worker、API、ALB 等资源持续运行，十分钟自动停止只针对 GPU。外部脚本任务不在应用的租约记录内，接管前需确认此前的测试已结束。

历史扫描入口支持按目标搜索、状态筛选及每页 40 条加载更多，记录按用户隔离并持久保存在 DynamoDB。页面提供扫描总耗时和待核验发现，报告保存 Strix 原始输出；尚未实现页面级 TTFT/E2E 汇总、私有仓库凭证输入或 API 专用认证配置。
