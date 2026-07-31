# P5F 能力中心与来源透明页独立验收报告

- 日期：2026-07-29
- 角色：独立 Test Agent（严格只读）
- 范围：注册式 View 契约、Catalog/API/Scope、泄露防护、既有光模块回归与静态 Web 验证
- 结论：**条件通过**。独立代码与接口验收无阻断缺陷；Compose 与实际浏览器由 Project Lead 另行完成，未计为本报告的独立复现证据。

## 独立执行证据

| 项目 | 命令或方法 | 结果 |
| --- | --- | --- |
| Python 回归 | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q -p no:cacheprovider` | 44 passed |
| Ruff | `.venv/bin/ruff check .` | 通过 |
| Mypy | `.venv/bin/mypy packages services connectors` | 19 个源文件无问题 |
| Web | `pnpm typecheck`、`pnpm test:web` | 通过；Vitest 3 tests |
| 治理与差异 | `bash infra/ci/check-p0-governance.sh`、`git diff --check` | 通过 |
| API smoke | TestClient 三条目录问句、operator/admin Scope 与非法 ViewContext | 通过 |

## 验收结论

- `ViewContract` 对所有既有 View 实施精确版本、filter 与 Workspace module allow-list；未知 View、错误版本、非法 filter/module 及 Scope 扩张均失败关闭。
- Catalog 只由 Capability Registry、P6 `RuntimeConfig` 和既有能力开关投影；默认 Fixture 中光模块为 `L0_L1/ready`，P5E 为 `not_configured/data_source_not_configured`，未验证 Zabbix 为 `unavailable/connector_not_validated` 和 `preflight_only`。
- `operator` 不获得仅 site-b 可见的能力，且默认来源仅投影 site-a；`project-admin` 获得本项目完整脱敏的 site-a/site-b 状态。
- 三条受控目录问句均返回 `response_kind=capability_catalog`、`capability_catalog@1.0.0` 与唯一的 `capability-catalog-overview`；目录回答不附带 `optic_health`。既有光模块 Chat/ViewContext/Fixture 回归通过。
- 响应扫描未发现 endpoint、token、credential、PromQL、label 或 `raw_observation`；没有真实 Connector、L4 或 Production 结论。

## 证据边界与非阻断风险

本 Agent 未操作 Compose，也没有可用浏览器连接；实际 Compose、普通入口、390px 与浏览器 Chat/Workspace 证据见 Project Lead 的 P5F 完成包，不能表述为独立 Test Agent 复现。

`/v1/views/context` 不接受客户端 Workspace module；module allow-list 由 Registry 单元/API 路径及服务端 `_server_presentation()` 验证。若未来开放客户端 module 输入，必须先扩展契约并增加 HTTP 级拒绝测试。
