# ADR-0007：注册式版本化 View 契约

- 状态：Accepted
- 日期：2026-07-29
- 决定者与批准者：Project Lead 提案；项目负责人于 2026-07-29 批准 P5F 全局收紧
- 生效日期：P5F 实施开始时

## 问题

现有 `PlatformRegistry` 只登记 `view_id`，因此 `ViewContext` 虽携带版本与 filters，服务端却未验证其版本或该 View 允许的筛选字段。该实现只适合作为早期测试骨架，不能满足 P5F 对注册式 `capability_catalog` Workspace 的失败关闭要求，也允许旧 View 使用未登记版本或任意 filters。

## 候选方案

1. 仅为 `capability_catalog` 在 API 中增加特例校验：改动最小，但保留其他 View 的不一致安全语义。
2. 继续只校验 `view_id`：兼容最强，但不符合 P5F 的版本化、注册式导航边界。
3. 将 Registry 的 View 登记升级为 `ViewContract`，对所有 View 校验精确版本、允许的 filter 键和可选模块：统一失败关闭，需同步现有测试与已登记 View。

## 决定

采纳方案 3。每个 View 必须在服务端注册唯一的 `view_id`、版本、允许 filters 及允许的 Workspace module。`ViewContext` 必须精确匹配已注册版本；未登记版本、filter 或 module 一律以稳定原因码拒绝。前端和 Chat 只能消费服务端验证后返回的 ViewContext 与 module，不得生成任意页面、链接、能力 ID 或导航地址。

该决定不开放写操作、真实 Connector、数据源切换或新的数据持久化类别。`optic_health` 作为既有测试能力迁移到同一版本化契约；`capability_catalog` 从其首版即遵守该标准。

## 影响

- 代码：公共 `ViewContract`、Registry、API 验证、Chat 编排与 Web module 分发均需使用登记项。
- 数据与部署：无 SQLite 迁移、无 Compose 修改、无真实来源连接；P6 脱敏数据源状态仍是唯一来源状态输入。
- 兼容性：过去未验证版本或任意 filters 的测试调用将失败关闭，属于负责人已批准的全局收紧；合法既有 `optic_health` `1.0.0` 调用保持可用。
- 测试：覆盖未知 View、版本不匹配、未允许 filter、未允许 module、Scope 扩张及既有 Chat-to-Workspace 回归。
- 回滚：仅可回退 P5F 任务分支；不得以放宽未登记 View 的方式规避失败关闭。

## 验证与复审

Project Lead 在集成阶段运行 Python、Web、P6 Compose 与浏览器回归；独立 Test Agent 只读验证所有注册式拒绝路径、Scope 投影和现有光模块路径。若未来需要一个 View 支持新的版本、filter 或 module，必须先登记契约；破坏性语义变更须建立新的 ADR。
