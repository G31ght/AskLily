# P5 阶段交接报告：前端检查点与功能开发转场

- 日期：2026-07-28
- 交接分支：`codex/p5b-local-account-history`
- 前端检查点：`16f1d75 feat(P5A): add conversation delete action`
- 冻结基线：`efd5dc15e71bd8c677db0067d3cbab1912575db3`（本交接报告）
- 当前状态：**冻结，待 P6 架构收敛完成后再继续 P5 能力扩展。**
- 结论：当前前端与本机持久化能力是有价值的功能检查点，但不是可独立结项或可直接合并为运行基线的 P5 阶段交付。

## 1. Git 与工作区核验

本报告生成前，当前分支 HEAD 为 `16f1d7541caf4f0e5533c48208972fe0dda0ad00`。`git status --porcelain=v2`、工作区与暂存区差异检查均无输出；`git diff --check`、`git diff --cached --check` 和 `git fsck --no-dangling` 均通过。

本次交接报告本身将单独提交；提交完成后应再次确认工作区为空。未对 `main` 执行直接修改、重置、合并或推送。

## 2. 当前已交付的产品检查点

| 区域 | 已交付状态 | 仍受限于 |
| --- | --- | --- |
| P5A 前台体验 | 自然语言优先的对话壳、文章式回答、深蓝对话背景、空会话粒子画布、固定 Fixture 待关注问题、Chat/Work 布局过渡、紧凑工具栏、窄屏适配与减少动态效果降级。Work Mode 仅由服务端受限展示指令进入；Developer Profile 有明确标记的调试入口。 | 没有真实模型、真实预测或任意模型生成页面；当前只有已注册的 Fixture 模块。 |
| 本地账号与历史 | 本地登录、一次性首位管理员初始化、按账号保存/恢复/继续对话、账号隔离、用户主动删除、历史与审计列表内部滚动。最近对话支持右键“删除对话”菜单与二次确认。 | 仅单机本地 SQLite；无 SSO、LDAP、OAuth、同步、保留期或真实对话数据。 |
| P5D 管理控制面 | 项目管理员从前台头像菜单进入本机后台；可查看能力、账号、审计与只读系统状态，可管理已注册业务 Capability、operator 账号、会话。前台不再提供自助注册。 | 后台 URI 仅降低发现概率，真正的访问控制是服务端 `project-admin`；不能创建管理员、扩大 Scope、授予写权限或配置未注册参数。 |
| P4 Standalone | 原有单机、loopback、无状态 Compose 资产及离线校验仍在。 | 它不是 P5 本地持久化 Profile，也不是 Production、HA、真实数据或 L4 交付。 |

## 3. 可复用的功能基座

- `Scope -> Tool -> ViewContext -> Workspace` 与服务器端 Scope 收窄仍是查询和展示的唯一授权链路。
- 展示契约含受限 `presentation.mode` 与模块列表；前端按服务端返回的顺序渲染，不能由前端根据上下文长度自行进入 Work Mode。
- 光模块健康能力仍是唯一已验证的业务 Fixture 能力，来源显式标记为 L0/L1 Fixture，并保留“无真实 Connector、无写操作”的限制。
- 本地身份、会话、对话、账号、最小审计和 Capability 启停均已具备 API、数据库迁移和权限测试基础；新能力必须复用这些边界，而不是旁路实现。

## 4. 已执行验证

| 验证 | 结果 |
| --- | --- |
| Python API、权限、历史、管理员与 E2E 回归 | 29 passed |
| Ruff | 通过 |
| Mypy | 通过，17 个源文件无问题 |
| Web TypeScript、Vitest、生产构建 | 通过；Vitest 2 passed |
| P4 Standalone 离线资产策略 | `ops/standalone/verify-assets.sh` 通过 |
| Git 完整性与差异检查 | 通过，报告生成前工作区干净 |

本机在本次交接核验时没有运行中的 API 或 Web 开发服务。当前会话仅能读取 Docker 客户端信息，不能连接 Docker 守护进程，且 `docker compose` / `docker-compose` 运行时未安装；因此本次只复核了 P4 的离线资产，不重新声明本机 Compose 启动验收。

## 5. 必须继续遵守的边界

- 严格只读：不得新增设备配置、工单写入、自动修复或其他运维业务写操作。
- 数据等级：当前只使用 L0 Fixture 与 L1 Synthetic Scenario；P3 真实 Zabbix L4 仍延期，真实数据、真实 Provider、外部网络访问须先经 ADR 和单次批准。
- 公开仓库：不得提交凭据、Token、真实终端、真实对话、SQLite 数据库、未入库后台路径或其他敏感信息。
- P4 Standalone：继续是受控单机无状态 Profile，非 Production；P5 的本地持久化不回溯改写 P4 关闭结论。
- 新功能：每项业务能力都必须先有 Capability Brief、Fixture/Scenario、受限 Tool/View、Scope 验证、E2E 与完成记录；不得因前端已有 Work Mode 而绕过服务端验证。

## 6. 文档状态与下一步

`P5A-NATURAL-LANGUAGE-WORKSPACE-UX-brief.md` 和 `P5B-LOCAL-ACCOUNT-HISTORY-brief.md` 曾保留早期“已批准；等待实现任务协议”的表述；该表述已在本次冻结决定中更正为“已实现检查点，冻结待 P6”。它们仍是需求与验收依据，但不构成 P5 已绿色结项的证据。

下一阶段先执行 P6 架构收敛，而非继续扩展前端外观或新增业务 Capability。P6 验收完成前，不启动新的 P5 Capability Brief、前端美化批次或真实数据接入；仅允许处理 P6 所需的运行时、配置、迁移、测试和文档收敛工作。

## 7. 冻结决定与交接

1. 将当前前端视为可用的 P5A 视觉与交互检查点；不在 P6 之外开启泛化美化工作流。
2. P5 的本地账号、审计、受限展示与光模块健康 Fixture 基座保留，但其运行与持久化形态必须在 P6 中统一后才可作为后续能力扩展基础。
3. P5 不单独合并到 `main`。P6 应从本冻结基线创建独立分支，并以涵盖 P5 冻结点与 P6 收敛结果的完整验收 PR 回到 `main`。
4. 真实数据、SSO、持久化保留策略、Production/HA 和 P3 L4 均不随 P6 自动开放。

## 8. 冻结原因与 P6 入口

本次独立审计确认：P5 的自动化检查已通过，但当前代码同时存在 `developer` / `standalone` 运行 Profile；P5 的本地 SQLite 账号、历史与审计能力尚未纳入 P4 的无状态、只读、无持久卷 Compose 运行形态。因此不能把 P5 表述为“统一 Docker 运行基线已验证”。

项目负责人已决定 AskLily 只保留一套应用运行形态：同一套 Compose 与镜像既可连接 Fixture，也可连接客户指定的测试或生产 Zabbix/Prometheus。测试或生产由客户声明的数据源上下文决定，不由前端模式切换或 URL 自动推断。实现该决定的唯一入口是 [P6 统一运行时与数据源架构收敛任务书](../governance/P6-unified-runtime-architecture-convergence-project-lead-task.md)。
