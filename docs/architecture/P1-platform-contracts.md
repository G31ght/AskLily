# P1 平台契约

P1 冻结最小的跨模块语义；它不定义厂商字段、光模块规则、真实数据源或业务页面。契约版本均为 `1.0.0`，破坏性变更必须建立 ADR 并提升语义主版本。

| 契约 | 所有者 | P1 语义 |
| --- | --- | --- |
| API Contract | API / Domain | `PlatformResponse` 带 `request_id`、可选 `query_id`，且数据与错误互斥。 |
| Scope | Identity / API | 服务端签发的项目、站点、集群、资源类型、动作允许集；调用者只能请求其子集。 |
| Resource / Observation / HealthAssessment | Domain | 资源身份、来源事实和规则结论分离；P1 仅定义模型，不计算健康。 |
| Tool Contract | Agent / Domain | 已注册、只读、声明所需动作和输入/输出版本的调用边界。 |
| View Contract | Web / Domain | 已注册 `view_id`、收窄后的 Scope、公开 filters、可选焦点资源和查询快照。 |
| Capability Manifest | Capability Registry | 能力的版本、所有者、Profile、Tool/View 引用和限制的权威目录项。 |
| AuditEvent | Audit | 请求、Scope、Tool、结果与拒绝原因的可追溯关联。 |

## 拒绝语义

- 项目不匹配、动作扩大或允许集外的站点/集群/资源类型必须拒绝，不能静默回退。
- 未注册 Tool、View，或引用未注册 Tool/View 的 Capability 必须拒绝。
- P1 禁止注册写 Tool；Agent 不能查询 Connector 或自行生成业务事实。
- 允许与拒绝均须携带 `request_id`；查询可额外携带 `query_id`，以便审计和复现。

## P2 接入边界

P2 可在不改变这些语义的前提下增加光模块 Fixture、规则、只读查询 Tool 和 `optic_health` View。任何破坏性 Resource、Event、ViewContext 或 Tool 改动都需要 ADR 与契约版本升级。
