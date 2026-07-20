# P3 Zabbix L4 只读验收运行手册

- 适用任务：[P3-003](https://github.com/G31ght/AskLily/issues/8)
- 前置 ADR：[ADR-0003](../adr/0003-zabbix-live-readonly-data-handling.md)
- 当前状态：仅完成 mock 演练；未获真实环境与本次执行授权，禁止发起网络连接。

## 执行前门禁

1. 确认 ADR-0003 仍为 Accepted，且实际 Zabbix 版本、认证方式和数据保留边界未发生变化。
2. 由项目负责人提供专用最小权限、只读 API Token，及最小 Host Group、时间窗、允许样本范围；Token、endpoint、主机名、item key 和原始指标均不得写入 Git、聊天、日志或报告。
3. 仅在本地忽略的 `connectors/zabbix/.env` 配置 endpoint 与 Token；提交前确认 `.env` 未被追踪。
4. 明确项目/站点 Scope 绑定与三个光模块字段的 item-key 映射；缺失、重复、空值或时间异常不得自动补造。
5. 运行 L4 预检。只有 ADR、本地配置、批准范围与本次执行授权均为真时才可继续；任何 blocker 均停止，不创建 transport、不访问网络。

## 获授权后的只读验收

1. 仅调用 `host.get`、`item.get`、`history.get`，并限制为获批 Host Group、样本和时间窗。
2. 将返回结果转换为既有 P2 Resource/Observation 输入，保留来源、观测时间与质量；服务端 Scope 过滤保持生效。
3. 输出仅含 request id、允许方法、资源计数、映射覆盖、缺失/重复计数、不可用项计数与错误类别的脱敏质量摘要。
4. 不写回 Zabbix，不持久化原始数据，不改变设备状态；发生权限、超时、映射或 Scope 异常立即停止。

## 收尾与报告

1. 撤销或安全保存本地 Token；不提交 `.env`，不附带原始响应。
2. 在 P3 阶段报告中记录执行时间、批准范围的抽象描述、预检结论、脱敏质量摘要与 L4 通过/阻塞状态。
3. 由独立 Test Agent 复核只读方法、Scope、质量摘要脱敏和无写操作证据；未完成真实运行时阶段仍为黄色，不能宣称 L4 通过。
