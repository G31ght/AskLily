# ADR-0006：统一运行时与显式数据源状态

- 状态：Accepted
- 日期：2026-07-28
- 决定者与批准者：Project Lead 提案；项目负责人批准 P6 实施

## 问题

P5 冻结点同时留下 developer/standalone Profile、无状态 Compose 假设和本地 SQLite 持久化实现。它们让部署形态、数据真实性与前端显示相互混淆，也会在真实源不可用时诱发不透明的 Fixture 回退。

## 决定

- 产品只保留一份 Compose、API 镜像和 Web 镜像；不再以 Docker Profile 或前端开关选择运行形态。
- 部署持有只读数据源注册表。注册表声明 `fixture`、`test` 或 `production` 环境及某一来源的 `kind`、启用状态、只读性、能力映射、可见站点和配置版本；它不包含 endpoint、Token、密码或原始监控事实。
- Fixture 只有在注册表明确声明 `kind=fixture`、`enabled=true`、`declared_environment=fixture`、`data_level=L0_L1` 时才可执行。来源缺失、停用、未验证或真实 Connector 不可用时，服务端必须返回可审计的不可用错误；不得回退到 Fixture。
- 前端只读取并展示服务端返回的客户声明环境和脱敏状态，不能切换来源、推断环境或提交数据源配置。
- SQLite 是单机平台控制面：账号、会话、P5 对话历史、最小审计、能力开关、迁移版本及脱敏数据源状态可持久化。原始 Observation/Event、真实 endpoint、凭据、Token、主机名、item key、指标值和响应载荷不得写入 SQLite、备份清单、日志或前端状态。
- Compose 用专用的最小权限一次性初始化服务建立 `0700` 数据卷目录；API 根文件系统保持只读。Nginx 经 Docker 内部 DNS 动态解析 API，以支持 API 容器重启。

## 后果

- 旧 P4 Standalone Profile 是历史关闭证据，不能再作为当前产品运行时接口；P5 功能边界、账号/历史和控制面只做必要的 P6 适配。
- P3 的真实 Zabbix L4 仍被 ADR-0003 约束。本 ADR 不授权连接真实来源、真实数据、L4、SSO、HA、Kubernetes 或 Production 容量承诺。
- 客户若希望使用 Zabbix/Prometheus，须提供独立、受控的只读注册表和秘密注入，并按新的 Capability/ADR 与 ADR-0003 前置条件验收；P6 不实现该连接。
- 状态库恢复采用离线、受限 SQLite 备份；恢复失败停止服务并保留最小错误证据，不以删除未知数据伪造回滚。

## 验证与复审

P6 独立验收必须证明：无 Profile、唯一 Compose、显式 Fixture、真实/缺失来源失败关闭、状态库迁移与重启保持、Web 经代理的重启恢复、原始监控事实不落库，以及隔离 Fixture 项目的启动、重启和清理证据。首次启用真实来源或改变保留类别时，重新审批相关 ADR。
