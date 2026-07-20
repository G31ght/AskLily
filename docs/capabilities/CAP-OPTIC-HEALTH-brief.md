# CAP-OPTIC-HEALTH 光模块健康纵向切片

- GitHub Task: [#4](https://github.com/G31ght/AskLily/issues/4)
- 阶段：P2 光模块纵向切片
- 基线：`9361a5cade8910544dcdfd849d66392e3b0579a5`
- 验证 Profile：Demo / Developer
- 数据等级：L0 Fixture 与 L1 Synthetic Scenario

## 用户价值

授权范围内的运维人员可用中文询问光模块健康状态，并获得可追溯的 Fixture 来源、观测时间、规则版本与范围说明；复杂问题可进入已带入站点、健康状态、时间和焦点资源的工作台。

## 范围

- 固定、可审计的光模块 Fixture，以及覆盖故障和权限边界的 L1 Scenario。
- 纯领域健康规则与结构化 Resource、Observation、Event、HealthAssessment 结果。
- 一个只读光模块查询 Tool、受限 Chat 归纳、`optic_health` ViewContext 和 Workspace 呈现。
- 规则、权限、API、前端和 E2E 的可重复验证。

## 非目标

- Zabbix 或任何真实 Connector、真实数据、真实阈值承诺、自动修复、设备配置、工单或任意写操作。
- 数据持久化、生产认证、性能承诺、Docker Compose/Standalone 硬化。

## 依赖

- P1 契约 `1.0.0`：Scope、Resource、Observation、HealthAssessment、Tool、ViewContext、AuditEvent。
- 服务端 Scope 过滤和已注册 Tool/View 守卫。
- Fixture 仅以 `fixture://optic-health/...` 作为来源标识；不得替换为真实系统 URL。

## Demo 规则基线

这些数值只用于固定 Fixture 的确定性验收，**不是**生产告警阈值或设备厂商建议：

| 规则 | Demo 判断 | 结构化结果 |
| --- | --- | --- |
| 正常 | RX >= -18 dBm、TX >= -9 dBm、温度 <= 75 C，且观测质量完整 | `healthy` |
| RX 低 | RX < -18 dBm | `critical` + `rx_power_low` |
| TX 低 | TX < -9 dBm | `critical` + `tx_power_low` |
| 温度高 | 温度 > 75 C | `warning` + `temperature_high` |
| 恢复 | 前一状态异常、当前观测恢复正常 | `recovered` + `recovered` |
| 数据缺失 | 当前 Fixture 无可用观测或质量为 `missing` | `unknown` + `data_missing` |
| 重复告警 | 同一资源、规则和状态的重复异常 | 一个稳定 fingerprint 的 Event，不重复计数 |

## 验收

- Chat 必须经授权的光模块 Tool 返回结论，并披露 Scope、观测时间、Fixture 来源和规则版本。
- `optic_health` ViewContext 必须包含站点、健康筛选、时间范围与可选焦点资源；服务端拒绝 Scope 扩张或未知 View。
- Workspace 仅展示授权 Scope 内的资源、汇总和搜索建议；越权资源不得出现在结果、计数或建议中。
- 七类规则行为均由单元/契约测试覆盖；至少一条 API-to-Web E2E 覆盖 Chat 到 Workspace。
- 所有 Demo 输出显式标注 Fixture/L0-L1 限制；无真实数据、Connector 或写操作。

## 风险

- Fixture 阈值不可外推到生产；真实字段、阈值、时区和空值语义必须在 P3 的 L4 Connector 验收中独立校准。
- 健康结论和原始观测必须保持分离；Chat 不得补充没有证据的故障原因。
- P2 仅验证纵向效果，不能据此宣称真实 Zabbix 或 Production 已验证。
