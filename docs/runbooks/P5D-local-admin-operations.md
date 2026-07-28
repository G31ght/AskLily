# P5D 本地后台管理操作

## 初始化管理员

仅在运行 AskLily 的本机终端执行：

```bash
PYTHONPATH=services/api/src:packages/contracts/src:packages/domain/src python -m asklily_api.admin_bootstrap
```

该命令只允许在尚无本地 `project-admin` 时成功，并通过终端密码输入创建管理员。不要将密码写入 shell 历史、环境变量、仓库、截图或日志。

## 访问后台

启动本地 API 与 Web 后访问 `/admin`。只有本地 `project-admin` 会话可读取后台；普通账号与未登录请求会被拒绝。

## 能力停用

后台只能停用注册且标记为可管理的业务 Capability。停用后服务端将拒绝该能力的查询和聊天执行；不会删除 Fixture、改变 Tool/View 契约，也不会影响严格只读边界。恢复后仅重新允许原有受 Scope 约束的路径。

## 审计与恢复

审计保存在本地 SQLite 的 `audit_events` 表，且不包含对话正文、密码或 Token。账号停用会立即撤销其会话；管理员可单独撤销账号会话。管理员密码丢失不提供仓库或默认后门恢复流程。

