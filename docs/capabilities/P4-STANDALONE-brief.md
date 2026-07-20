# P4 Standalone 硬化与运维基线

- GitHub Task: [#10](https://github.com/G31ght/AskLily/issues/10)
- 阶段：P4 Standalone 硬化
- 基线：`2cb9604bfbf2c768c5c2c19b1d6ddd476751e0ac`
- 目标 Profile：`standalone`

## 用户价值

私有化部署人员可使用可复现的 Docker Compose Profile 在单机本地运行 AskLily Fixture Demo，获得受限网络暴露、健康检查、非秘密部署备份、升级步骤、审计边界与容量限制说明。

## 范围

- `api` 与 `web` 两个容器的 Standalone Compose Profile；Web 仅绑定 `127.0.0.1`，API 只暴露给内部网络。
- 只读运行 Profile 标识、API 健康检查、Web 对 `/v1/` 和 `/health` 的内部反向代理。
- 只读的部署资产校验、非秘密无状态部署备份、显式升级命令、容器日志审计边界和容量基线文档。
- 本地静态回归与 GitHub Actions 的 Compose config、build、startup、health/Web smoke 验收。

## 非目标

- 不引入 Kubernetes、HA、数据库、持久化审计、真实 Zabbix、模型 Provider、外部部署或真实数据。
- 不将 Fixture Demo、P3 mock Connector 预备或此 Profile 说成真实 L4、Production 或 L6 容量验证。
- 不增加设备配置、工单、自动修复等业务写操作。

## 验收

- `docker compose --profile standalone config --quiet` 可解析；Profile 构建后 Web 与经代理的 `/health` 均可访问，health 返回 `profile=standalone`。
- Compose 具备 API health gate、内部网络、loopback host bind、non-root image、只读 root filesystem、最小 capability、`no-new-privileges` 与日志轮转。
- 备份包只包含 Git 追踪的非秘密部署材料，带提交元数据与 SHA-256；运行手册明确当前无持久化业务数据可备份。
- 文档披露审计为受限读取与容器轮转日志，容量基线仅为 Standalone 计划值；所有既有 Python/Web 回归保持通过。

## 风险

- P4 的无状态边界不提供持久化审计或灾备恢复；若要新增保留周期、数据库、日志汇聚或新数据类别，须先提交 ADR。
- 真实环境、真实 Connector、性能/并发数据仍未验证；这些分别属于延期 L4 与未来 L6/Production 里程碑。
