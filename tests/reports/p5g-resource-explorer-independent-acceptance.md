# P5G 资源检索与详情工作台独立验收报告

- 日期：2026-07-31
- 角色：独立 Test Agent（只读验收）
- 范围：Fixture 资源目录、Registry/API/Scope、反枚举、ViewContext、Chat-to-Workspace、健康摘要与 P5F 回归
- 结论：**条件通过**。独立静态、单元和 TestClient API 验收未发现阻断问题。Compose 与实际浏览器由 Project Lead 负责，本报告不将其表述为独立复现证据。

## 独立执行证据

| 项目 | 命令或方法 | 结果 |
| --- | --- | --- |
| Python 全量回归 | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` | 53 passed |
| Ruff | `.venv/bin/ruff check .` | 通过 |
| Mypy | `.venv/bin/mypy packages services connectors` | 20 个源文件无问题 |
| Web | `pnpm typecheck`、`pnpm test:web` | 通过；Vitest 5 tests |
| 治理与差异 | `bash infra/ci/check-p0-governance.sh`、`git diff --check` | 通过 |
| 反枚举 API 矩阵 | 独立 FastAPI `TestClient` 脚本 | 通过 |
| 原始事实/健康一致性 | 独立 FastAPI `TestClient` 响应扫描 | 通过 |

## 验收结果

- Fixture 目录只含 `site`、`device`、`interface` 与底层兼容类型 `optic_module`；所有名称为演示 Fixture。详情与搜索只序列化资源公开摘要、关联资源、数据级别和健康摘要，没有把 `Observation`、`Event` 或健康证据引用放入资源身份。
- `resource_explorer.read`、`resource_search@1.0.0` 和 `resource_detail@1.0.0` 已登记。准确版本、filter allow-list、Workspace module allow-list、客户端 Scope 收窄和详情 `focus_resource_id` 均保持 ADR-0007 的失败关闭语义。
- 独立 API 矩阵比较了 operator 的未知详情与 site-b 越权详情：两者均为 `404/resource_not_available`。Chat 的两种“打开”请求以及 `resource_detail` ViewContext 的两种探测同样等价；响应不包含被隐藏资源名称。
- 对 `leaf-b01` 的越权 suggestions 与不存在名称 suggestions 都是同形的空数组；operator 对 `site-b` 与不存在站点的目录筛选都得到零项、零总数。无 query 的分页仅报告当前 Scope 可见目录的计数，未见 site-b 或 `optic-b-01`。
- 受控 Chat 路径返回服务端签发的 `resource_search` 或 `resource_detail` Context 与唯一注册模块；`site-a 有哪些光模块异常` 的 Context 固定为 site-a、`optic_module` 和既有健康状态筛选。现有 P2 光模块 Chat-to-Workspace 流程仍在全量回归内通过。
- P5G 资源响应扫描未发现 `latest_observation`、`observation_id`、`rx_dbm`、`tx_dbm`、`temperature_c`、`event_id`、`evidence_refs`、endpoint、credential、PromQL 或 raw observation 字段。`optic-a-02` 的 P5G 健康摘要与既有 `/v1/optic-health` Assessment 的 health、reason_codes 与 rule_version 一致。
- P6 来源失败关闭回归已包含于全量测试：资源能力 disabled 与缺少 production source 不回退到 Fixture。P5F 能力中心、Scope 投影、P5E `not_configured`、旧光模块 View/Chat 与 Web API 消歧测试均未回归。

## 证据边界与剩余项

本 Agent 没有启动或操作 Compose，也没有浏览器会话；因此不声称独立验证能力中心点击、实际 Chat/Workspace 页面渲染、移动端或 Compose 网络运行时。Project Lead 的隔离 Compose 与浏览器证据应在完成包中单独记录。

本次 API 反枚举验证覆盖默认 Fixture identities。未来新增资源类型、跨项目目录、真实标识、搜索历史、外部数据源或任何写操作，均须建立独立 Capability/ADR 并重做等价响应与数据边界验收。
