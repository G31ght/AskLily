# P3-001 Zabbix 只读 Connector 预备与 L4 验收门禁

- GitHub Task: [#6](https://github.com/G31ght/AskLily/issues/6)
- 阶段：P3 Zabbix 只读接入
- 基线：`8de6a1c0ae1ad5584af5535909bcb6a70bd3eb3f`
- 当前状态：Connector 预备实现；L4 Live Read-only 验收阻塞

## 用户价值

后续获得专用只读 Zabbix 环境后，运维人员可在既有光模块健康链路中获得来源明确、质量可报告的真实观测；在此之前系统不会伪造任何真实系统结论。

## 本轮范围

- Zabbix JSON-RPC 的最小只读客户端，固定允许 `host.get`、`item.get`、`history.get`。
- 本地环境变量读取、HTTPS JSON-RPC endpoint 校验、缺失配置失败关闭。
- 显式光模块 item key 映射、主机级缺失/重复/不可用项质量报告，以及纯 mock transport 测试。
- L4 环境准备清单和数据处理 ADR 提案。

## 非目标

- 本轮不连接、扫描、探测或验证真实 Zabbix；不提交真实 URL、Token、主机名、item key、指标或质量明细。
- 不执行任何写方法、自动修复、配置下发、工单、持久化或生产部署。
- 不将 P2 Fixture 或 mock 验证称为 L4 或 Production 验证。

## 依赖

- P2 的 `optic_health` Resource/Observation/HealthAssessment 语义和 Scope 守卫。
- 本地忽略的 `connectors/zabbix/.env`，由项目负责人后续配置；仓库仅跟踪安全形状示例。
- ADR-0003 获批准，以及专用、可审计的 Zabbix 只读身份。

## L4 验收门禁

- 负责人提供 HTTPS endpoint、Zabbix 版本/认证方式、最小 Host Group、只读 API Token 和一组允许采集的样本资源；Token 不进入聊天、Git、日志或测试报告。
- 仅对明确范围调用 allow-list 方法，记录方法、范围、时间、质量摘要和错误类别，不记录原始指标或敏感资源名称。
- 输出字段映射与质量报告：映射覆盖、缺失/重复项、空值、时间滞后、权限错误和不可用资源。
- 复核真实结果仍受服务端 Scope 过滤；未经验证的数据不得回写或改变设备状态。

## 风险

- 当前没有真实环境，因此不能确认 Zabbix 版本、认证头、item key、字段类型、空值语义和延迟；P3 只能是黄色预备状态。
- 当前仓库为公开仓库，任何 live 配置或原始观测泄露均为不可接受风险，必须在 L4 前完成 ADR 审批和本地秘密配置复核。
