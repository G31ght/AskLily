# P5F 能力中心与来源透明页完成包

- Capability ID：`capability-center`
- 完成日期：2026-07-29
- 施工基线：`main` `058dc12c4cae5f297fd12bf91334cc67845c6c97`
- 适用决定：[ADR-0007](../adr/0007-registered-versioned-view-contracts.md)、ADR-0003 至 ADR-0006
- 独立验收：[P5F 独立验收报告](../../tests/reports/p5f-capability-center-independent-acceptance.md)

## 交付内容

1. 全局引入注册式 `ViewContract`：所有 View 必须精确匹配版本、allow-listed filters 和 Workspace modules；非法项失败关闭。
2. 新增 `capability-center`、`capability_catalog.read` 与 `capability_catalog@1.0.0`，从既有 Registry、P6 RuntimeConfig 和能力开关生成只读目录。
3. 普通用户入口、受控目录 Chat、来源透明卡片、服务端预置问句与 390px 移动入口已交付；浏览器只渲染服务端授权模块。
4. 默认 Fixture 环境中，光模块显示 `fixture/L0_L1/ready`；P5E 显示零网络 `not_configured`，不宣称真实 Connector、L4 或 Production。

## 安全与数据边界

- operator 目录省略 Scope 外能力；project-admin 仅看到本项目的完整脱敏状态。
- 未新增 SQLite schema、Compose 配置、数据源注册、凭据、endpoint、真实 Connector、来源切换或写操作。
- Catalog 和 Chat 不暴露 endpoint、Token、credential、PromQL、label、原始 Observation/Event 或其他账号资料。

## Project Lead 集成证据

| 项目 | 结果 |
| --- | --- |
| Python / 静态 / Web / 治理 | `pytest -q` 44 passed；Ruff、Mypy、`pnpm typecheck`、`pnpm test:web`（3 passed）、治理门禁和 `git diff --check` 全部通过。 |
| 隔离 Compose | `asklily-p5f-729`、临时端口 `18086`、临时卷；`storage-init` 正常结束，API healthy，Web 回环监听。 |
| 实际浏览器 | 本机初始化隔离管理员后，普通入口打开能力中心；显示 Registry 卡片、Fixture/L0_L1/ready、P5E `not_configured` 与零网络限制；预置 Zabbix 问句进入合法目录 Workspace；光模块问句进入服务端授权的 optic Workspace。 |
| 390px | 首检发现侧栏隐藏导致入口消失；已补会话头部普通入口，重建镜像后在 390px 实测打开能力中心且无 console error。 |
| 独立验收 | 条件通过；独立 Test Agent 覆盖代码、契约、API、Scope、泄露与回归，未将 Lead 的 Compose/浏览器结果冒充为独立复现。 |

## 已知限制

- 所有可用业务数据仍是显式 Fixture L0/L1；P5E 仅是无网络预检。
- 未来若允许客户端提交 Workspace module，必须先扩展 View 契约与 HTTP 级拒绝测试；当前 module 仅可由服务端注册并生成。
