# P5E-001 只读监控数据源接入预检任务协议

- Capability：`P5E-READONLY-MONITORING-SOURCE-READINESS`
- 授权：项目负责人于 2026-07-28 批准 P5E Mock/Fixture 范围
- 工作分支：`codex/p5e-readonly-monitoring-source-contracts`

## 允许范围

- `connectors/` 下的无 I/O 预检契约、Prometheus mock 预检与单元测试。
- API Capability Registry、管理员安全摘要和相应前端类型/展示适配。
- P5E Brief、完成包、测试报告和运维说明。

## 禁止范围

- 不启动或实现任何真实网络调用、endpoint 探测、凭据读取、秘密挂载或真实数据收集。
- 不保存 PromQL、标签、主机名、item key、指标/事件载荷或原始观察数据。
- 不引入写操作、时序数据库、SSO、HA、Kubernetes、Production 承诺或新的业务健康能力。

## 验收证据

- 无 I/O 单元/契约测试覆盖 Zabbix 与 Prometheus allow-list、阻塞原因、Scope 与 API 脱敏返回。
- P6 Fixture 回归、P5 账号与管理员权限回归、类型/静态检查和实际浏览器后台状态检查。
- 独立 Test Agent 只读复核；真实数据与真实 Connector 明确标为未测且不在范围内。
