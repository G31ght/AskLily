# P5B-001 本地账号、会话与按账号对话历史 - 任务协议

## Task identity

- Task or capability ID: P5B-001 / P5B-LOCAL-ACCOUNT-HISTORY
- Title: 本地账号、服务端会话与按账号保存的 Fixture 对话历史
- Responsible role: Delivery Agent under Project Lead integration
- Target branch: `codex/p5b-local-account-history`
- Baseline commit: `19832e8`

## Scope

- Allowed directories/files: `services/api/`、`packages/contracts/`、`apps/web/`、`tests/`、`docs/`、`pyproject.toml`、`requirements-dev.lock`、`.gitignore`；如需要部署文件变更，必须先由 Project Lead 单独确认。
- Dependent contract version and owner: P1 `Scope`、`AuditEvent`、`PlatformResponse`、`ViewContext` 1.0.0（API / Domain / Project Lead）；[ADR-0004](../adr/0004-local-account-and-conversation-history.md)。
- Explicit non-goals: SSO、LDAP/OAuth、外部网络、真实模型/Connector/数据、设备或工单写操作、Production/HA、多实例同步、修改 P4 无状态 Standalone 历史结论。

## Acceptance

- Business acceptance: 本地账号可登录/注销；登录用户只看见和继续自己的 Fixture 对话；刷新后最近对话恢复；用户可删除自己的对话。
- Permission scenarios: 账号间不可枚举/读取/继续/删除；历史重新打开后按当前服务器 Scope 重查；客户端身份、角色、Scope 或历史消息均不可扩大 Scope。
- Exception scenarios: 无效凭据、失效会话、CSRF/跨站状态变更、损坏或不可写数据库、迁移失败、非法会话/对话 ID 均失败关闭且不泄露数据。
- Regression scope: P1/P2 Scope、Tool、ViewContext、Fixture Chat、API E2E、P3 mock 预备、P4 离线部署资产，以及 Web typecheck/test/build。
- Performance or real-data requirement: 不设 L6 性能结论；仅 L0/L1 Fixture，禁止网络和真实数据。

## Constraints

- Files or policies that must not change: 公开仓库敏感信息规则、ADR-0003 的 L4 延期、严格只读边界、P4 Standalone 的 loopback/无状态验收边界。
- Forbidden operations: 不连接外部系统，不创建真实账号/真实运维数据，不提交数据库、密码、Token、Cookie、`.env`、日志或测试中生成的敏感内容。
- Data, secret, network, and external-system limits: 密码只使用不可逆自适应哈希；会话凭据仅服务端安全存储的摘要；持久化消息限 Fixture/L0-L1；无 SSO、外部模型或外网请求。

## Completion handoff

- Self-test evidence: 数据迁移、身份/会话/历史/删除/Scope 单元和 API 测试，Ruff、Mypy、Web typecheck/test/build、实际浏览器路径。
- Required independent-test evidence: 独立 Test Agent 覆盖账号隔离、Scope 收窄、会话失效、删除、迁移失败和敏感信息扫描；默认不修改业务代码。
- Documentation updates: ADR-0004、P5B Brief、功能完成包、运行/备份影响说明与 API 契约说明。
- Defect status: 无未接受 Critical/High 安全、权限、数据删除或迁移缺陷。
- Report location and handoff notes: `docs/reports/P5B-local-account-history-completion-package.md` 与独立测试报告；真实数据/SSO/Production 必须明确为未测且不在范围内。
