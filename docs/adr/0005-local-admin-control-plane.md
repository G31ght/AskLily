# ADR-0005: 本地管理员控制面与能力停用边界

- 状态：Accepted
- 日期：2026-07-28
- 决定者与批准者：Project Lead 提案；项目负责人批准后台管理、持久化审计与能力停用

## 决定

AskLily 新增仅限本机、仅限本地 `project-admin` 身份使用的 `/admin` 管理控制面。

- 首位管理员必须通过本机交互式初始化命令创建；仓库、界面、环境变量和日志中不提供默认管理员凭据。
- 自助注册账号仍固定为 `operator` 与受限只读 Scope。管理员可以查看账号、停用/恢复非管理员账号并撤销其会话，但不能在后台扩大角色、项目或 Scope。
- 审计事件持久化到本地 SQLite，采用只追加的最小字段：操作者、动作、结果、请求标识、项目 Scope、能力/Tool 标识与原因码。不得保存密码、Token 或对话正文。
- 管理员可停用已注册的业务 Capability。停用是服务端强制的运行时拒绝，不删除注册表、不改写 Tool/View Contract、不修改 Fixture，也不允许任何写操作或真实 Connector。
- 平台基础 Capability 不可停用；它不是业务开关，停用会破坏平台自身的受控验证路径。
- 所有可编辑参数必须来自 Capability 注册的配置 Schema。未声明 Schema 的 Capability 只能展示来源、版本、限制和状态；不能以后台为由加入任意键值配置。

## 后果

- `/admin` 只显示真实的本地能力、账号与审计记录；没有时间序列证据时不制造趋势或调用量。
- 管理员控制面属于 P5 持久化 Profile，不改写 P4 无状态 Standalone 的关闭结论。
- 新 Capability、契约/Scope 变化、模型 Provider、真实数据和真实 Connector 仍须走独立 Capability Brief 与适用 ADR。

