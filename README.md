# AskLily

AI 驱动运维平台。当前交付包含 P2 光模块健康 Fixture Demo、P3 Zabbix 只读 Connector 预备，以及 P4 无状态 Standalone Compose Profile。

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
