# P6 统一运行时与数据源架构收敛完成包（待负责人验收）

- 实施分支：`codex/p6-unified-runtime-convergence`
- 施工基线：`ada7cadd97354ea77eee9e6fd3a7c438adc7aa2b`（包含 P6 实施授权治理记录）
- P5 冻结点：`efd5dc15e71bd8c677db0067d3cbab1912575db3`
- `main` 基线：`21afa61a567d647a059fcc694e6019c6eb445a77`
- 状态：项目负责人于 2026-07-28 接受；实现、自测与独立只读验收完成。P5 可按新的、单独批准的 Capability Brief 继续。

## 已交付收敛

| 目标 | 实现与证据 |
| --- | --- |
| 一套运行时与镜像 | `compose.yaml` 不含 product Profile；`storage-init`、`api`、`web` 是唯一启动拓扑，API 与 Web 镜像均由标准 Compose 构建。 |
| 显式数据源状态 | `deploy/runtime/sources.fixture.json` 是版本化、只读的显式 Fixture 注册表；`runtime.py` 对环境、来源类型、只读、L0/L1 和配置版本失败关闭。 |
| 禁止静默回退 | 未配置来源返回 `data_source_not_configured`；P6 未验证的 Zabbix/Prometheus 返回 `data_source_unavailable`；二者均不运行 Fixture 查询。 |
| UI 一致性 | `/v1/session`、`/v1/data-sources`、健康检查和管理控制面返回客户声明环境及脱敏数据源状态。前端仅显示该状态，没有 Profile 或来源切换器。 |
| SQLite 平台边界 | 命名卷只挂载 `/var/lib/asklily`；目录 `0700`、数据库 `0600`。迁移版本与安全数据源状态可保存；原始监控 Observation/Event、endpoint、凭据和载荷没有表或写入点。 |
| 恢复与回滚 | `ops/runtime/backup_state.py` 做本地一致性 SQLite 备份及 SHA-256；部署材料备份与平台状态备份明确分离。迁移、损坏、不可写异常返回安全错误或停止启动。 |
| API 重启恢复 | Nginx 使用 Docker 内部 DNS 变量解析，避免旧上游地址长期失效。API 停止期间可能有短暂 502；恢复后健康与会话均成功，P6 不把这表述为 HA/SLA。 |

## 实际隔离 Fixture 验证

全部验证仅使用本机 Colima、临时项目名、临时命名卷和显式 L0/L1 Fixture；没有客户 endpoint/凭据、真实来源、镜像推送或本地镜像导出。

| 项目 | 结果 |
| --- | --- |
| `asklily-p6-verify-728` | 构建、`up --wait`、经 Web 的 `/health` 与 `/v1/session` 成功；重启 API 后首次探测短暂 502，重试后恢复；已 `down --volumes --remove-orphans` 并核对无容器/卷/网络残留。 |
| `asklily-p6-final-728` | 启动成功；重启前 `audit_events=1`，重启后 `audit_events=2`；`schema_migrations=1,2`；数据卷目录 `0700`，数据库 `0600`；已清理。 |
| `asklily-p6-browser-728` | 浏览器实际完成本地 Fixture 初始化、登录、Chat/Workspace、后台系统状态与 390px 窄屏检查；显示 `fixture · L0_L1`、`fixture-optic-health-l0-l1: ready`、只读和不显示 endpoint/凭据/原始数据；已清理。 |
| `asklily-p6-acceptance-728` | 最终代码构建、启动、operator Session 的数据源站点投影为 `site-a`、API 重启恢复和 Optic Health 查询均成功；已清理。 |

## 自动化与独立验收

- Python：`34 passed`（`pytest -q`）。
- 静态检查：`ruff check packages services connectors tests` 通过；`mypy` 通过。
- 前端：`pnpm typecheck` 与 `pnpm test:web`（2 项）通过。
- 独立 Test Agent：完成只读复核。最初发现的数据源 Scope 未执行、Session 可见站点泄露与 README 误删卷命令均已修复；复核确认 `session=200 [site-a]`、查询仅 `site-a`、越出来源范围的 ViewContext 返回 `403 data_source_scope_not_allowed`。独立 Agent 的测试批次为 `33 passed`，Ruff/mypy、前端 TypeScript/2 项 Web 测试、离线资产校验和 diff 检查均通过；随后 Project Lead 新增损坏 SQLite/控制面数据落库边界测试并取得最终 `34 passed`。

## 已知限制与非目标

- P6 没有连接 Zabbix、Prometheus、客户系统或 L4；它们仍需 ADR-0003 的环境前提及独立 Capability。
- 单一 API 重启期间的短暂 502 是单实例恢复窗口，不是失败回退，也不构成 HA 承诺。
- SQLite 备份包含获准的平台控制面（包括 P5 本地账号/历史），必须本机受限保存；它不是远程备份功能，也绝不能含原始监控事实。
- P5 冻结已解除；本完成包不自动批准或启动下一项 P5 Capability。

## 负责人验收所需决定

P6 已接受。下一项 P5 Capability 必须仍以独立 Brief、任务协议和验收证据推进。
