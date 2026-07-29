# P5E、P6 与 P6 CI 结项及工作交接

- 交接日期：2026-07-29
- 交接审计基线：`main` `f4dae7a2a6d5917fccd9028bfeeafd5a4b67b54a`
- 合并证据：PR #12 已合并，且 L0 governance、Python、Web、P6 unified Compose smoke 均通过。
- 本地运行：`http://127.0.0.1:8080`，默认显式 Fixture；不连接真实来源。

## 已关闭事项

| 项目 | 结论 | 主要证据 |
| --- | --- | --- |
| P6 统一运行时与数据源架构收敛 | 已接受、已合并 | [P6 完成包](P6-unified-runtime-convergence-completion-package.md)、[ADR-0006](../adr/0006-unified-runtime-and-data-source-state.md) |
| P5E 只读监控来源预检 | 已接受、已合并 | [P5E 完成包](P5E-readonly-monitoring-source-readiness-completion-package.md)、`monitoring-source-readiness` Capability |
| P6 CI 合同收敛 | 已关闭、CI 全绿 | [P6 CI 结项记录](P6-unified-runtime-ci-closeout.md) |
| Git 历史收敛 | 已完成 | 本地与远端仅保留 `main`；P0-P4 历史分支及 PR 临时分支已删除 |

## 当前运行合同

1. 只有一个产品运行入口：根目录 `compose.yaml` 的 `storage-init`、`api`、`web`。
2. 环境由客户声明的数据源上下文决定；`fixture`、`test`、`production` 不是镜像、Compose 或前端版本切换。
3. 默认 `deploy/runtime/sources.fixture.json` 显式启用 L0/L1 Fixture；Fixture 不会替代未配置或异常的真实来源。
4. SQLite 仅保存平台控制面、身份、历史、审计、迁移和安全的数据源状态；不得保存 endpoint、凭据、PromQL、标签、原始 Observation/Event 或监控载荷。
5. P5E 仅预检：Zabbix allow-list 为 `host.get`、`item.get`、`history.get`；Prometheus 为 `query`、`query_range`；没有 HTTP 调用。

## 验证与运维入口

- 本地启动与恢复：[P6 统一运行时运维手册](../runbooks/P6-unified-runtime-operations.md)。
- 本地管理员操作：[P5D 本地后台管理操作](../runbooks/P5D-local-admin-operations.md)。
- 结项回归：`pytest -q`（37 passed）、`pnpm typecheck`、`pnpm test:web`（2 passed）、`bash infra/ci/check-p0-governance.sh`、`docker compose config --quiet`。
- 若做隔离 Compose 验证，必须使用临时项目名、临时端口和临时卷，并在记录结果后执行 `down --volumes --remove-orphans`；不得复用客户或既有持久化数据。

## 仍然禁止或待单独授权的事项

- 真实 Zabbix、Prometheus、客户 endpoint、Token/凭据、L4 数据读取、模型 Provider、写操作。
- Production、HA、Kubernetes、灾备、多区域、容量或 SLA 承诺。
- 新 P5 Capability 的自动开工：必须先有独立 Capability Brief、任务协议、验收范围和负责人批准。

## 下一位 Project Lead 的首轮动作

1. 阅读 [工程基线](../architecture/engineering-baseline.md)、ADR-0003 至 ADR-0006、本交接文档和拟议 Capability Brief。
2. 做只读基线核验；确认 `main`、CI、Fixture 运行状态与待办范围一致。
3. 先提交方案和风险/授权清单，等待负责人批准后才创建 Delivery Agent、变更代码、接触任何真实来源或执行新的隔离 Compose 验证。
