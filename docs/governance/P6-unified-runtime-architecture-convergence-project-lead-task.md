# P6 - 统一运行时与数据源架构收敛 Project Lead 任务书

- 状态：项目负责人已授权**只读接手核验、隔离 Fixture Compose 验证与 P6 方案**；未授权实现、真实外部连接、推送或合并。
- 任务性质：P5 冻结后的架构收敛阶段，不是 Production/商业化工程阶段。
- P5 功能冻结基线：`efd5dc15e71bd8c677db0067d3cbab1912575db3`，分支 `codex/p5b-local-account-history`；P6 必须从包含本任务书的该分支最新治理提交创建。
- `main` 基线：`21afa61a567d647a059fcc694e6019c6eb445a77`；不得直接修改。
- 预期工作分支：从冻结基线创建 `codex/p6-unified-runtime-convergence`；P5 不先单独合并，P6 以完整验收 PR 统一回到 `main`。

## 1. 项目负责人已作出的决定

1. AskLily 只保留一套应用运行形态、一份标准 Docker Compose 和同一套镜像；不维护 Developer、Standalone、Test、Production 等不同产品版本。
2. Fixture、Zabbix、Prometheus 是数据源状态，不是前端页面模式或独立产品版本。Fixture 只能显式启用，真实源失败时不得静默展示 Fixture 数据。
3. 客户决定连接的是测试环境还是生产环境。该上下文由部署配置明确声明并在 UI 展示；不得从 URL、主机名或前端开关自动推断，也不得由普通用户在 UI 切换。
4. AskLily 是信息聚合和分析层，不是第二个监控时序库。Zabbix、Prometheus 及其上游汇聚系统继续是监控事实的系统记录。
5. 平台继续严格只读。P6 不开放设备配置、工单、自动修复、模型 Provider、真实数据 L4、SSO、HA、Kubernetes、远程访问或商业化容量承诺。
6. P5 的界面与本机账号/历史/控制面保持冻结。P6 只为统一运行、数据源状态、迁移、测试和必要展示适配而改动；不开展新的业务 Capability 或泛化 UI 美化。

## 2. P6 要解决的已知不一致

| 领域 | 当前冻结状态 | P6 的收敛目标 |
| --- | --- | --- |
| 运行识别 | API 与展示仍使用 `developer` / `standalone` Profile 语义 | 删除产品级运行 Profile 分叉，使用统一运行时和显式数据源状态。 |
| Compose | P4 是 loopback、无状态、只读、无持久卷 Compose；这是已关闭的历史范围 | 建立一份可持久运行的标准 Compose，并保留最小权限与只读业务边界。 |
| 本地 SQLite | P5B/P5D 已使用账号、历史、审计 SQLite，但未纳入 P4 Compose | 明确 SQLite 的目录、卷、权限、迁移、备份/恢复边界和重启验收。 |
| 数据来源 | 光模块能力仍是 L0/L1 Fixture，且当前页面/API 暴露开发 Profile | 以注册数据源、连接状态、数据等级、客户声明环境标签表达来源；不伪称真实 Connector 已验证。 |
| P5 治理 | 自动化检查通过，但 Brief 状态、完成包和独立验收不完整 | 补齐 P5/P6 可追溯性与独立验收证据；P5 不在 P6 前标绿。 |

## 3. 首轮：只读接手核验与 P6 方案

在创建 Delivery Agent、改动产品文件、连接真实数据源、创建真实账号、推送或合并前，Project Lead 必须先提交一份 `P6` 接手核验与方案报告，并等待项目负责人批准。

为避免只凭源代码推断 Compose 行为，首轮明确**允许**运行当前 Docker Compose 的隔离 Fixture 验证；这是唯一运行形态的验证，不是另一种 Developer 版本。该验证必须同时满足：仅使用 L0/L1 Fixture、无客户 endpoint/凭据、独立临时项目名和数据卷、不复用或修改现有持久化数据、记录启动/重启/清理结果。它不得被表述为真实 Connector、测试环境或生产环境验证。

必须先阅读：

1. [工程基线](../architecture/engineering-baseline.md) 与 [工程开工文档 PDF](../../output/pdf/AskLily_工程开工文档_v0.1.pdf)
2. [P4 最终关闭记录](../reports/P4-final-closeout.md)、[P4 完成包](../reports/P4-completion-package.md) 与 [P4 Standalone 运维手册](../runbooks/P4-standalone-operations.md)
3. [P5 冻结交接报告](../reports/P5-phase-ii-functional-development-handoff.md)
4. P5A、P5B、P5D Capability Brief、[P5D 完成包](../reports/P5D-local-admin-control-plane-completion-package.md) 与 [P5D 本地后台操作手册](../runbooks/P5D-local-admin-operations.md)
5. ADR-0003、ADR-0004、ADR-0005，以及 [协作政策](collaboration-policy.md) 和 [风险变更审查](risk-change-review.md)
6. 当前 `compose.yaml`、Dockerfile、运行时配置、SQLite 存储代码、Capability Registry、Fixture/Connector 边界和现有测试。

该报告至少必须回答：

- 冻结基线与 `main` 的提交关系、工作区状态、文档与实现是否一致。
- 所有现存运行 Profile、Compose 入口、环境变量、卷、只读文件系统约束和本地数据库写入点。
- P5 功能在“本地开发进程”和“标准 Compose”下的实际可用差异；不得仅根据源代码推断。
- 拟议的单一运行时配置契约：数据源 ID、类型、启用状态、只读能力、连接健康、数据等级、最后检查时间、客户声明的环境标签与可见范围。
- 哪些平台状态允许持久化，哪些监控事实不得持久化；敏感配置、凭据注入、备份、迁移失败和数据库不可写时如何失败关闭。
- Fixture、未配置真实源、连接失败真实源三种状态的区别，以及“禁止静默回退”的实现和验收方式。
- 对 `Scope -> Tool -> ViewContext -> Workspace`、Capability Catalog、严格只读和公开仓库边界的影响。
- 一份实施分解、Agent 文件边界、迁移/回滚策略、测试矩阵、风险清单，以及需要项目负责人确认的决策。

首轮必须提出 ADR 草案；在项目负责人明确接受前，ADR 不是已生效架构决定，任何实现不得抢跑。

## 4. 获批后的实施范围

项目负责人批准 P6 方案和 ADR 后，Project Lead 可按原子 PR 范围串行协调下列工作，不得扩大到新业务功能：

1. **运行时与配置契约**：消除产品级 Profile 分叉；建立版本化数据源注册与状态模型，保持 Fixture 显式、来源可追溯和严格只读。
2. **标准 Compose 与持久化**：统一 API/Web 启动方式，为 SQLite 提供显式受控持久卷；保持最小写入目录、根文件系统限制、loopback 默认暴露与无敏感信息入库。
3. **P5 迁移与必要展示**：迁移既有本地账号、会话、审计；以数据源状态替代 `developer` / `standalone` 产品标签。不得借机重做 P5 视觉设计。
4. **测试、运维与治理**：补充配置、迁移、重启持久化、失败关闭、权限、浏览器和 Compose 验收；更新架构图、运行手册、Capability Catalog/完成包和独立测试报告。

公共契约、数据库迁移、Compose、Connector/数据源模型与安全配置由 Project Lead 串行协调。可并行的 Delivery Agent 必须使用独立 Worktree 或严格不重叠的目录边界；独立 Test Agent 不得修改产品代码。

## 5. 退出条件与验收证据

P6 只有在以下条件全部满足后才能请求负责人验收：

1. 一份标准 Compose 能运行 Fixture 场景，并在重启后保留允许持久化的平台状态；不要求也不得连接真实客户系统。
2. 数据源状态在 API、Chat/Workspace 和管理视图中一致可见，包含来源、数据等级、客户声明环境上下文和限制。
3. 真实源未配置或不可用时，能力明确失败/降级并说明原因；没有静默 Fixture 回退或把 L0/L1 表述为真实数据。
4. SQLite 迁移、目录权限、不可写、损坏与重启路径都有失败关闭或可操作的安全提示；数据库、凭据、真实 endpoint、真实数据均不进入公开仓库。
5. `Scope -> Tool -> ViewContext -> Workspace`、账号隔离、管理员限制与严格只读回归通过。
6. 实际浏览器验证至少覆盖：初始化/登录、Chat、进入 Workspace、数据源状态展示、管理员只读状态、账号历史，以及窄屏或减少动态效果路径。
7. 独立 Test Agent 出具测试报告；Project Lead 提交 P6 完成包、更新后的架构表/图、运行手册、已知限制和 PR/CI 证据。

P6 完成后，Project Lead 才可向项目负责人请求解除 P5 冻结，并提交下一项 P5 Capability 的候选与 Brief；不得自动开始。

## 6. 负责人沟通格式

首轮只读报告与后续周报均按以下顺序汇报：`基线与状态`、`已确认事实`、`待决定事项`、`建议方案`、`风险/非目标`、`下一步与所需授权`、`证据链接`。Project Lead 是唯一日常沟通入口；Delivery Agent 的自述不能替代独立测试证据或负责人接受。
