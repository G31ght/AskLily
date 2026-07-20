# P4 Standalone 独立验收记录

- 验收对象：`b14ed75c9c5feb766ee63682fc86a8362a5f87f9`
- 验收方式：独立工作树、只读检查；未连接网络、未安装 Docker、未创建或提交 PR。
- 复检结论：**通过（静态、回归与离线部署资产）**。此前的 host-bind 失败关闭阻塞项已修复。

## 已通过证据

| 检查 | 精确结果 |
| --- | --- |
| Python 回归 | `PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=packages/contracts/src:packages/domain/src:connectors/zabbix/src:services/api/src:services/agent/src /private/tmp/asklily-p1-integration/.venv/bin/python -m pytest`：22 passed in 0.28s。 |
| Python 静态检查 | `ruff check packages services connectors tests`：All checks passed；`mypy`：Success: no issues found in 15 source files。 |
| Web 验证 | `pnpm --filter @asklily/web typecheck`、`test`、`build` 均退出 0；Vitest 2/2 passed，Vite 生产构建完成。 |
| 离线部署资产 | `bash ops/standalone/verify-assets.sh`：`P4 standalone assets pass offline policy validation`。 |
| API 私有网络 | `compose.yaml` 的 `api` 仅有 `expose: 8000`，无 `ports:`；仅加入 `asklily_internal`，其网络声明 `internal: true`。 |
| 容器硬化静态证据 | 两个服务均声明 `read_only: true`、`no-new-privileges:true`、`cap_drop: ALL` 与 tmpfs；API Dockerfile 显式 `USER 10001:10001`。 |
| 备份与数据边界 | `tests/ops/test_standalone_assets.py::test_backup_creates_a_non_secret_stateless_deployment_bundle` 已通过；追踪文件扫描仅发现两个 `.env.example`，未发现私钥、证书或 `secrets/`。P4 文档明确仅为 Fixture、无真实数据和业务写操作。 |
| 容量表述 | `docs/architecture/P4-standalone-capacity-baseline.md` 明确说明其不是 L6 负载测试、性能承诺或 Production 容量结论。 |
| 复检安全修复 | `compose.yaml` 现固定 `127.0.0.1:${ASKLILY_HOST_PORT:-8080}:8080`，不再接受 `ASKLILY_HOST_BIND`；`verify-assets.sh` 与 `tests/ops/test_standalone_assets.py` 都会拒绝该变量回归。Web 接入 `asklily_edge` 以承载已发布的 loopback 端口，API 未接入该网络、仍仅接入 `asklily_internal`。 |

## 已关闭阻塞项：宿主监听地址失败关闭

初次验收时，`compose.yaml` 使用可覆盖的 `ASKLILY_HOST_BIND`，可能被设置为 `0.0.0.0`。复检时该定义已改为：

```yaml
- "127.0.0.1:${ASKLILY_HOST_PORT:-8080}:8080"
```

`.env.example` 与升级脚本也仅保留端口变量，`ops/standalone/verify-assets.sh` 明确在 Compose、示例配置或升级脚本重新出现 `ASKLILY_HOST_BIND` 时失败。因而操作者不能通过该部署配置将 Web 改为全接口发布；API 仍无宿主 `ports:`。

## 已知验证限制

本机没有 `docker` CLI，故未运行 `docker compose config`、镜像构建、启动、健康端点或浏览器 smoke；本记录没有把该限制误报为本地运行时通过。Web 最终镜像使用 `nginxinc/nginx-unprivileged`，但在无 Docker 环境下未对镜像实际 UID 做运行时确认；合并前仍应以 CI 的 Compose build/start/health/Web smoke 作运行时门禁。
