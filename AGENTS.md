# AGENTS.md — Mneme 项目行为准则

> 给 AI 编码助手的**地图**，不是说明书。
> 深层知识在 `docs/` 下渐进式披露。

---

## 🎯 项目概述

**Mneme** — Edge-first memory for AI agents.
纯离线、即插即用的 AI Agent 记忆系统。

- 语言：Python 3.11+
- 架构：详见 [docs/design-docs/v0.1-core-architecture.md](docs/design-docs/v0.1-core-architecture.md)
- 存储：SQLite + sqlite-vec
- 协议：HTTP REST API (:8989) + MCP

## 📂 知识库结构

```
AGENTS.md                ← 本文件（~100 行目录）
docs/
├── design-docs/         ← 设计文档、架构图、竞品对比
│   └── index.md         ← 设计文档索引
├── research/            ← 调研记录（脑暴/竞品/基准/参考）
│   └── index.md         ← 调研索引
├── exec-plans/          ← 执行计划（版本化一等公民）
│   ├── active/          ← 当前任务
│   └── completed/       ← 已完成
├── references/          ← LLM 参考（.txt）
├── PLANS.md             ← 开发路线图
└── QUALITY_SCORE.md     ← 各模块质量评分
```

## ✅ MVP 范围

| 做 | 不做 |
|:---|:-----|
| 记忆 CRUD + 类型 + 标签 | 睡眠计算（V2） |
| 语义搜索 + BM25 + 过滤 | 矛盾检测（V1.5） |
| HTTP API + MCP 双协议 | 全量版本控制（V2） |
| CLI（serve/add/search） | 插件系统（V2） |
| 单条/批量/软删除 | 多用户/Web 控制台/云同步 |

## 🚫 红线

- **隐私**：禁止任何 PII（真实姓名、性别、工作单位、邮箱、定位）。允许：作者署名、技术术语、公开 GitHub 用户名
- **提交**：必须遵循 [Conventional Commits](https://www.conventionalcommits.org/)：`<类型>(<范围>): <描述>`
  - 类型：feat / fix / docs / style / refactor / perf / test / chore / ci / build
  - 破坏性变更：类型后加 `!`

## 🧪 开发命令

```bash
pip install -e ".[dev]"
pytest -v
ruff check src/ && ruff format src/
mypy src/
mneme serve
```

## 💡 编码原则

1. **先想后写** — 明确理解再动手，不隐藏困惑
2. **保持简单** — 最少代码解决当前问题，不加投机性抽象
3. **精准修改** — 只碰该碰的代码，只清理自己的垃圾
4. **目标驱动** — 把指令转化为可验证的成功标准

---

> 此文件每季度由 doc-gardening agent 检查新鲜度。
