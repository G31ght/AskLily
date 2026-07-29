# P5F 能力中心与来源透明页

- 阶段：Program Phase II / P5F 平台共性能力
- Capability ID：`capability-center`
- 状态：项目负责人已批准**只读接手核验与实施计划**；尚未授权产品实现、真实数据源连接、推送或合并。
- 施工基线：`main` `058dc12c4cae5f297fd12bf91334cc67845c6c97`
- 数据等级：仅使用已注册 Capability 元数据、P6 脱敏数据源状态与现有 L0/L1 Fixture。
- 权限与数据边界：严格只读；不新增外部连接、凭据、真实监控事实持久化、业务写操作或前端数据源切换。

## 用户价值

管理人员无需依赖 Wiki 或源码，即可在 AskLily 中确认：平台当前具备哪些能力、能力是否可用、数据来自何处、处于何种客户声明环境、数据等级和限制是什么。

运维人员可从能力中心进入其授权范围内的 Chat/Workspace 查询场景，不必记忆页面地址、Tool 名称或能力状态约定。

## 范围

1. 在普通用户可访问的产品入口提供“能力中心”；它不能只存在于管理员后台。
2. 每张能力卡至少展示：
   - 名称、用途和能力类别（平台基础、运维查询、来源预检）；
   - 当前状态：可用、未配置、停用、未验证或受 Scope 限制；
   - 数据源、客户声明环境、数据等级、只读性质和已知限制；
   - 验证等级：Fixture、Mock/预检或真实只读已验证；
   - 安全的下一步入口：预置查询、进入对应 Workspace，或查看不可用原因。
3. 支持受控对话入口。用户询问“你现在可以做什么？”、“光模块健康能力的数据来自哪里？”或“为什么 Zabbix 现在不能查询？”时，服务端返回可追溯文字结论，并可通过合法 `ViewContext` 打开 `capability_catalog` Workspace 模块。
4. Scope 投影：
   - `operator` 只能看到其 Scope 可见的能力、来源状态和站点；
   - `project-admin` 可看到本项目已注册能力的完整脱敏运行状态；
   - 未注册能力、未来 Connector、endpoint、凭据、其他账号信息和原始监控事实不得泄露。

## 领域与契约边界

```text
Capability Registry + P6 数据源状态
        -> 受 Scope 限制的 Capability Catalog API / Tool
        -> Chat 文字结论 + ViewContext(capability_catalog)
        -> Capability Center Workspace 模块
```

- 优先复用现有 Capability Registry、Capability Catalog、P6 `RuntimeConfig` 和数据源公开状态；不得旁路 Registry 建立第二套能力清单。
- `capability_catalog` 是版本化、注册式 View；模型或前端不能生成任意页面、链接、能力 ID 或导航地址。
- 能力状态必须区分 `ready`、`not_configured`、`unavailable`、`disabled` 和 `scope_not_allowed`；实际 API 原因码可在任务协议中冻结，但不得丢失失败关闭语义。
- `ready` 仅表示当前已注册来源在其已验证等级下可用，绝不自动表示真实来源、L4 或 Production 已验证。
- 文档说明应来自注册的摘要/限制字段或受控路由，不得让 Web 读取仓库文件系统或暴露任意本地路径。

## 非目标

- 不在此功能中配置 Zabbix、Prometheus、Token、endpoint、数据源注册表或秘密注入。
- 不新增真实 Connector、L4、模型 Provider、SSO、告警规则、时序存储、自动修复或任何写操作。
- 不新增 SQLite 业务数据表；能力中心是 Registry 和 P6 状态的只读投影。
- 不允许管理员通过能力中心修改 Scope、权限、Tool、View Contract 或任意配置。P5D 既有的受限能力启停不因本功能扩大。
- 不把 Wiki、GitHub 或仓库文件浏览器实现为本功能的一部分。

## 验收条件

1. 实际浏览器中，用户能从普通产品入口打开能力中心，也能通过受控对话进入对应 Workspace。
2. 光模块健康明确显示为 Fixture/L0-L1；P5E 明确显示为零网络预检，不得伪称真实 Connector。
3. 未配置、未验证、停用或超出 Scope 的能力显示安全、可理解的原因；不得静默回退为 Fixture 或泄露超范围信息。
4. `operator` 不会看到超出自身站点 Scope 的数据源可见范围；`project-admin` 也只能看到脱敏平台状态。
5. 预置查询和 Workspace 跳转只针对已注册、已授权的 Capability/View；非法 ViewContext、Scope 扩张和未注册能力继续失败关闭。
6. P6 单一 Compose、SQLite 控制面边界、数据源状态、P5 账号隔离与严格只读回归均不被破坏。
7. Python、Web、P6 Compose smoke、实际浏览器验证和独立 Test Agent 验收均通过；完成包与正式测试报告可追溯。

## 风险与升级条件

- Capability Catalog、Tool Contract 或 View Contract 如需破坏性变更，Project Lead 必须先提交 ADR。
- 若能力中心需要保存收藏、偏好、看板布局或使用统计，属于新的持久化类别，必须单独评审；本轮不得顺带加入。
- 若需要显示真实来源配置、连接诊断详情或管理入口，必须先确认秘密边界和 RBAC，不得以“透明页”名义扩大 P5D 权限。
- UI 成功必须由实际浏览器交互证据证明，不能只凭源码、截图或静态测试。

## Project Lead 首轮授权与子代理边界

Project Lead 的第一轮只能做只读基线核验和实施计划。必须先核对现有 Capability Registry、P6 数据源状态、Scope 投影、Chat -> ViewContext -> Workspace 契约、现有测试和文档；随后提交 API/View 契约草案、文件边界、测试矩阵、风险和待负责人决定事项。项目负责人批准后才能创建 Delivery Agent 或修改产品文件。

获批实施后，Project Lead 应主动使用受控并行：

| 角色 | 范围 | 禁止范围 |
| --- | --- | --- |
| Delivery Agent A | Registry/API/Tool/ViewContext、Scope 投影、后端测试 | 前端布局、Compose、真实数据源连接 |
| Delivery Agent B | 能力中心 Workspace、状态/空态/窄屏、浏览器验证 | 后端权限语义、Registry 契约、Compose |
| Test Agent | 独立 API、Scope、异常、浏览器与回归验收，并出具正式报告 | 修改产品代码、公共契约或权限策略 |

Project Lead 独自串行负责共享契约、集成、Compose 回归、文档与最终汇报。不得让多个 Agent 同时修改公共 Contract、Compose、Scope 或 `main`。
