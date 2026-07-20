# P0 开工基线阶段报告

- 阶段：P0 开工基线
- 报告角色：Project Lead
- 报告日期：2026-07-20
- 集成候选分支：`chore/P0-integration`
- 初始集成候选提交：`1d3d919b2fcb6f53561a60e4e4aa07f7bfe83e3a`
- 远端草稿 PR：[#1](https://github.com/G31ght/AskLily/pull/1)
- 验收状态：**黄色 - 条件验收**

## 阶段结论

P0 的本地可控施工环境已经形成：Git 初始基线、工程目录骨架、忽略与协作治理、任务/ADR/Capability/完成包模板，以及不访问网络或数据源的 L0 CI 均已可重复验证。独立 Test Agent 已给出复验报告，未发现候选树内缺陷。私有 GitHub 单仓库已创建，初始 `main` 与 P0 候选已推送，草稿 PR #1 的远端 `L0 governance check` 已通过。

不能给出绿色结论：GitHub REST API 对该私有仓库返回 HTTP 403，要求升级至 GitHub Pro 或将仓库公开后才允许启用分支保护。仓库必须保持私有，且公开不是可接受的绕过方式；因此尚不能验证或强制禁止直接推送、PR 门禁和必需状态检查。这是明确的外部产品能力阻塞，不能由本地 CI、草稿 PR 或文档替代。

## 已完成

- 建立本地 Git 初始提交 `8029261`；后续 P0 修改全部位于独立集成分支，未再直接修改 `main`。
- 建立 `apps/web`、`services/{api,agent,worker}`、`packages/{contracts,domain}`、`connectors`、`tests/{fixtures,scenarios,reports}`、`infra`、`docs` 和 `.github` 骨架，未引入业务实现。
- 建立 `.gitignore`、`.gitattributes`、`CONTRIBUTING.md`、任务协议模板、ADR 模板、Capability Brief/Manifest 与功能完成包模板。
- 建立协作、任务状态和高风险变更审查规则；明确 Worktree、原子提交、独立测试与越权升级约束。
- 建立 GitHub Actions 的 PR/`main` L0 工作流和离线治理检查脚本；P1 才会在实际源码和锁定依赖进入后接入 Python/TypeScript 静态检查。
- 独立验收报告已提交，见 `tests/reports/p0-baseline-acceptance.md`。
- 创建私有仓库 `G31ght/AskLily`，设置 `origin`，推送初始 `main` 与 P0 候选，并创建草稿 PR #1。
- 远端 GitHub Actions `L0 governance check` 已通过，运行证据见 [Actions job](https://github.com/G31ght/AskLily/actions/runs/29738929672/job/88340850540)。

## 测试摘要

| 项目 | 状态 | 结论 |
| --- | --- | --- |
| L0 静态 | 通过 | `bash -n infra/ci/check-p0-governance.sh`、治理门禁和 `git diff --check` 通过。 |
| 模板与协作约束 | 通过 | 独立验收核对任务协议、ADR、Brief、Manifest、完成包及治理字段。 |
| 权限/密钥边界 | 通过（本地） | 代表性密钥、环境、构建与 IDE 路径被忽略；`.env.example` 可追踪。 |
| 业务/真实数据/写操作 | 通过 | 受追踪内容仅含骨架、文档、模板和离线 CI；未发现业务实现或真实数据。 |
| GitHub 私有性 | 通过 | `G31ght/AskLily` 已创建为私有仓库。 |
| GitHub 远端 CI | 通过 | 草稿 PR #1 的 `L0 governance check` 通过。 |
| GitHub `main` 保护 | 未通过 - 外部阻塞 | GitHub 对私有仓库分支保护返回 HTTP 403，要求 GitHub Pro 或公开仓库；公开违背 P0 私有仓库要求。 |

## 风险与限制

- **阻塞项：** 私有仓库的 GitHub 分支保护能力不可用。`main` 仍可能被拥有写权限的成员直接推送；本地协作政策不是远端强制门禁。
- **草稿 PR 未合并：** P0 候选保留在 PR #1，等待可满足“受保护 main”要求的仓库能力与项目负责人验收；不得绕过保护直接合并。
- **首期 CI 限制：** P0 仅有 L0 治理门禁；不虚构 Python/TypeScript lint、类型检查、服务集成、E2E 或真实 Connector 验证。

## 建议与下一步

建议项目负责人给予 **条件接受**，但不进入 P1。请在以下方案中选择其一后再继续：

1. 将该私有仓库迁移至支持私有仓库分支保护的 GitHub 计划或组织；
2. 为当前账户启用支持该能力的 GitHub 计划；
3. 明确批准一项记录在 ADR 中的替代治理方案（该方案不能将仓库改为公开）。

在受保护 `main` 可实际复验前，草稿 PR #1 不合并，Project Lead 不请求 P1 授权。

## 证据

- 初始基线：`8029261e3f328efb80d8c8201b8d97be604170ea`
- P0 目录骨架：`bef69ba`
- P0 离线 CI：`492b0c0`
- P0 治理与模板：`4b58c0a`
- 独立验收：`1d3d919`，`tests/reports/p0-baseline-acceptance.md`
- 私有远端：`https://github.com/G31ght/AskLily`
- 草稿 PR：`https://github.com/G31ght/AskLily/pull/1`
- 远端 CI：`https://github.com/G31ght/AskLily/actions/runs/29738929672/job/88340850540`
