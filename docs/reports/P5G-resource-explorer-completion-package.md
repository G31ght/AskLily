# P5G 资源检索与详情工作台完成包

- 功能与状态：绿色（Fixture/L0-L1、严格只读）
- Capability：`resource-explorer`
- 实施分支：`codex/p5g-resource-explorer`
- 实施基线：`main` `2ca252688266e983955b5169587b040062fe8698`

## 本次实现

1. 新增稳定的演示 Fixture 目录，覆盖 `site`、`device`、`interface` 与既有兼容类型 `optic_module`；前台把最后一类明确显示为“光模块（optic）”。目录关系仅是受控导航元数据，不改动 P1 `Resource`、`Scope` 或 ViewContract 语义。
2. 新增只读 `resource_explorer.read@1.0.0`、`resource_search@1.0.0`、`resource_detail@1.0.0`，精确登记 filters/modules；`GET /v1/resources`、suggestions 和详情均经 Capability、P6 Fixture 来源和 Scope 收窄后执行。
3. 未知与 Scope 外详情统一 `404/resource_not_available`；范围外和不存在 suggestions 均为空；前端不提交 Scope、View、module、数据源或任意路由。
4. Chat 的受控“查/搜/检索/打开”意图、能力中心的预置入口和 Workspace 均使用服务端签发的 ViewContext。`site-a 有哪些光模块异常` 仅引用既有光模块 `HealthAssessment`，不重新计算或序列化 Observation/Event。
5. 资源详情展示 Fixture/L0-L1、最小公开摘要、所属/受控关联资源、健康摘要及限制；P5H/P5I 未注册时只显示通用安全不可用原因。

## 测试摘要

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| Python 全量 | 通过 | Project Lead：`53 passed` |
| Ruff / mypy | 通过 | `ruff`；mypy 20 files |
| Web | 通过 | `pnpm typecheck`；Vitest 5 tests |
| 治理与差异 | 通过 | P0 governance；`git diff --check` |
| 独立 Test Agent | 条件通过 | [正式报告](../../tests/reports/p5g-resource-explorer-independent-acceptance.md)；仅静态/TestClient，不含 Compose/浏览器 |
| P6 Compose | 通过 | Project Lead 以 `asklily-p5g-731` 临时项目、独立卷与 loopback `18087` 构建并 `up --wait`；`/health` 与资源 API 成功 |
| 实际浏览器 | 通过 | Project Lead：能力中心卡片和预置检索、operator Chat 到 `optic-a-02` 详情、site-a 异常筛选、越权 `leaf-b01` 通用空态、390px 入口与零 console error |

## 运行时证据边界

浏览器验证使用临时管理员查看注册能力后，销毁并重建同一临时 Compose 卷；随后用新建的 `site-a` 只读测试账号实际登录。operator 页面不显示 `site-b`，`打开 optic-a-02` 显示 `critical/rx_power_low` 的已有摘要且无原始事实；`查 leaf-b01` 仅回显用户输入并显示“没有可展示的匹配资源”，不确认资源存在。

独立 Test Agent 没有启动 Compose 或操作浏览器，其“条件通过”不得解读为第二次运行时复现。测试结束后 Lead 按 P6 规则清理临时容器、网络和卷。

## 风险与限制

- 全部名称、关系和结论均是 L0/L1 Fixture；没有真实 CMDB、Connector、L4、Production、资源写入或 SQLite 业务目录。
- 新资源类型、跨项目目录、真实资产标识、导入/同步、搜索历史、P5H/P5I 实体入口或任何写入都需独立 Capability/ADR，并重做 Scope/反枚举验收。
- 任何改变 P1 `Resource`、`Scope` 或已注册 View 语义的需求必须先走 ADR。

## 建议

接受 P5G 的 Fixture 资源检索与详情工作台；提交前保持 P0/P1/P5F/P6 回归和独立报告随变更一并评审。
