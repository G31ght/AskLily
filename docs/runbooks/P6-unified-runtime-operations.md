# P6 统一运行时运维手册

## 范围与前置条件

本手册仅适用于单机、隔离的 L0/L1 Fixture 验证。唯一的 `compose.yaml` 只发布 Web 的 loopback 端口；API 没有宿主端口。默认镜像内的 `deploy/runtime/sources.fixture.json` 是显式 Fixture 注册表，不含真实 endpoint 或凭据。

真实 Zabbix/Prometheus、客户网络、客户凭据、L4、SSO、HA、Kubernetes 和远程备份不在本手册范围。它们必须先满足 ADR-0003、ADR-0006 与独立 Capability 的批准。

## 启动、验证与停止

```bash
docker compose --env-file deploy/standalone/.env up --build --wait
curl --fail http://127.0.0.1:8080/health
docker compose down --remove-orphans
```

健康响应必须显示 `runtime.declared_environment=fixture`，且数据源为 `fixture`、`enabled=true`、`data_level=L0_L1`、`connection_state=ready`。不要把客户 endpoint、Token 或真实来源写进 `.env`；来源注册表与秘密注入是不同边界。

Compose 首先运行 `storage-init`，仅在命名卷中创建归属 API 用户的 `0700` 目录。`api` 和 `web` 均维持只读根文件系统。API 重启后须再次验证经 Web 代理的 `/health` 与 `/v1/session`，不能只验证容器自身 healthcheck。

## 数据源失败关闭

- Fixture 必须在注册表中显式启用；没有注册或被停用时，Optic Health 返回 `data_source_not_configured` 或 `data_source_disabled`。
- 标记为 `zabbix` 或 `prometheus` 的来源在 P6 中保持 `unverified`；请求返回 `data_source_unavailable`，绝不改用 Fixture。
- 管理控制面只显示安全状态和配置版本，不显示 endpoint、凭据或原始监控记录。

## SQLite 平台状态备份与恢复

`ops/standalone/backup.sh` 只备份非秘密部署材料，**不**含平台状态。账号、会话、对话历史、审计和能力开关需要停机后单独用受限 SQLite 备份工具处理；原始监控数据不得进入该文件。

1. 停止 Compose：`docker compose down --remove-orphans`。
2. 从命名卷取得数据库后，在受限本地目录运行 `python3 ops/runtime/backup_state.py /path/to/asklily-local.sqlite3 /safe/local/backup`。工具创建权限 `0600` 的一致性 SQLite 副本和 SHA-256；不要上传该文件、提交 Git 或放入共享目录。
3. 恢复前验证 SHA-256，停止 Compose，并以 API 用户 `10001:10001` 将经批准的备份替换到同一命名卷中的 `/var/lib/asklily/asklily-local.sqlite3`；权限为目录 `0700`、文件 `0600`。然后启动并验证 `/health`、`/v1/session`、管理员最小状态和数据源状态。
4. 迁移或恢复校验失败时保持服务停止，保留脱敏错误码和备份 checksum，按上一个已验收版本重建；不得删除未知状态、不得重新连接来源来“修复”数据。

## 隔离 Fixture 清理

验证使用临时 Compose 项目名和临时命名卷。记录启动、重启、health/session 结果后，执行 `docker compose -p <temporary-project> down --volumes --remove-orphans`。不得复用现有持久卷或清理不属于该项目的卷。
