# P5E/P6 独立只读验收报告

- 验收范围：P6 统一运行时与数据源架构收敛、P5E 只读监控来源预检，以及其最终集成/CI 合同。
- P6 验收对象：`20cadf6`（P6 实施提交）。
- P5E 验收对象：`7699583`（P5E 实施提交）。
- 最终集成对象：PR #12 合并提交 `f4dae7a2a6d5917fccd9028bfeeafd5a4b67b54a`；交接关闭提交 `e1e9dbb3038a449cc71d21b11fbb675f0beafb0c`。
- 验收方式：独立 Test Agent 只读复核、隔离 Fixture Compose 证据与受保护 PR CI；未连接真实数据源、客户 endpoint 或凭据。
- 结论：**通过。**P6 与 P5E 的已批准范围、失败关闭边界和最终持续集成证据一致。

## 检查与证据

| 范围 | 命令或证据 | 结果 |
| --- | --- | --- |
| P6 Python 回归 | `pytest -q` | 独立复核批次 `33 passed`；边界补测后 P6 最终 `34 passed`。 |
| P5E Python 回归 | `pytest -q` | 最终集成前 `37 passed`；覆盖无 I/O allow-list、阻塞状态与管理员 API 脱敏。 |
| 静态与 Web | `ruff check packages services connectors tests`、`mypy`、`pnpm typecheck`、`pnpm test:web` | 全部通过；Web Vitest `2 passed`。 |
| 治理与差异 | `bash infra/ci/check-p0-governance.sh`、`git diff --check` | 通过。 |
| P6 隔离 Compose | `asklily-p6-verify-728`、`asklily-p6-final-728`、`asklily-p6-acceptance-728` | 使用临时项目名/卷和 L0/L1 Fixture；构建、经 Web 的 health/session、API 重启恢复、Scope 投影均通过，随后清理。 |
| P6 浏览器 | `asklily-p6-browser-728` | 实际检查 Fixture 初始化、登录、Chat/Workspace、后台系统状态和 390px 窄屏；界面显示 `fixture · L0_L1` 与 `fixture-optic-health-l0-l1: ready`，不显示 endpoint、凭据或原始数据。 |
| P5E 预检合同 | 临时 Zabbix/Prometheus 注册表的管理员 API 回归 | 两类来源均确定性 `blocked`；只暴露来源类型、阻塞码和 allow-list，序列化结果不含 endpoint、token、credential、PromQL、label 或原始观察字段。 |
| 最终远端门禁 | PR #12 | L0 governance、P1 Python、P1 Web、P6 unified Compose smoke 全部通过。 |

## 发现与复核

| 发现 | 处置与复核结论 |
| --- | --- |
| P6 初检发现数据源 Scope 未执行、Session 可见站点可能泄露、README 对卷清理表述不准确 | 已修复；复核确认 operator Session 仅投影 `site-a`，越出来源 Scope 的 ViewContext 返回 `403 data_source_scope_not_allowed`。 |
| P5E 初检发现管理员 API 脱敏证据不足 | 已补充临时来源注册表回归；复核确认响应不暴露敏感配置或原始监控字段。 |
| PR #12 初次 CI 保留 P4 Profile 健康断言 | 已由 `76668ba` 对齐为 P6 单一 Compose/Fixture 合同；更新后的 P6 unified Compose smoke 通过。 |

## 明确未验收范围

- 不执行 Zabbix、Prometheus、客户系统或 L4 网络访问；不读取 endpoint、Token 或凭据。
- 不验证 Production、HA、Kubernetes、容量、灾备或 SLA。
- 不验证业务写操作、时序存储、告警规则或真实监控事实持久化。

本报告是 P5E/P6 完成包中“独立 Test Agent 复核通过”的正式 Git 跟踪证据，不把 Fixture、Mock 或 CI 结果表述为真实数据源/L4/Production 验证。
