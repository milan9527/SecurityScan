# SecurityScan

Strix + Amazon Bedrock GLM-5.3 Flex 的本地渗透测试与复现项目。

测试对象是仓库内的 SQLite 登录靶场。已完成的扫描发现一个 SQL 注入问题：5 组输入均绕过有漏洞的登录函数，参数化查询对全部 5 组输入阻止绕过。

## 复现验证（不调用模型）

```bash
PYTHONPATH="$PWD/strix-fixture" python3 strix_sqli_poc.py
```

## 重新扫描

需要 Git、uv、Docker、GNU timeout，以及拥有 Bedrock 模型调用权限的 AWS 身份。Strix 源码固定为上游提交 `a1ccf777d80e812edf23fc8b82bdc17def6143ac`，由 submodule 管理。

```bash
bash setup-strix.sh
bash run-strix-glm.sh
```

启动脚本使用 `us-east-1`、`bedrock/converse/us.zai.glm-5.3` 和 Flex tier；会产生 AWS 调用费用。Bedrock 参数适配保存在 `strix_bedrock_params.patch`，安装脚本会应用它。

## 测试记录

- [中文实测说明](strix_glm_report.md)
- [扫描报告](reports/strix-fixture_8f1e/penetration_test_report.md)
- [漏洞详情](reports/strix-fixture_8f1e/vulnerabilities/vuln-0001.md)
- [工具执行证据](strix_sqli_evidence.txt)
- [PoC 重放输出](strix_sqli_replay.txt)

未配置 Bedrock Guardrails；这不代表模型内置安全限制已关闭。本次结果只适用于该本地靶场。4096 token 输出上限曾造成子代理异常，根代理接手后完成测试，详见实测说明。

本地虚拟环境、原始会话数据库及运行日志不提交。上游 Strix 的源码及许可证见 `strix-src` 子模块。
