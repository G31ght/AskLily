# P5G 资源检索与详情工作台

- 阶段：Program Phase II / P5G 运维查询能力
- Capability ID：`resource-explorer`
- 状态：2026-07-31 已获负责人实施授权；仅 L0/L1 Fixture / Synthetic Scenario。
- 前置依赖：P5F、P6、ADR-0007、P1 `Resource` 与 `Scope`。

## 目标

用户可通过受控对话、能力中心预置入口或 Workspace 定位 `site`、`device`、`interface`、`optic` 资源，并查看同一会话下的结构化详情。目录及健康结论均为演示数据。

## 已批准范围

1. 服务端 Fixture 目录提供稳定 ID、显示名、站点、最小公开摘要和受控的父级归属；底层既有光模块 `Resource.resource_type` 保持 `optic_module`，前台显示“光模块（optic）”。
2. `resource_explorer.read`、`resource_search@1.0.0` 与 `resource_detail@1.0.0` 必须经 Registry、Scope、P6 数据源状态和 ADR-0007 精确 filter/module allow-list 验证。
3. 仅支持精确 ID、受控名称匹配、站点/类型/已引用健康筛选与服务器分页。客户端不得全量加载、提交 Scope、任意 View、模块或路由。
4. 详情只引用已有 `HealthAssessment` 摘要，不重算规则，也不返回或持久化 Observation/Event 原始事实。P5H/P5I 未注册时仅显示通用安全不可用原因。
5. 能力中心展示 Fixture/L0-L1、来源和限制，并可发起“检索当前可见资源”的预置 Chat 查询。

## 安全语义

- 未知资源与 Scope 外资源详情使用相同安全失败响应；建议在当前 Scope 外不返回名称；非法 Scope 扩张与未登记 View/filter/module 失败关闭。
- 健康筛选仅复用已有光模块能力；其来源不可用时返回明确不可用状态，绝不以未筛选 Fixture 结果回退。
- 不新增外部连接、凭据、CMDB/资产同步、真实主机名、写操作、SQLite 业务数据、历史/收藏/笔记、任意全文/正则/SQL/路径搜索。

## 验收

Python/Web/P0、P6 Compose、真实浏览器与独立 Test Agent 均须通过；浏览器覆盖能力中心、Chat、搜索、详情、空/歧义/拒绝与窄屏。正式报告必须清晰区分独立测试证据和 Project Lead 的 Compose/浏览器证据。
