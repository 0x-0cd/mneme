# AGENTS.md

本文件为 AI 编码助手（OpenCode / Codex 等）在 Mneme 项目中提供行为准则。

---

## 项目概述

**Mneme** — Edge-first memory for AI agents.
纯离线、即插即用的 AI Agent 记忆系统。

- 语言：Python 3.11+
- 架构：详见 `designs/architecture.html` 和 `designs/01-design-doc-v0.1.md`
- 存储：SQLite + sqlite-vec 向量扩展
- 协议：HTTP REST API (:8989) + MCP Protocol

## MVP 范围

### ✅ 做
- 记忆 CRUD（文本 + 类型 + 元数据 + 标签）
- 语义搜索（sqlite-vec）+ BM25 关键词 + 类型过滤
- 记忆类型：fact / preference / event / conversation / skill
- HTTP API + MCP 双通道
- CLI：`mneme serve` / `mneme add` / `mneme search`
- 轻量版本控制（created_at / updated_at / version / superseded_by）
- 数据管理：单条删除、全部清除（软删除）

### ❌ 不做（以后再说）
- 睡眠计算 / AI 做梦
- 矛盾检测 / 质量管理
- 全量版本控制（git 式）
- 插件系统
- 多用户 / Web 控制台
- 云同步

## 约束条件（两条红线）

### 1. 🔒 隐私红线（必须遵守）
GitHub 仓库中**禁止出现任何个人身份信息**：
- 真实姓名、昵称、性别
- 工作单位、公司名
- 邮箱地址
- 定位信息（城市、地址）
- 任何可追溯到个人的信息

允许的：项目作者署名（如 `Mneme by Emma`）、技术术语、公开的 GitHub 用户名。

### 2. 📝 约定式提交（必须遵守）
所有 git commit 遵循 [Conventional Commits v1.0.0](https://www.conventionalcommits.org/zh-hans/v1.0.0/)：

```
<类型>(<范围>): <描述>

[正文]

[脚注]
```

| 类型 | 用途 |
|:----|:------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 文档 |
| `style` | 代码格式 |
| `refactor` | 重构 |
| `perf` | 性能优化 |
| `test` | 测试 |
| `chore` | 构建/工具/初始化 |
| `ci` | CI 配置 |

破坏性变更：类型后加 `!`，或脚注写 `BREAKING CHANGE:`

## Karpathy 编码原则（必须遵守）

来源：Andrej Karpathy 对 LLM 编码陷阱的观察整理。

### 1. Think Before Coding（先想后写）
不要假设，不要隐藏困惑，不要跳过取舍分析。在写任何代码前：
- 明确自己的理解
- 指出不确定的地方
- 列出可能的方案及其取舍

### 2. Simplicity First（保持简单）
最少的代码解决当前问题，不加任何投机性抽象。
> **自测**：一个高级工程师会觉得这个实现过于复杂吗？如果会，简化。

核心逻辑 < 500 行，超过就拆模块。

### 3. Surgical Changes（精准修改）
只碰你该碰的代码，只清理自己引入的垃圾。
> **自测**：每一行改动的代码是否都能直接追溯到需求？

不要顺手格式化、重命名、或清理与你任务无关的代码。

### 4. Goal-Driven Execution（目标驱动执行）
不要把指令当待办清单，把指令转化成可验证的成功标准：

```
❌ "添加输入验证"
✅ "写一个测试覆盖无效输入，然后让它通过"
```

多步计划格式：
```
1. [步骤] → 验证: [检查点]
2. [步骤] → 验证: [检查点]
```

## 技术栈与依赖

- Python 3.11+（asyncio + uvloop）
- SQLite3 + sqlite-vec（向量存储）
- sentence-transformers（嵌入模型）
- FastAPI（HTTP 服务）
- MCP Python SDK（MCP 协议）
- rich（CLI 输出）
- pytest（测试）
- ruff（代码格式化 + lint）
- mypy（类型检查）

## 项目结构（规划中）

```
mneme/
├── src/mneme/
│   ├── __init__.py
│   ├── server.py        # HTTP + MCP 服务入口
│   ├── cli.py           # CLI 入口
│   ├── engine/          # 核心引擎
│   │   ├── store.py     # 存储模块
│   │   ├── search.py    # 搜索模块
│   │   └── types.py     # 记忆类型定义
│   ├── storage/         # 持久化层
│   │   ├── db.py        # SQLite 操作
│   │   └── vector.py    # 向量索引
│   ├── api/             # HTTP API
│   │   ├── routes.py    # 路由
│   │   └── models.py    # 请求/响应模型
│   ├── mcp/             # MCP 协议
│   │   └── server.py    # MCP 服务
│   └── embed/           # 嵌入
│       └── model.py     # 嵌入模型管理
├── tests/
├── designs/
├── research/
├── pyproject.toml
└── AGENTS.md
```

## 开发命令（规划中，随项目完善）

```bash
# 安装
pip install -e ".[dev]"

# 测试
pytest -v

# 代码检查
ruff check src/
mypy src/

# 运行
mneme serve
```
