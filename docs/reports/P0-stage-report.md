# P0 开工基线阶段报告

- 阶段：P0 开工基线
- 报告角色：Project Lead
- 报告日期：2026-07-20
- 集成候选分支：`chore/P0-integration`
- 初始集成候选提交：`1d3d919b2fcb6f53561a60e4e4aa07f7bfe83e3a`
- 远端草稿 PR：[#1](https://github.com/G31ght/AskLily/pull/1)
- 基线变更：ADR-0001 已由项目负责人批准并执行；仓库为公开可审查仓库，`main` 已启用远端保护。
- 验收状态：**黄色 - 条件验收**

## 阶段结论

P0 的本地可控施工环境已经形成：Git 初始基线、工程目录骨架、忽略与协作治理、任务/ADR/Capability/完成包模板，以及不访问网络或数据源的 L0 CI 均已可重复验证。独立 Test Agent 已给出复验报告，未发现候选树内缺陷。私有 GitHub 单仓库已创建，初始 `main` 与 P0 候选已推送，草稿 PR #1 的远端 `L0 governance check` 已通过。

原“私有仓库”P0 基线已由 ADR-0001 替换。公开仅适用于当前不含业务实现、真实数据或密钥的 P0 内容，并不放宽后续敏感信息治理。`main` 已由 GitHub 实际强制 PR、1 项审批、`L0 governance check`、管理员约束、禁止强推和禁止删除。候选仍在草稿 PR #1，等待项目负责人验收后才可合并，因此本阶段维持黄色。

## 已完成

- 建立本地 Git 初始提交 `8029261`；后续 P0 修改全部位于独立集成分支，未再直接修改 `main`。
- 建立 `apps/web`、`services/{api,agent,worker}`、`packages/{contracts,domain}`、`connectors`、`tests/{fixtures,scenarios,reports}`、`infra`、`docs` 和 `.github` 骨架，未引入业务实现。
- 建立 `.gitignore`、`.gitattributes`、`CONTRIBUTING.md`、任务协议模板、ADR 模板、Capability Brief/Manifest 与功能完成包模板。
- 建立协作、任务状态和高风险变更审查规则；明确 Worktree、原子提交、独立测试与越权升级约束。
- 建立 GitHub Actions 的 PR/`main` L0 工作流和离线治理检查脚本；P1 才会在实际源码和锁定依赖进入后接入 Python/TypeScript 静态检查。
- 独立验收报告已提交，见 `tests/reports/p0-baseline-acceptance.md`。
- 创建私有仓库 `G31ght/AskLily`，设置 `origin`，推送初始 `main` 与 P0 候选，并创建草稿 PR #1。
- 远端 GitHub Actions `L0 governance check` 已通过，运行证据见 [Actions job](https://github.com/G31ght/AskLily/actions/runs/29738929672/job/88340850540)。
- 项目负责人已批准 ADR-0001；仓库可见性已复验为 `PUBLIC`，并已启用和复验 `main` 分支保护。

## 测试摘要

| 项目 | 状态 | 结论 |
| --- | --- | --- |
| L0 静态 | 通过 | `bash -n infra/ci/check-p0-governance.sh`、治理门禁和 `git diff --check` 通过。 |
| 模板与协作约束 | 通过 | 独立验收核对任务协议、ADR、Brief、Manifest、完成包及治理字段。 |
| 权限/密钥边界 | 通过（本地） | 代表性密钥、环境、构建与 IDE 路径被忽略；`.env.example` 可追踪。 |
| 业务/真实数据/写操作 | 通过 | 受追踪内容仅含骨架、文档、模板和离线 CI；未发现业务实现或真实数据。 |
| GitHub 可见性变更 | 通过 | `G31ght/AskLily` 已按 ADR-0001 复验为 `PUBLIC`。 |
| GitHub 远端 CI | 通过 | 草稿 PR #1 的 `L0 governance check` 通过。 |
| GitHub `main` 保护 | 通过 | GitHub API 已确认 PR、1 项审批、`L0 governance check`、管理员强制、禁止强推和禁止删除。 |

## 风险与限制

- **公开范围限制：** 仓库已公开；后续不得提交真实数据、密钥、私有基础设施信息或任何未按 ADR-0001 复审的敏感内容。
- **草稿 PR 未合并：** P0 候选保留在 PR #1，等待可满足“受保护 main”要求的仓库能力与项目负责人验收；不得绕过保护直接合并。
- **首期 CI 限制：** P0 仅有 L0 治理门禁；不虚构 Python/TypeScript lint、类型检查、服务集成、E2E 或真实 Connector 验证。

## 建议与下一步

远端保护与 CI 已复验通过。请项目负责人审阅并接受草稿 PR #1；PR 转为可审阅并获得所需审批后，可按保护规则合并。P1 授权另行请求。

## 证据

- 初始基线：`8029261e3f328efb80d8c8201b8d97be604170ea`
- P0 目录骨架：`bef69ba`
- P0 离线 CI：`492b0c0`
- P0 治理与模板：`4b58c0a`
- 独立验收：`1d3d919`，`tests/reports/p0-baseline-acceptance.md`
- ADR-0001：`docs/adr/0001-public-repository-for-branch-protection.md`
- 私有远端：`https://github.com/G31ght/AskLily`
- 草稿 PR：`https://github.com/G31ght/AskLily/pull/1`
- 远端 CI：`https://github.com/G31ght/AskLily/actions/runs/29738929672/job/88340850540`
- ADR 更新后的远端 CI：`https://github.com/G31ght/AskLily/actions/runs/29739252802/job/88341897760`
- `main` 保护 API：已于 2026-07-20 复验 PR、审批、L0 状态检查、管理员强制、禁止强推与删除均生效。
