# P5E 只读监控数据源接入预检完成包

- Capability：`P5E-READONLY-MONITORING-SOURCE-READINESS`
- 分支：`codex/p5e-readonly-monitoring-source-contracts`
- 范围：Mock/Fixture、零网络、零凭据；不代表真实 Zabbix、Prometheus 或 L4 验证。

## 交付

- 新增统一无 I/O 预检契约，Zabbix 仅允许 `host.get`、`item.get`、`history.get`；Prometheus 仅允许 `query`、`query_range`。
- 未声明来源、未声明配置/Scope、未接受治理或未获单次执行授权均返回确定性阻塞原因。
- 管理员系统状态只返回来源类型、阻塞码与 allow-list；不含 endpoint、凭据、PromQL、标签、主机名或原始指标。
- 默认 Fixture 不伪造真实来源预检结果；P6 的真实来源失败关闭保持不变。

## 验证

- Python 全量：`36 passed`。
- Ruff、mypy、Web TypeScript 通过；Web Vitest：`2 passed`。
- 独立 Test Agent：复核通过。补充临时 Zabbix/Prometheus 注册表的管理员 API 回归后，确认两类来源均 `blocked`、allow-list 正确，且序列化响应不含 endpoint、token、credential、PromQL、label 或原始观察字段。

## 未包含

没有 HTTP 客户端调用、真实环境配置、秘密注入、L4、时序存储、告警规则、写操作或 Production 承诺。任何真实连接仍需单独的负责人授权与适用 ADR。
