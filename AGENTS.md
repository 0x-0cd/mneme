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

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **mneme** (1195 symbols, 1943 relationships, 50 execution flows). Use the GitNexus MCP tools to understand code, assess impact, and navigate safely.

> Index stale? Run `node .gitnexus/run.cjs analyze` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? `npx gitnexus analyze` (npm 11 crash → `npm i -g gitnexus`; #1939).

## Always Do

- **MUST run impact analysis before editing any symbol.** Before modifying a function, class, or method, run `impact({target: "symbolName", direction: "upstream"})` and report the blast radius (direct callers, affected processes, risk level) to the user.
- **MUST run `detect_changes()` before committing** to verify your changes only affect expected symbols and execution flows. For regression review, compare against the default branch: `detect_changes({scope: "compare", base_ref: "main"})`.
- **MUST warn the user** if impact analysis returns HIGH or CRITICAL risk before proceeding with edits.
- When exploring unfamiliar code, use `query({query: "concept"})` to find execution flows instead of grepping. It returns process-grouped results ranked by relevance.
- When you need full context on a specific symbol — callers, callees, which execution flows it participates in — use `context({name: "symbolName"})`.

## Never Do

- NEVER edit a function, class, or method without first running `impact` on it.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit changes without running `detect_changes()` to check affected scope.

## Resources

| Resource | Use for |
|----------|---------|
| `gitnexus://repo/mneme/context` | Codebase overview, check index freshness |
| `gitnexus://repo/mneme/clusters` | All functional areas |
| `gitnexus://repo/mneme/processes` | All execution flows |
| `gitnexus://repo/mneme/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
|------|---------------------|
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
