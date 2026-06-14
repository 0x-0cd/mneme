<p align="center">
  <img src="https://img.shields.io/badge/version-0.1.0-blue.svg" alt="Version 0.1.0">
  <img src="https://img.shields.io/badge/python-3.11+-brightgreen.svg" alt="Python 3.11+">
  <img src="https://img.shields.io/badge/tests-90%20passing-green.svg" alt="90 tests passing">
  <img src="https://img.shields.io/badge/license-MIT-yellow.svg" alt="MIT License">
</p>

<h1 align="center">🧠 Mneme</h1>
<p align="center"><strong>Edge-first memory for AI agents.</strong><br>
<em>纯离线、即插即用的 AI Agent 记忆系统。</em></p>

<p align="center">
  <b>Mneme</b> /ˈniːmi/（尼米）— 以希腊记忆女神谟涅墨（Mneme）命名。
</p>

---

## 📖 总览

**Mneme** 是一个为 AI Agent 设计的轻量级记忆系统，**纯离线、即插即用**。它让任何 Agent 框架都能拥有持久的语义记忆——不需要 GPU，不需要云服务，甚至可以在树莓派上跑。

```bash
pip install mneme

# 启动记忆服务
mneme serve

# 记下一件事
mneme add "巴黎是法国的首都" --type fact --tags geography

# 语义检索
mneme search "法国首都在哪里"
```

### 🎯 核心差异化

| 特性 | Mneme | 传统方案 |
|:-----|:------|:---------|
| **端侧优先** | 纯离线运行，在线可选 | 多数依赖云端 API |
| **零 PyTorch 依赖** | ONNX Runtime 推理，占用 ~450MB | PyTorch 动辄 1GB+ |
| **即插即用** | HTTP API + MCP 协议，任意 Agent 框架即接即用 | 需要特定 SDK 集成 |
| **轻量部署** | 树莓派 4B (4GB) 流畅运行 | 通常需要服务器级硬件 |

---

## ✨ 功能特性

### 五类记忆类型

| 类型 | 说明 | 示例 |
|:----|:-----|:-----|
| `fact` | 客观事实 | "Python 3.11 于 2022 年发布" |
| `preference` | 偏好设定 | "用户喜欢简洁的回答风格" |
| `event` | 事件记录 | "2024-03-15 完成了项目架构评审" |
| `conversation` | 对话历史 | "用户上次询问了关于 RAG 的问题" |
| `skill` | 技能/能力 | "可以通过 FastAPI 创建 REST 接口" |

### 多渠道接入

```
┌─────────────────────────────────────────────┐
│              Mneme Memory Service            │
├──────────────┬──────────────┬────────────────┤
│  HTTP API    │  MCP Protocol│  CLI           │
│  :8989       │  (stdio/SSE) │  mneme <cmd>   │
│  8 routes    │  5 tools     │  6 commands    │
└──────────────┴──────────────┴────────────────┘
```

### 混合搜索

融合**语义搜索**（384 维向量嵌入）与 **BM25 关键词匹配**，支持按类型和标签过滤，权重可调，精准召回。

### 轻量版本控制

每条记忆自动记录 `created_at`、`updated_at`、`version`，支持软删除和数据追溯。

---

## 🚀 快速开始

### 安装

```bash
pip install mneme

# 或者从源码安装
git clone https://github.com/0x-0cd/mneme.git
cd mneme
pip install -e .
```

### 启动服务

```bash
# 一键启动 HTTP 服务（默认 :8989）
mneme serve

# 指定端口和数据库路径
mneme serve --port 8080 --db /path/to/memories.db
```

### CLI 命令行

```bash
# 存储记忆
mneme add "Paris is the capital of France" --type fact --tags geography,world

# 搜索记忆（语义 + 关键词混合）
mneme search "French capital"
mneme search "法国首都" --type fact

# 查看统计
mneme stats

# 删除单条
mneme delete <memory-id>

# 清空全部
mneme clear --force
```

### HTTP API 示例

```bash
# 创建记忆
curl -X POST http://localhost:8989/v1/memories \
  -H "Content-Type: application/json" \
  -d '{
    "content": "Paris is the capital of France",
    "type": "fact",
    "tags": ["geography"]
  }'

# 搜索记忆
curl "http://localhost:8989/v1/memories/search?q=French+capital&type=fact"

# 健康检查
curl http://localhost:8989/v1/health

# 系统统计
curl http://localhost:8989/v1/stats
```

### MCP Agent 集成

```python
# 任何支持 MCP 协议的 Agent 都可以无缝接入
from mcp import Client

client = Client("mneme")
client.call("store_memory", {
    "content": "Agent 的重要记忆",
    "type": "skill",
    "tags": ["agent", "core"]
})
```

可用 MCP 工具：

| Tool | 功能 |
|:-----|:-----|
| `store_memory` | 存储一条记忆 |
| `search_memory` | 搜索记忆 |
| `forget_memory` | 删除单条记忆 |
| `wipe_memories` | 清空所有记忆 |
| `memory_stats` | 获取系统统计 |

---

## 🏗️ 项目结构

```
mneme/
├── src/mneme/
│   ├── __about__.py         # 版本信息 (v0.1.0)
│   ├── cli.py               # Click CLI（6 个命令）
│   ├── server.py            # uvicorn 入口
│   ├── engine/
│   │   ├── types.py         # MemoryType 枚举 + Memory 数据模型
│   │   ├── store.py         # 存储引擎（嵌入 + 双存储协调）
│   │   └── search.py        # 混合搜索（语义 + BM25 + 类型过滤）
│   ├── storage/
│   │   ├── db.py            # SQLite CRUD（插入/查询/更新/软删除/清空）
│   │   └── vector.py        # sqlite-vec 向量索引（384 维，余弦相似度）
│   ├── api/
│   │   ├── app.py           # FastAPI 应用工厂
│   │   └── routes.py        # 8 个 REST 路由
│   ├── mcp/
│   │   └── server.py        # 5 个 MCP 工具
│   └── embed/
│       └── model.py         # ONNX Runtime 嵌入模型（无 PyTorch）
├── tests/                   # 90 个测试（TDD）
├── docs/                    # 设计文档、调研、架构图
│   ├── design-docs/         #   设计文档与架构图
│   ├── research/            #   调研、竞品分析、基准测试
│   ├── exec-plans/          #   执行计划
│   └── references/          #   参考文件
├── pyproject.toml           # 项目配置
├── AGENTS.md                # AI 编码助手行为准则
└── README.md                # 本文件
```

---

## 📊 项目数据

| 指标 | 数值 |
|:-----|:-----|
| Python 源码文件 | 18 个 |
| 代码行数 | ~980 行 |
| 测试数量 | 90 个（全部通过） |
| 开发方法 | TDD（RED → GREEN → REFACTOR） |
| 嵌入维度 | 384 |
| 运行时内存 | ~450 MB |
| 兼容平台 | 树莓派 4B 4GB ✅ |

---

## 🛠️ 技术栈

| 层 | 技术 |
|:---|:-----|
| **语言** | Python 3.11+ |
| **存储** | SQLite3 + sqlite-vec（向量扩展） |
| **嵌入** | ONNX Runtime（all-MiniLM-L6-v2, 384 维） |
| **HTTP** | FastAPI + uvicorn |
| **MCP** | MCP Python SDK |
| **CLI** | Click + rich |
| **测试** | pytest + pytest-asyncio |
| **质量** | ruff + mypy |

### 为什么是 ONNX Runtime？

大多数嵌入方案依赖 PyTorch，部署负担沉重。Mneme 使用 ONNX Runtime 推理，**完全没有 PyTorch 依赖**，从安装到运行都极为轻量。这是 Mneme 能在树莓派上流畅运行的关键。

---

## 🔬 架构设计

Mneme 采用**分层架构**，核心分为三层：

1. **传输层**（Transport）— HTTP API / MCP / CLI，多通道统一入口
2. **引擎层**（Engine）— Store（写入 + 向量化）与 Searcher（混合搜索）
3. **存储层**（Storage）— SQLite（结构化存储）+ sqlite-vec（向量索引）

存储一条记忆时，引擎自动完成：文本嵌入 → SQLite 持久化 → 向量索引写入。搜索时，引擎融合语义距离和关键词匹配，对结果去重排序。

> 详细设计文档见 [`docs/design-docs/v0.1-core-architecture.md`](docs/design-docs/v0.1-core-architecture.md)
>
> 架构图见 [`docs/design-docs/architecture.html`](docs/design-docs/architecture.html)（浏览器打开）

---

## 🧪 开发指南

### 环境准备

```bash
git clone https://github.com/0x-0cd/mneme.git
cd mneme
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 运行测试

```bash
pytest -v        # 90 个测试，全部通过
pytest --cov     # 带覆盖率报告
```

### 代码质量

```bash
ruff check src/  # Lint 检查
mypy src/        # 类型检查
```

### 提交规范

本项目采用 **[Conventional Commits v1.0.0](https://www.conventionalcommits.org/zh-hans/v1.0.0/)**：

```
feat(engine): 添加混合搜索权重参数
fix(api): 修复空查询时的 500 错误
docs: 更新 README 安装说明
test: 增加跨通道集成测试
```

| 类型 | 用途 |
|:----|:------|
| `feat` | 新功能 |
| `fix` | 修复 bug |
| `docs` | 文档 |
| `test` | 测试 |
| `refactor` | 重构 |
| `chore` | 构建/工具 |

---

## 📚 更多资料

- [设计文档 v0.1](docs/design-docs/v0.1-core-architecture.md) — 完整的设计决策
- [架构图](docs/design-docs/architecture.html) — 交互式架构图（浏览器打开）
- [竞品分析](docs/research/02-competitive-landscape.md) — 市场调研
- [基准测试](docs/research/05-benchmarks.md) — 性能数据
- [技术参考](docs/research/06-technical-references.md) — 外部资料索引

---

## 🔒 隐私与安全

- **纯离线运行**：所有数据存储在本地 SQLite，不依赖任何云端服务
- **零数据泄露**：没有遥测，没有匿名统计，不上传任何数据
- **无个人身份信息**：代码仓库不包含任何真实姓名、邮箱、地址等 PII

---

## 📄 许可证

[MIT License](LICENSE) © Mneme by Emma 🥰

---

<p align="center">
  <sub>以 Mneme 之名，为 AI Agent 赋予记忆。</sub>
</p>
