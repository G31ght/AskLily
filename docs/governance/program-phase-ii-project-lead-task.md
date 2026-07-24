# Program Phase II - 新任 Project Lead 任务书

- 状态：待项目负责人授权
- 任务类型：阶段接手、基线核验与产品成熟化计划
- 初始基线：`21afa61a567d647a059fcc694e6019c6eb445a77`
- 上一阶段：P0-P4 已关闭；P3 真实 Zabbix L4 延期；P6 Production 规划暂停

## 1. 授权目标

接手 AskLily 的下一轮工作，将项目从“平台基础与 Standalone 硬化”推进到“产品成熟化与能力横向扩展”。本任务书不是对任意具体功能的实现授权。

Program Phase II 的产品方向：

1. 让前端逐步具备成熟运维平台的清晰性、稳定性和工作台体验。
2. 在不破坏既有 Scope、Fixture、只读、Tool、ViewContext 和 Capability Registry 语义的前提下，填充后端与领域能力。
3. 仍以 Capability Brief 和纵向切片交付每项能力，不把“功能填充”变成无边界的大重构。

## 2. 先读材料

在创建任何 Delivery Agent、修改项目文件或运行有副作用的操作前，Project Lead 必须阅读：

1. [工程基线](../architecture/engineering-baseline.md)
2. [归档工程开工文档 PDF](../../output/pdf/AskLily_工程开工文档_v0.1.pdf)
3. [P4 最终关闭记录](../reports/P4-final-closeout.md)
4. [P4 完成包](../reports/P4-completion-package.md)
5. [P4 阶段报告](../reports/P4-stage-report.md)
6. [P4 Standalone Brief](../capabilities/P4-STANDALONE-brief.md)
7. [P4 Standalone 运维手册](../runbooks/P4-standalone-operations.md)
8. [ADR-0003 Zabbix L4 数据处理边界](../adr/0003-zabbix-live-readonly-data-handling.md)
9. [多 Agent 协作政策](collaboration-policy.md) 与 [风险与变更审查](risk-change-review.md)

## 3. 第一轮交付 - 只读接手核验

第一轮只允许产生一份 Phase II 接手核验与计划报告。不得实现产品功能、修改核心契约、接入外部系统或启动 Delivery Agent。

报告必须包含：

- `main` 基线、工作区状态、文档可追踪性与 P0-P4 状态的一致性核验。
- 当前可运行能力、能力状态、已有 Fixture/Scenario 与未完成限制的清单。
- P3 L4 延期、严格只读、公开仓库敏感信息约束和 Standalone 非 Production 边界的复述。
- Program Phase II 的分批路线图、任务粒度、依赖关系和建议的阶段退出条件。
- 前端体验路线图，包括要保留的行为、可重构的呈现层、必须进行的实际浏览器验证和回归方式。
- 首批最多三个能力候选；每项说明用户价值、依赖、数据等级、Scope、非目标、风险和验收方向。
- 需要项目负责人做出的决定；没有决策的问题不得假装已确定。
- 推荐的子代理分工与并行边界。首轮通常无需 Delivery Agent；如需专项审阅，仅可请求只读 Reviewer。

Project Lead 提交该报告后，必须等待项目负责人批准路线图，才可创建实现任务或 Delivery Agent。

## 4. Phase II 的工作流

经项目负责人批准后，按以下三条工作线推进，但不得把它们合并成一个无边界分支：

| 工作线 | 目标 | 典型任务 | 不可破坏的约束 |
| --- | --- | --- | --- |
| UX 成熟化 | 让 Chat、Workspace 和能力目录具备一致、清晰、可操作的运维体验 | 设计令牌、布局、通用工作台组件、空/加载/错误状态、信息层级 | Scope、Fixture 来源、严格只读提示、Chat -> ViewContext -> Workspace 行为、可访问性 |
| 平台共性补齐 | 使多个业务能力可复用相同平台能力 | Capability Catalog 完整度、View Registry 表达、Fixture/Scenario 管理、审计展示、测试辅助 | 不绕开版本化契约，不把 Demo 元数据宣称为生产能力 |
| 业务能力扩展 | 按价值逐项新增后端、Tool 和工作台能力 | 新 Capability Brief、Fixture/Scenario、领域规则、API、Tool、View、E2E | 每项独立验收；先 Fixture/Scenario，后讨论真实 Connector |

每项实现任务均需创建 Capability Brief 和 GitHub Task Protocol，明确允许目录、依赖契约、非目标、Scope、异常路径、Fixture/Scenario、E2E、回归、风险和完成包要求。

## 5. 前端成熟化的硬性要求

- 前端美化不得仅凭源码、截图或静态测试宣称成功；必须启动实际页面并用浏览器检查相关交互。
- 每个 UI 改造任务必须写明保留行为、目标场景、浏览器验证路径和回归范围。
- 不得为视觉效果改变 API 契约、权限边界、Fixture 语义、数据来源披露或只读边界。
- Workspace 中的继续对话、ViewContext 驱动的定位/筛选和异常/空数据状态是产品行为，不是可随意删除的装饰。
- 优先建立可复用的设计令牌、布局和工作台组件，而不是按单个页面复制样式。

## 6. 明确禁止与需升级事项

在 Phase II 中，下列事项仍须先提交 ADR 并获得项目负责人批准：

- 真实数据、真实 Zabbix L4、外部网络访问、模型 Provider、持久化、数据库、数据保留或新敏感数据。
- 写操作、自动修复、设备配置、工单写入或权限/RBAC/项目隔离变更。
- Kubernetes、HA、灾备、Production 承诺、容量目标、独立服务或关键技术栈变化。
- 对 Resource、Event、Tool、ViewContext 或 Scope 的破坏性变更。

P6 Production 规划保持暂停。P5 的能力扩展含义仅在经批准的 Phase II 路线图中按 Capability 逐项开展，不构成一次性开放全部能力范围。

## 7. 汇报与验收

Project Lead 是项目负责人的唯一日常汇报入口。其汇报必须包含基线、完成项、下一步、风险、所需决定和证据链接；不能只报告“已完成”。

每个完整能力结束时，Project Lead 必须提交一页功能完成包，至少说明：状态、已完成与未包含内容、静态/单元/契约/集成/E2E/真实数据/回归测试摘要、风险限制、接受建议、基线提交、功能说明和完整测试报告位置。

独立 Test Agent 负责完整能力的跨模块、权限、异常和回归验收，默认不得修改业务代码或产品契约。无独立验收、无证据或存在未接受高风险时，功能不得标记为绿色。

## 8. Project Lead 对项目负责人的首轮请求

Project Lead 完成只读接手核验后，应只请求以下确认：

1. 是否接受 Program Phase II 路线图。
2. 首批 UX 成熟化任务的优先级和视觉目标。
3. 从候选能力中优先启动哪一项 Capability Brief。
4. 是否接受每项完整能力必须独立 Test Agent 验收的成本与节奏。

在收到这些确认前，Project Lead 不得自行选定新能力、扩大数据范围或让多个 Delivery Agent 无目的并行施工。
