# P2 光模块纵向切片阶段报告

- 阶段：P2 光模块纵向切片
- Capability / Task：[CAP-OPTIC-HEALTH #4](https://github.com/G31ght/AskLily/issues/4)
- 报告角色：Project Lead
- 报告日期：2026-07-20
- P1 基线：`9361a5cade8910544dcdfd849d66392e3b0579a5`
- 实现候选：`5afedd63f7aada8645c296625b9b03d9496ff4c5`
- 集成分支：`feature/CAP-OPTIC-HEALTH`
- 验收状态：**绿色 - 自测、实际联调、独立复检和远端 CI 已通过，待项目负责人审核**

## 阶段结论

P2 已形成第一条可运行的受控能力链路：固定光模块 Fixture 经版本化规则生成结构化 HealthAssessment 与去重 Event；受授权的只读 Tool 查询后由 Chat 归纳可追溯结论，再生成合法 `optic_health` ViewContext 并驱动 Workspace。所有结果在服务端 Scope 内过滤。

## 已完成

- CAP-OPTIC-HEALTH Brief、Capability Manifest 和 GitHub 任务协议；规则阈值明确为仅供 Demo Fixture 验收，非生产阈值。
- L0/L1 Fixture：正常、RX 低、TX 低、温度高、恢复、数据缺失和重复告警七类行为。
- `optic_health.query` 只读 Tool、`/v1/optic-health` 查询、受限搜索建议、来源/时间/规则版本披露和基础审计。
- Chat 将受授权 Query 的结构化结果转换为带 Scope、来源、时间与限制说明的答复；不调用模型 Provider。
- Workspace 可展示健康汇总、资源筛选、结果表格和 Scope 校验；界面显式标记 Fixture L0/L1、非生产阈值与严格只读。
- API 端到端回归和实际回环浏览器联调均覆盖 Chat -> ViewContext -> Workspace。

## 测试摘要

| 项目 | 状态 | 证据与结论 |
| --- | --- | --- |
| 领域规则 | 通过 | 7 类规则、事件 fingerprint 去重、资源类型和站点 Scope 过滤。 |
| API / 契约 | 通过 | Scope 扩张、未知 Tool/View、受控 Chat、直接查询与搜索建议不泄露跨站点资源。 |
| API E2E | 通过 | `tests/e2e/test_optic_health_flow.py` 覆盖 Chat -> ViewContext -> Workspace 查询。 |
| Python 静态 | 通过 | `pytest` 12/12、Ruff、MyPy。 |
| Web 静态 | 通过 | TypeScript、Vitest 2/2、生产构建。 |
| 实际联调 | 通过 | 回环 FastAPI/Vite：Chat 展示授权 Tool、Fixture 来源、时间和规则；Workspace 仅显示 `site-a`，并成功验证受限 `optic_health` ViewContext。 |
| 真实数据 / Connector | 未执行（符合范围） | 无 Zabbix、无 Connector、无真实数据或真实阈值。 |
| 写操作 | 未执行（符合范围） | 仅允许 read Tool；不含持久化、自动修复、配置或工单写入。 |
| 独立复检 | 通过 | `tests/reports/p2-optic-health-acceptance.md`；独立 Test Agent 未修改候选。 |
| 远端 CI | 通过 | 草稿 PR #5 的 `L0 governance check`、`P1 Python validation`、`P1 web validation` 均通过。 |

## 风险与限制

- `demo-1.0.0` 阈值只用于固定 Fixture，不能外推为任意光模块或生产环境告警策略。
- L0/L1 合成数据无法验证真实 Zabbix 字段、空值语义、时钟、延迟或告警关联；这些属于 P3 的独立 L4 验收。
- 开发身份与进程内审计沿用 P1 骨架，仅用于 Demo 证据，不能视作生产认证或持久化审计。

## 审核建议

建议项目负责人验收为“Demo 绿色”。P3 仅可按单独授权接入 Zabbix 的真实只读 Connector；不得把 P2 结果表述为真实系统或 Production 已验证。

## 证据

- Brief：`docs/capabilities/CAP-OPTIC-HEALTH-brief.md`
- Manifest：`docs/capabilities/optic-health.yaml`
- 领域规则：`packages/domain/src/asklily_domain/optic_health.py`
- API E2E：`tests/e2e/test_optic_health_flow.py`
- 独立验收：`tests/reports/p2-optic-health-acceptance.md`
- 本地实现候选：`5afedd63f7aada8645c296625b9b03d9496ff4c5`
- 草稿审核 PR：`https://github.com/G31ght/AskLily/pull/5`
- 远端 CI：`https://github.com/G31ght/AskLily/actions/runs/29750695719`
