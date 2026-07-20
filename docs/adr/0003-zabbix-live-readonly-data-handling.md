# ADR-0003: Zabbix L4 只读数据处理与凭据边界

- 状态：Proposed
- 日期：2026-07-20
- 决定者与批准者：Project Lead 提案；项目负责人待批准
- 生效日期：未生效

## 问题

P3 需要验证真实 Zabbix Connector 兼容性，但当前仓库公开，且项目尚未提供专用只读环境。若直接将 endpoint、Token、资源标识或原始指标带入代码、日志或报告，将违反现有敏感信息边界，也无法保证 Connector 只读。

## 候选方案

1. 继续只使用 Fixture/mock：安全且可重复，但不能完成 L4 兼容性验收。
2. 使用普通运维账号或在仓库存放配置：实施快，但最小权限、审计和公开仓库风险不可接受。
3. 使用专用 HTTPS Zabbix 只读 API Token、本地忽略配置和最小样本范围：可获得 L4 证据，同时限制数据暴露与操作面。

## 决定

提议采纳方案 3，但在项目负责人批准前不发起任何真实网络连接。批准后：

- 凭据仅存在于本地忽略文件或受控运行环境；不得进入 Git、聊天、日志、测试 fixture 或报告。
- Connector 仅允许 `host.get`、`item.get`、`history.get`；其他 JSON-RPC 方法失败关闭。
- endpoint 必须为 HTTPS JSON-RPC；采集范围限制为负责人指定 Host Group/样本与时间窗。
- 报告只保留映射/质量摘要和可审计 request id，不保存原始指标、真实地址或资源名称。

## 影响

- 代码：新增可注入 transport 的只读 Connector 与显式字段映射；P2 Fixture 数据源保持独立。
- 数据：L4 运行只在本地内存处理获准最小范围的数据；不持久化、不出网、不写回 Zabbix。
- 测试：mock 覆盖白名单、认证、超时/错误、空值与质量；真实验收须单独记录执行时间、允许范围和质量摘要。
- 回滚：移除本地环境配置、撤销 Token、停止 Connector 运行即可；仓库无 live 数据需要清理。

## 验证与复审

在提供真实环境后，由 Project Lead 与独立 Test Agent 验证 API Token 权限、方法白名单、Scope 过滤、字段质量和无写操作，再将本 ADR 更新为 Accepted 或记录新的 ADR。若 endpoint、认证方式、数据类别或保留策略改变，必须重新审批。
