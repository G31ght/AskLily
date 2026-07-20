# P3 Zabbix 只读预备阶段报告

- 阶段：P3 Zabbix 只读接入（P3-001 至 P3-003）
- GitHub Tasks：[\#6](https://github.com/G31ght/AskLily/issues/6)、[\#7](https://github.com/G31ght/AskLily/issues/7)、[\#8](https://github.com/G31ght/AskLily/issues/8)
- 报告角色：Project Lead
- 报告日期：2026-07-20
- P2 基线：`8de6a1c0ae1ad5584af5535909bcb6a70bd3eb3f`
- 实现候选：`f0f1782a64bd03a8bf688f58bd7bbb2d105c71df`
- 集成分支：`feature/P3-zabbix-readonly`
- 验收状态：**黄色 - P3-001 至 P3-003 mock 预备与独立复检通过；真实 L4 只读验收因未提供环境而阻塞**

## 阶段结论

本阶段已将未来 Zabbix 只读接入的安全边界、mock 数据规范化、L4 预检与脱敏证据形状固化。P2 的 Fixture 默认数据源没有改变，未建立真实连接、未读取真实数据、未执行写方法，也没有把 mock 结果表述为真实系统结论。

## 已完成

- P3-001：固定 `host.get`、`item.get`、`history.get` 的 JSON-RPC allow-list；HTTPS endpoint 与本地配置失败关闭；ADR-0003 已获批准但只授权 mock 预备。
- P3-002：以显式 Scope 绑定把 mock Host/Item/History 规范化为 P2 既有 Resource/Observation 输入，保留来源、观测时间、质量和缺失/无效值，不补造观测。
- P3-003：无 I/O 的 L4 预检要求 ADR、本地只读配置、获批 Scope 和单次执行授权全部具备；将局部映射诊断转换为不含资源标识、item key 或原始指标的聚合质量摘要。
- 运行手册明确后续获授权的 L4 只读操作、停止条件、无写操作和仅脱敏留证要求。

## 测试摘要

| 项目 | 状态 | 证据与结论 |
| --- | --- | --- |
| Python 回归 | 通过 | 19/19，覆盖 Connector 白名单、配置失败关闭、规范化、缺失/无效值、L4 预检与摘要脱敏。 |
| Python 静态 | 通过 | Ruff 与 Mypy（14 个源文件）均通过。 |
| 独立复检 | 通过 | `tests/reports/p3-zabbix-readonly-preparation-acceptance.md`；未修改业务实现。 |
| P2 默认链路 | 未变更 | P3 未改动 Fixture 默认数据源或 Web/API 用户界面。 |
| 真实 Zabbix / L4 | 未执行（阻塞） | 当前未提供 endpoint、专用只读 Token、最小获批 Scope 与单次执行授权；按 ADR-0003 不得连接。 |
| 写操作 | 未执行（符合范围） | allow-list 不包含写方法；`host.create` 被测试验证为失败关闭。 |

## 风险与下一门禁

- 目前不能确认真实 Zabbix 的版本、认证兼容性、item key、空值/时间语义、权限边界与数据延迟，因此不能将本阶段称为 L4 或生产绿色。
- 公开仓库不得接收 endpoint、Token、真实资源名、item key 或原始指标；L4 只可使用本地忽略配置，并只输出脱敏质量摘要。
- 取得环境后，先按 [P3 L4 运行手册](../runbooks/P3-zabbix-l4-readonly-runbook.md) 完成门禁；再由 Project Lead 与独立 Test Agent 进行一次最小范围、只读、无写入的真实验收。

## 证据

- ADR：[ADR-0003](../adr/0003-zabbix-live-readonly-data-handling.md)
- 能力说明：[P3 Zabbix 只读 Brief](../capabilities/P3-ZABBIX-READONLY-brief.md)
- 运行手册：[P3 Zabbix L4 只读验收](../runbooks/P3-zabbix-l4-readonly-runbook.md)
- 独立验收：`tests/reports/p3-zabbix-readonly-preparation-acceptance.md`
- 实现提交：`9ce154e`、`4318b82`、`f0f1782`
