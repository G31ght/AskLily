# AskLily

AI 驱动运维平台。当前交付包含 P2 光模块健康 Fixture Demo、P3 Zabbix 只读 Connector 预备，以及 P4 无状态 Standalone Compose Profile。

项目的可追踪施工约束见 [工程基线](docs/architecture/engineering-baseline.md)。P4 已在 `21afa61` 关闭；P5 已在 `efd5dc1` 冻结，待 P6 统一运行时与数据源架构收敛后再继续。真实 Zabbix L4、Production/HA 与业务写操作均不在当前已验证范围内。下一任 Project Lead 的当前交接入口见 [P6 任务书](docs/governance/P6-unified-runtime-architecture-convergence-project-lead-task.md)。

## Standalone 快速开始

前置条件：Docker Engine / Docker Desktop，且仅在本机受控环境运行。P4 不连接真实 Zabbix、不需要 Token，也不包含业务写操作。

```bash
cp deploy/standalone/.env.example deploy/standalone/.env
docker compose --env-file deploy/standalone/.env --profile standalone up --build --wait
curl --fail http://127.0.0.1:8080/health
```

浏览器访问 `http://127.0.0.1:8080`。Web 仅绑定 loopback；API 不对宿主机开放，Web 通过内部网络反向代理 `/v1/` 与 `/health`。

关闭服务：

```bash
docker compose --env-file deploy/standalone/.env --profile standalone down --volumes --remove-orphans
```

部署、备份、升级、审计和容量限制见 [Standalone 运维手册](docs/runbooks/P4-standalone-operations.md)。真实 Connector、L4 和 Production/HA 均不在此 Profile 范围内。

## 本地后台管理（P5D）

管理控制面只通过前台本地 `project-admin` 账号的头像菜单进入。实际路径由未纳入仓库的本机 `VITE_ADMIN_PATH` 配置提供，且 API 仍强制校验 `project-admin` 身份；私有 URI 只是一层降低入口被发现概率的措施。它可查看注册能力、管理本地账号状态、持久化最小审计，并停用或恢复已注册的业务 Capability；不会开放真实数据、模型 Provider、写操作或任意契约配置。

初始化与运行边界见 [P5D 本地后台管理操作](docs/runbooks/P5D-local-admin-operations.md)。该持久化能力不改写 P4 无状态 Standalone 的验收结论。
