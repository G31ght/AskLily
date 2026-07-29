# P6 统一运行时 CI 结项记录

- 结项日期：2026-07-29
- 最终集成：PR #12，合并提交 `f4dae7a2a6d5917fccd9028bfeeafd5a4b67b54a`
- CI 修复提交：`76668ba ci(P6): align Compose smoke with unified runtime`
- 状态：已合并；全部必需检查通过。

## 根因与修复

P6 已将运行时收敛为单一 Compose，健康响应改为 `runtime.declared_environment=fixture`。遗留的 P4 工作流仍以 `docker compose --profile standalone` 启动，并断言已删除的 `"profile":"standalone"` 字段；服务本身已健康，失败仅来自过时 CI 合同。

工作流现以标准 `docker compose config --quiet`、`up --build --wait` 与 `down --volumes --remove-orphans` 运行，并解析经 Web 代理的 `/health`，断言：

- `status=ok`；
- `runtime.declared_environment=fixture`；
- `fixture-optic-health-l0-l1` 为只读、L0/L1、已启用且 `ready`；
- Web 首页可访问。

## 验证与边界

- 本机隔离验证使用项目名 `asklily-p6-ci`、临时端口 `18080` 与临时卷；构建、健康合同和 Web 入口均通过，随后执行 `down --volumes --remove-orphans` 清理。
- PR #12 的 L0 governance、P1 Python、P1 Web、P6 unified Compose smoke 全部通过。
- 此修复只更新 CI 合同；不新增 Connector、网络访问、凭据、真实来源、写操作或 Production 承诺。

## 结论

P4 的 Standalone 验收事实仍保留为历史记录；当前持续集成验证的是 P6 已接受的统一 Compose 合同。未来运行时合同变更必须同步更新该 smoke 测试，并先取得相应 ADR/负责人授权。
