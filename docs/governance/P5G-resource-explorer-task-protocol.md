# P5G 资源检索与详情工作台任务协议

- Capability ID：`resource-explorer`
- 授权日期：2026-07-31
- 施工基线：`main` `2ca252688266e983955b5169587b040062fe8698`
- 适用决定：ADR-0003 至 ADR-0007，尤其是 [ADR-0007](../adr/0007-registered-versioned-view-contracts.md)。

## 冻结的公共契约

| 项目 | 值 |
| --- | --- |
| Tool | `resource_explorer.read@1.0.0`，只读 |
| Search View | `resource_search@1.0.0`；filters：`query`、`site_id`、`resource_type`、`health`、`page`；module：`resource-search-results` |
| Detail View | `resource_detail@1.0.0`；无 filters，以已验证的 `focus_resource_id` 定位；module：`resource-detail-overview` |
| API | `GET /v1/resources`、`GET /v1/resources/{resource_id}`、`GET /v1/resources/suggestions`；前端不得发送 Scope、View ID、module 或数据源参数 |
| 安全失败 | Scope 扩张、非法 filter、未登记版本/module 均失败关闭；未知与越权详情返回等价的 `resource_not_available`，不含资源名称 |

## 已批准范围

1. 仅建立 `site`、`device`、`interface` 与 `optic` 的 L0/L1 Fixture 目录；既有 `optic_module` 底层类型不迁移。
2. 搜索结果和详情由服务端 Scope、Capability 启停和显式 Fixture 来源共同收窄；无来源或不可用来源不得回退。
3. 详情的健康内容仅为已有光模块 `HealthAssessment` 引用摘要；不返回 Observation/Event 事实、指标值或新健康规则。
4. 使用受控 Chat 意图和能力中心预置入口进入 Workspace；P5H/P5I 未注册时显示“暂无已授权的后续调查入口”。

## 禁止范围

- 不修改 P1 `Resource`、`Scope`、`ViewContract` 语义或任何 SQLite schema；如必须改变，先停工并提交 ADR。
- 不加入真实 CMDB/Connector/网络/凭据/真实资源标识、导入同步、编辑删除、收藏/历史/笔记、拓扑、事件研判或影响分析。
- 不泄露 Scope 外名称、计数、建议、来源细节、原始监控事实或未来能力存在性。

## 验收和职责

- Agent A：领域 Fixture、Registry/API/Scope/Chat 与 Python 测试。
- Agent B：Web API、Workspace、空态/窄屏与实际浏览器验证。
- 独立 Test Agent：只读检查越权枚举、ViewContext、Chat/Workspace、回归并提交正式报告。
- Project Lead：本协议、公共契约、集成、P6 Compose、完成包与最终汇报。
