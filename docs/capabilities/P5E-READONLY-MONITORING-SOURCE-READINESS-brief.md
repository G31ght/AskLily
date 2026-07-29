# P5E 只读监控数据源接入预检（Zabbix / Prometheus）

- 阶段：Program Phase II / P5E 平台共性能力
- 状态：项目负责人于 2026-07-28 批准 Mock/Fixture 实现；真实连接仍须单次授权
- 前置：P6 统一运行时与数据源状态已关闭并获接受；ADR-0003 继续适用于真实 Zabbix

## 用户价值

项目管理员能够区分“来源未配置”“来源配置形状不安全”“等待负责人授权的真实只读验证”三种状态，而不是把预检误认为已连接、已验证或已获得真实监控数据。Zabbix 与 Prometheus 采用同一安全的预检语义，为后续获批准的真实 Connector 提供可追溯入口。

## 范围

- 建立统一、无 I/O 的只读监控来源预检契约：来源类型、允许只读操作、配置形状、已声明 Scope、单次真实执行授权和阻塞原因。
- 复用既有 Zabbix L4 预检，不改变其 JSON-RPC allow-list；新增 Prometheus HTTP API 的最小只读 allow-list（`query`、`query_range`）及同等失败关闭预检。
- 向管理员控制面/API 暴露不含 endpoint、凭据、主机名、item key、PromQL、标签或原始指标的安全就绪摘要。
- 使用本地 mock/fixture 与契约测试验证；数据源注册表仍不存放真实连接信息。

## 非目标

- 不创建 Zabbix/Prometheus 网络连接、HTTP 请求、环境凭据读取或秘密注入实现。
- 不实现 L4、Production、时间序列存储、告警规则、写操作、设备配置、模型 Provider 或自动修复。
- 不将 P3 Zabbix mock 或 P5E Prometheus mock 表述为真实 Connector 验证。

## 依赖与边界

- P6 的 `fixture` / `test` / `production` 数据源声明、Scope 投影与禁止 Fixture 回退。
- Zabbix 真实运行仍需要 ADR-0003、专用 HTTPS 只读身份、最小 Scope 和单次执行授权。
- Prometheus 真实运行需另行确认认证方式、HTTPS endpoint、最小查询范围、保留策略和外发数据边界；本 Brief 不授予它们。

## 验收

1. 对 Zabbix、Prometheus 都能在零网络、零凭据条件下返回确定性预检摘要和阻塞原因。
2. allow-list 只含声明的只读操作；任一写/管理操作被拒绝。
3. API/后台只显示来源类型、环境、状态、计数和安全原因码；不泄露敏感配置或监控事实。
4. Fixture、未配置真实源、已声明但未授权真实源互相可区分，且没有 Fixture 回退。
5. Scope、P5 本地管理员限制、P6 SQLite 不保存原始数据及所有既有回归继续通过。

## 风险与负责人决定

P5E 只降低将来真实接入的工程不确定性，不能证明任一实际 Zabbix/Prometheus 兼容性。若要进入真实验证，负责人必须分别确认目标来源、最小 Scope、凭据保管、允许的只读调用、数据保留与单次网络授权。
