# P5D 本地后台管理控制面完成包

- 功能与状态：绿色（Fixture/本机持久化范围）
- Capability：P5D-LOCAL-ADMIN-CONTROL-PLANE
- 基线提交：`7240586`（P5A 紧凑工具栏统一）

## 本次实现

- 增加从前台管理员菜单进入的本地后台：概览、能力状态、账号状态/会话撤销、持久化审计和只读系统边界。
- 本机交互式命令或前台一次性初始化页创建首位 `project-admin`；没有默认管理员凭据，创建后 Web 初始化入口关闭。
- 前台不再提供自助注册；本地 `project-admin` 只能在后台创建固定只读的 `operator` 账号，并分配自身站点 Scope 的子集。
- `optic-health` 可被安全停用/恢复。服务端对聊天、查询、View 校验和 Tool 授权失败关闭；平台基础 Capability 受保护。
- 新增最小持久化审计，不包含密码、Token 或对话正文。

## 测试摘要

| 项目 | 结果 | 证据 |
| --- | --- | --- |
| 前端静态、单元与构建 | 通过 | `pnpm typecheck && pnpm test:web && pnpm --filter @asklily/web build` |
| Python API / 权限 / 回归 | 通过，27 tests | `PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest -q` |
| 代码质量 | 通过 | `ruff check`、`mypy`、`git diff --check` |
| 浏览器 E2E | 通过 | 隔离 Fixture 环境实测后台登录、概览、停用/恢复、账号停用与审计展示 |
| 真实数据 / Provider / Connector | 未测且不在范围 | P5D 只使用本机 Fixture/L0-L1 控制面数据 |

## 风险与限制

- 管理员密码丢失没有默认后门恢复；不得通过仓库、环境变量或日志保存凭据。
- 审计和账号数据只适用于单机本地 SQLite，不支持 SSO、同步、集中控制面或备份保留策略。
- 后台不允许扩大 Scope、编辑 Tool/View Contract、接入真实系统或解除严格只读边界。

## 建议

接受 P5D 的本机 Fixture 控制面交付；任何业务参数编辑需先为对应 Capability 注册版本化配置 Schema。
