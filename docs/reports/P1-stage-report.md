# P1 平台骨架阶段报告

- 阶段：P1 平台骨架
- 报告角色：Project Lead
- 报告日期：2026-07-20
- P0 基线：`74e42df53dbe9d64d3db91115ac384f454fa1a53`
- 实现候选：`a77a8180353d7b697283e7d393734b54840d7c3d`
- 集成分支：`chore/P1-platform-skeleton`
- 验收状态：**黄色 - 实现与本地验证完成，待远端 CI 和项目负责人审核**

## 阶段结论

P1 已实现工程开工文档规定的“平台骨架”，而非业务能力：版本化契约、服务端签发并只可收窄的 Scope、受注册表约束的 Tool/View/Capability、基础审计，以及开发 Profile 的 Chat/Workspace/Capability Center 壳层均可运行。系统没有 Connector、真实数据、真实模型 Provider 或写操作。

## 已完成

- 固化 API、Scope、Resource、Observation、HealthAssessment、Tool、ViewContext、Capability 和 AuditEvent 的 `1.0.0` 契约；事实与规则结论保持分离。
- 建立注册表守卫：未知 Tool/View、未注册 Capability 引用、P1 写 Tool 和 Scope 扩张一律拒绝，不静默回退。
- 建立 FastAPI 只读开发 Profile：身份、能力目录、Tool 授权、ViewContext 校验、受限 Chat 和审计读取均带 `request_id`。
- 建立 React/Vite 的 Chat、Workspace、Capability Center；页面明确显示“无业务能力、无真实数据、严格只读”。
- 为本地联调配置仅回环的开发代理；生产 API 地址仍须以 `VITE_API_BASE_URL` 显式配置。
- 加入 Python 与 pnpm 锁定依赖、P1 GitHub Actions 静态验证和 Capability Manifest。

## 测试摘要

| 项目 | 状态 | 证据与结论 |
| --- | --- | --- |
| Python 契约/API | 通过 | `pytest`：6/6；覆盖 Scope 扩张、未知 Tool/View、无业务事实的 Chat 和审计拒绝记录。 |
| Python 静态 | 通过 | `ruff check packages services tests`、`mypy` 均通过。 |
| Web 静态 | 通过 | `pnpm typecheck`、`pnpm test:web`（1/1）、生产构建均通过。 |
| 实际联调 | 通过 | 回环 FastAPI 与 Vite 页面启动；Chat 返回无业务/真实数据/模型限制，Workspace 成功验证受限的 `platform_status` 与 `read` Scope。 |
| 真实数据/Connector | 未执行（符合范围） | P1 未实现且未调用任何真实数据源或 Connector。 |
| 写操作 | 未执行（符合范围） | 注册表和 API 均无写 Tool；仅使用进程内审计作为测试可追溯证据。 |
| 远端 CI | 待运行 | 将在候选分支推送并创建 PR 后以 GitHub Actions 复验。 |

## 风险与限制

- 开发 Profile 的身份与 Scope 是显式的演示常量，只用于验证服务端 Scope 语义；不能作为生产认证实现。
- 审计为进程内只读展示，不是持久化审计服务；后续持久化设计需单独 ADR 与权限审查。
- 前端仅提供 P1 元数据壳层，不能导出、查询或生成业务结论；不能据此声明任何业务功能已就绪。
- 公开仓库仍受 ADR-0001 的敏感信息限制；Python/Node 锁定依赖仅来自批准的公开包注册表。

## 审核建议

建议在远端 P1 CI 通过且独立复检完成后，由项目负责人审核该 PR。接受后才可进入 P2 的静态 Fixture、只读查询 Tool 和光模块规则工作；不得直接接入真实系统。

## 证据

- 契约说明：`docs/architecture/P1-platform-contracts.md`
- Capability Manifest：`docs/capabilities/platform-foundation.yaml`
- Python 锁：`requirements-dev.lock`
- Web 锁：`pnpm-lock.yaml`
- P1 CI：`.github/workflows/p1-static.yml`
- 本地实现候选：`a77a8180353d7b697283e7d393734b54840d7c3d`
