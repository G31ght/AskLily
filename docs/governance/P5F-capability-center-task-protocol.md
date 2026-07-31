# P5F 能力中心与来源透明页任务协议

- Capability ID：`capability-center`
- 授权日期：2026-07-29
- 施工基线：`main` `058dc12c4cae5f297fd12bf91334cc67845c6c97`
- 适用决定：[ADR-0007](../adr/0007-registered-versioned-view-contracts.md)、ADR-0003 至 ADR-0006

## 已批准范围

1. 以现有 Capability Registry、P6 RuntimeConfig 和能力停用状态生成严格只读的普通用户 Capability Catalog。
2. 将全部 View 收紧为版本化、注册式、filter/module allow-list 的失败关闭契约；保留合法 `optic_health` `1.0.0` 路径。
3. 增加 `capability_catalog` Tool/View/Workspace 与受控 Chat 分流，并在普通产品入口提供能力中心。
4. 在默认 Fixture 环境将 P5E 表示为 `not_configured` 的零网络预检；operator 不列出 Scope 外能力。

## 禁止范围

- 不修改 Compose、数据源注册表、SQLite schema、真实 Connector、endpoint、凭据或任何网络行为。
- 不增加来源切换、管理员配置入口、收藏/统计/布局持久化、模型 Provider 或写操作。
- 不暴露未注册能力、其他账号、Scope 外站点、endpoint、Token、PromQL、标签或原始监控事实。

## 交付与验收

- Python、Web、治理门禁、隔离 P6 Compose smoke、实际浏览器与独立 Test Agent 报告均须通过。
- 浏览器必须验证普通入口、Chat 到 `capability_catalog`、operator/admin Scope、P5E 默认空态、非法导航失败关闭和 390px 窄屏。
- 最终完成包说明 Fixture/L0-L1 或零网络预检边界；不得声称真实来源、L4 或 Production 验证。
