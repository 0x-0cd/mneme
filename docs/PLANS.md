# 开发路线图

## MVP（已完成）
- 记忆 CRUD ✅
- 语义搜索 + BM25 ✅
- HTTP API + MCP ✅
- CLI 基础命令 ✅
- 122 tests all green ✅

## V0.2a 矛盾检测（已完成 ✅）
- 反义词启发式检测 ✅
- 时间/同标签矛盾检测 ✅
- CLI + HTTP API + 13 tests ✅

## V0.2b（已完成 ✅）
- 睡眠计算 ✅
- 数据管理增强 ✅

## V0.3 插件系统 + 多用户（已完成 ✅）
- EventBus + PluginBase + PluginRegistry ✅
- 内置示例插件（LoggerPlugin, WebhookPlugin） ✅
- user_id 行级隔离 ✅
- API / CLI 多用户支持 ✅
- 33 新测试（20 plugin + 13 multi_user） ✅

## V1.0（未来路线）
- 插件 SDK / pip 安装式插件
- Web 管理控制台
- 跨设备同步
- **权重自适应校准** — 区间浮动 + 用户反馈闭环 | 设计完成 ✅ |
