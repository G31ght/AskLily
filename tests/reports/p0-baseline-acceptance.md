# P0 开工基线独立验收报告

- 验收任务：P0-04
- 执行角色：独立 Test Agent
- 验收工作树：`/private/tmp/asklily-p0-test`
- 目标分支：`test/P0-baseline`
- 候选提交：`4b58c0a6910bc4af4b2fee99b71de71e96045d59` (`docs(P0): add governance and delivery templates`)
- 验收范围：P0 基础治理、目录骨架、离线 L0 CI 与协作模板；不覆盖业务功能、真实数据源或写操作。
- 总体建议：**黄色（条件接受）**。候选树内的 P0 可验收项均通过；GitHub 私有远端与受保护 `main` 只能在有效 GitHub 凭据和远端仓库存在后验收，当前为外部阻塞，不能推断为已通过。

## 执行记录

| 编号 | 命令或检查 | 结果 | 证据与结论 |
| --- | --- | --- | --- |
| A1 | `git rev-parse HEAD`、`git log -1 --oneline`、`git status --short --branch` | 通过 | 干净候选工作树，HEAD 为 `4b58c0a`，分支为 `test/P0-baseline`。 |
| A2 | `bash -n infra/ci/check-p0-governance.sh` | 通过 | Shell 语法检查无输出、退出码 0。 |
| A3 | `bash infra/ci/check-p0-governance.sh` | 通过 | L0 离线治理门禁通过：目录、治理文件、代表性本地机密/构建/IDE 忽略规则，以及可追踪的 `.env.example` 均已验证。 |
| A4 | `git diff --check` | 通过 | 候选提交工作树无空白错误，命令退出码 0。 |
| A5 | 对任务协议模板执行字段存在性检查 | 通过 | 包含任务/Capability ID、责任角色、目标分支、基线提交、允许范围、业务/权限/异常/回归验收、禁止操作、自测及独立测试证据、缺陷状态。 |
| A6 | 对 ADR、Capability Brief、Manifest、功能完成包模板执行字段存在性检查 | 通过 | ADR 包含状态、问题、候选方案、决定、影响、验证与复审；其余模板覆盖用户价值、范围/非目标、依赖、验收、风险、契约/证据/限制与绿黄红结论。 |
| A7 | `git check-ignore --no-index` 反例检查 | 通过 | `.env`、`.env.local`、`secrets/local.pem`、`.venv/`、`__pycache__/`、`node_modules/`、`dist/`、`coverage/`、`.idea/` 均被忽略；`.env.example` 不被忽略。 |
| A8 | `git ls-tree -r --name-only HEAD`、实现/数据扩展名扫描与关键字扫描 | 通过 | 受版本控制的内容仅为治理文档、模板、目录占位符和离线脚本；未发现 Python/JS/TS/SQL 等业务实现或 CSV/JSON/XLSX/Parquet/DB 等数据文件。关键词扫描仅命中目录名称，无 Connector 实现、真实数据或写操作。 |
| A9 | `git remote -v`、`gh auth status`、本地分支配置检查 | 未测（外部阻塞） | 未配置远端；`gh auth status` 明确显示默认 GitHub Token 无效。无法核验仓库是否私有、默认分支是否为 `main`，或 `main` 是否禁止直接推送/要求 PR 与状态检查。不得从本地模板或 CI 文件推断这些 GitHub 远端策略已经生效。 |

## 模板核验明细

- 任务协议：`.github/ISSUE_TEMPLATE/task-protocol.md`
- ADR：`docs/adr/0000-template.md`
- Capability Brief：`docs/templates/capability-brief.md`
- Capability Manifest：`docs/templates/capability-manifest.yaml`
- 功能完成包：`docs/templates/feature-completion-package.md`

上述文件均为模板，不注册 Capability、不配置数据源，也不引入业务行为。

## 范围结论

本候选提交符合 P0 的本地范围：建立了 `apps/`、`services/`、`packages/`、`connectors/`、`tests/`、`infra/`、`docs/` 与 `.github/` 所需骨架；CI 只在 PR/`main` 运行离线治理脚本。验收期间未启动服务、未访问网络、未访问真实数据源、未执行数据或业务写操作。

## 缺陷、风险与后续准入

- **外部阻塞（黄色）：** GitHub 凭据失效且当前工作树无远端，无法确认私有仓库、默认 `main`、分支保护和必需状态检查。该项必须由具备仓库管理员权限的 Project Lead 在远端配置后复验。
- **未发现候选树内缺陷。** 本报告不以本地 CI 工作流代替 GitHub 分支保护验收。
- **P1 准入条件：** 远端私有仓库与 `main` 保护规则复验通过；并保留本报告中的离线 L0 通过证据。

## 2026-07-20 复验记录

- 复验对象仍为候选提交 `4b58c0a6910bc4af4b2fee99b71de71e96045d59`；本验收分支当前 HEAD 为仅包含本报告的后继提交 `8ace32a`。
- 已再次执行 `bash -n infra/ci/check-p0-governance.sh`、`bash infra/ci/check-p0-governance.sh` 与 `git diff --check`，三项退出码均为 0。
- 重新盘点受跟踪文件：除治理文档、模板、离线门禁、CI 配置、此验收报告及目录 `.gitkeep` 外无其他内容；`apps/`、`services/`、`packages/`、`connectors/` 中均只有 `.gitkeep`，因此无业务实现、真实数据文件或 Connector 代码。
- GitHub 私有仓库和 `main` 分支保护**未测且受阻塞**：现有验收记录确认 `gh` 凭据无效，且本任务禁止网络访问；本地证据不能替代远端私有性或保护规则验证。
- 复验建议维持：**黄色（条件接受）**。本地 P0 基线为绿色；远端私有仓库与 `main` 保护复验前，整体不得标记为绿色。
