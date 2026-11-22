# Web 应用渗透测试报告

日期：2026-11-20 UTC

目标：https://d2ic29y1hc1eco.cloudfront.net/

关联接口：前端直接引用的 https://qzd3j8cmn2.execute-api.us-west-2.amazonaws.com/prod 。测试采用低频 HTTP 请求、公开前端源码审查、一次公开演示账号登录以及虚构票据的访问控制验证。未修改票据或执行交易。此报告为有限范围测试，不能代表完整安全认证。

## 结果

未确认高危漏洞或身份认证绕过。发现可登录的公开演示账号、公开源码映射、内部错误信息暴露及浏览器安全响应头缺失。业务接口因 AgentCore 运行时错误未能正常完成查询，限制了业务权限验证。

| 项目 | 结果与严重性 | 证据 |
| --- | --- | --- |
| 公开演示账号可登录 | 条件性风险：页面明确展示 Demo Credentials，使用该凭据调用 POST /auth 返回 200、success=true 和访问令牌。若此环境只允许受邀用户，这是访问控制设计缺口；若为公开演示，则需确保账号仅访问隔离测试数据并限制调用费用。当前未证明访问真实用户数据，不判定高危。 | source/components/LoginForm.tsx:68；auth-checks.json 中 public-demo-login |
| 前端源码映射公开 | 低危/信息暴露：GET /static/js/main.320dac4d.js.map 返回 200，可恢复 TypeScript/TSX 业务源码及接口配置。未在已审查的业务源码中发现云访问密钥。 | source-map.json、source-map.body、source/ |
| 内部错误信息暴露 | 低危：持演示账号令牌访问虚构票据 tiers 接口，返回 HTTP 200、success=false，并包含 MCP 错误 -32006、AgentCore MMDSv2 配置和 UpdateAgentRuntime 修复参数。暴露运行时实现和配置细节。 | auth-checks.json 中 authenticated-nonexistent-ticket |
| 安全响应头缺失 | 加固项：首页响应缺少 Content-Security-Policy、X-Frame-Options、Strict-Transport-Security 和 X-Content-Type-Options。未进行浏览器点击劫持或 XSS 利用验证。 | headers.txt |

## 访问控制验证

- 不带令牌访问 tiers、recommendations、pricing、validate、chat 接口，均返回 401。
- tiers 接口拒绝无效 Bearer 令牌和 alg=none 的伪造 JWT，均返回 401。
- /.git/config、/.env 和随机不存在路径均返回 403，未读取到配置文件内容。
- HTTP 首页请求最终跳转至 HTTPS。
- 跨域预检返回 Access-Control-Allow-Origin: *，未返回 Access-Control-Allow-Credentials。应用使用 Bearer 令牌，此配置本身不证明跨域凭据窃取或认证绕过。
- 客户端将访问令牌存储在 localStorage，并检查 JWT 到期时间。客户端未验签不能单独判定漏洞；本次伪造 JWT 已被服务器拒绝。令牌存储方式会增加未来 XSS 的影响，但本次未发现可复现 XSS。

## 修复建议

1. 明确演示环境是否允许公众登录。若不是，禁用公开账号、撤销现有会话并移除页面凭据；若是，隔离测试数据，限制账号权限、请求速率和模型调用费用。
2. 生产构建不要公开上传 .map；将源码映射放在受限的错误监控存储中。移除现有公开对象时一并处理 CloudFront 缓存。
3. 服务端记录完整异常，客户端只返回通用错误及关联 ID，并使用适当错误状态码。修复 AgentCore 运行时配置后重新验证业务功能。
4. 使用 CloudFront Response Headers Policy 配置 HSTS、nosniff 和防嵌入策略；结合实际脚本、样式和 API 域名逐步部署 CSP。
5. 业务恢复后，使用两个隔离测试账号及其测试票据验证对象级授权、票据归属、价格计算与升级流程，并开展 AI 工具权限及提示注入测试。

## 限制及证据处理

本次未测试真实票据、支付、并发竞争、限流阈值、拒绝服务或 AI 提示注入；也未完成双账号越权测试。没有证据支持该站点或 GLM 模型的安全护栏已被绕过。

登录令牌仅用于本次内存中的请求，auth-checks.json 已将 tokens 字段脱敏。原始公开页面及源码文件仍包含网站自行公开的演示凭据，分享证据前应按需要脱敏。
