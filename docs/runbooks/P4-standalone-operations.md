# P4 Standalone 运维手册

- 适用任务：[P4 #10](https://github.com/G31ght/AskLily/issues/10)
- Profile：`standalone`
- 数据边界：仅 P2 Fixture；不连接真实 Zabbix，不读取真实数据，不执行业务写操作。

## 部署与验证

1. 安装 Docker Engine / Docker Desktop；不要将 Docker socket 暴露给应用容器。
2. 复制 `deploy/standalone/.env.example` 为本地忽略的 `deploy/standalone/.env`。host bind 固定为 loopback，仅允许调整端口；不得在其中放入 Token、endpoint 或真实系统信息。
3. 执行 `docker compose --env-file deploy/standalone/.env --profile standalone up --build --wait`。
4. 执行 `curl --fail http://127.0.0.1:8080/health`，应返回 `status=ok`、`profile=standalone` 与 `data=fixture_l0_l1`。
5. 在本机浏览器访问 `http://127.0.0.1:8080`；API 不应有对宿主机的直接端口映射。

## 备份与恢复边界

当前 Profile 没有数据库、挂载卷或持久化审计数据，因此备份的是可恢复的**非秘密部署材料**，而不是用户数据。执行：

```bash
ops/standalone/backup.sh /safe/local/backup
```

脚本创建 tar.gz、SHA-256 和提交元数据，拒绝 `.env`、密钥、`secrets/` 与 credential-shaped 文件。恢复方式是校验 checksum、解压部署材料、从受控 Git 提交重建镜像，并由操作员重新提供本地忽略配置。若未来要保存审计或业务数据，先批准关于数据保留和备份的 ADR。

## 升级与回滚

升级前先创建上述部署备份，再执行：

```bash
ops/standalone/upgrade.sh
```

脚本先验证 Compose，再构建、等待健康检查并验证 loopback health。失败时执行 `docker compose --profile standalone down --volumes --remove-orphans`，检出上一个已验收 Git 提交并重新执行升级。因为本 Profile 无状态，回滚不迁移或删除业务数据。

## 审计与日志

- 应用 `/v1/audit` 仍受 auditor/project-admin 角色限制；该列表仅在进程内用于 Demo 证据，重启后清空。
- 容器标准输出使用 Docker `local` logging driver，并限制为每容器最多 5 个 10 MB 文件。日志不得写入 Token、真实 endpoint、主机名、item key 或原始指标。
- 需要长期审计、集中日志或保留期时停止在 P4 边界，建立 ADR 后再实施。

## 停止与异常处置

停止服务：`docker compose --profile standalone down --volumes --remove-orphans`。健康失败、配置泄露、非 loopback 暴露或出现写操作迹象时，立即停止 Profile、保留最小脱敏证据并提交风险报告；不要重试真实 Connector。
