# P4 Standalone 硬化阶段报告

- 阶段：P4 Standalone 硬化
- GitHub Task：[P4 #10](https://github.com/G31ght/AskLily/issues/10)
- 报告角色：Project Lead
- 报告日期：2026-07-20
- 基线：`2cb9604bfbf2c768c5c2c19b1d6ddd476751e0ac`
- 实现候选：`b14ed75c9c5feb766ee63682fc86a8362a5f87f9`
- 集成分支：`feature/P4-standalone-hardening`
- 验收状态：**绿色 - Standalone Compose 交付、独立复检与远端实际运行验收均已通过，待项目负责人合并授权**

## 阶段结论

P4 已提供单机无状态 Standalone Compose Profile：Web 固定绑定 loopback，API 没有宿主端口且仅位于内部网络；容器具备 health gate、非 root、只读根文件系统、最小 capability、`no-new-privileges` 和本地日志轮转。备份、升级、审计边界、运维与容量限制均已写入可执行资产和文档。

项目负责人此前接受 P3 真实 L4 延期；P4 不改变该决定。当前 Profile 继续只使用 P2 Fixture，不连接真实 Zabbix、不读取真实数据，也不增加业务写操作。

## 已完成

- 两容器 Compose Profile 与 Nginx 内部反向代理，`/health` 返回 `profile=standalone`；Web 仅发布到 `127.0.0.1`。
- 运行时 Profile 由 API 显式披露，Web 同步展示，不改变现有 Scope、Fixture、Tool 或 ViewContext 契约。
- 部署资产离线校验、非秘密无状态部署备份（提交元数据与 SHA-256）和 fail-closed 升级脚本。
- 运维手册披露审计为受限 Demo audit 与 Docker 轮转日志；容量基线明确不是 L6 或 Production 承诺。
- P4 CI 运行 Compose config、build、health-gated startup、经 Web 代理的 API health 与 Web entrypoint smoke。

## 测试摘要

| 项目 | 状态 | 证据与结论 |
| --- | --- | --- |
| Python 回归与静态 | 通过 | 22/22 测试、Ruff、Mypy（15 个源文件）通过。 |
| Web 回归 | 通过 | TypeScript、Vitest 2/2、生产构建通过。 |
| 离线部署 / 备份 | 通过 | P4 asset gate 与非秘密无状态备份测试通过。 |
| 独立复检 | 通过 | `tests/reports/p4-standalone-acceptance.md`；首轮发现的可覆写 host bind 已修复并复检。 |
| Compose 实际运行 | 通过 | PR #11 GitHub Actions：config、镜像构建、API health gate、Web 代理 health 与 entrypoint smoke 均通过。 |
| 真实数据 / L4 | 延期（既有接受） | P4 未接触 Zabbix、Token、真实资源或指标；不将本阶段绿色外推为 L4/Production。 |
| L6 / Production 容量 | 未执行（符合范围） | 仅提交 Standalone 容量基线与未来 L6 输入；未声称性能或并发结论。 |

## 风险与限制

- 部署目标是受控单机本地使用；不适用于远程多用户、公网访问、HA、Kubernetes 或灾备。
- 当前无数据库、卷或持久化审计；备份仅恢复非秘密部署材料。引入保留周期、持久化数据或集中日志前必须先建立 ADR。
- 本机无 Docker CLI；实际启动证据由隔离 GitHub Actions runner 提供。最终私有化安装仍要求部署人员在目标机按运行手册验证 Docker 与 loopback health。

## 建议与证据

建议项目负责人验收 P4 为绿色 Standalone 交付，并在 PR #11 审阅后授权合并；真实 Connector/L4 与 Production/L6 均保持为后续独立里程碑。

- Brief：`docs/capabilities/P4-STANDALONE-brief.md`
- 运维手册：`docs/runbooks/P4-standalone-operations.md`
- 容量基线：`docs/architecture/P4-standalone-capacity-baseline.md`
- 独立验收：`tests/reports/p4-standalone-acceptance.md`
- 远端运行验收：[PR #11 Checks](https://github.com/G31ght/AskLily/pull/11/checks)
