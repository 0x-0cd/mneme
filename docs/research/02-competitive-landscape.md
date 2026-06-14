# 竞争格局分析 — AI Agent 记忆系统

> 更新日期：2026-06-13

## 概览

| 产品 | ⭐ Stars | 定位 | 许可证 | 融资 |
|:----|:-------:|:----|:------|:----|
| **Mem0** | 58.4k | 即插即用记忆层 | Apache 2.0 | YC S24，$24M Series A |
| **Letta** (原 MemGPT) | ~21k | 完整 Agent 运行时 | Apache 2.0 | Felicis $10M seed |
| **Zep** | 小众 | 企业知识图谱 | Community | - |
| **Minta** | 新秀 | 记忆质量管理 | MIT | - |
| **ByteRover** | 4.2k | Context Tree 架构 | - | - |
| **MemPalace** | 新项目 | 存原文路线 | - | Milla Jovovich + Ben Sigman |

## 各系统深度分析

### Mem0（对标主赛道）

**特点：**
- `add()` / `search()` 极简 API，3 行代码接入
- 底层：向量数据库 + 可选手 + 知识图谱（Pro）
- 2026 年 4 月全新算法：单次 ADD-only 提取，永不覆盖
- 最新 benchmark：LoCoMo 92.5%，LongMemEval 94.4%，BEAM 1M 64.1%

**被吐槽的点：**
- ❌ 没有质量控制 — "会乐呵呵地返回 200 天前与现状矛盾的记忆"
- ❌ Cloud-first — 最佳功能需要 API key 和云服务
- ❌ 扁平记忆，没有结构化类型
- ❌ 没有离线/端侧模式

### Letta / MemGPT

**特点：**
- 虚拟上下文管理（Core/Recall/Archival 三级存储）
- Sleep-time Compute（2025.4 首发，WIRED 报道）
- Context Repositories（Git 式版本控制）
- 双 Agent 架构：主 Agent 对话 + 睡眠 Agent 后台整理

**被吐槽的点：**
- ❌ 架构锁定 — 接入 Letta 等于重写整个 Agent 栈
- ❌ 复杂 — 概念多（blocks/agents/virtual context）
- ❌ 每个记忆操作都消耗 LLM token

### Zep

**特点：**
- 知识图谱（Neo4j）+ 时间感知边缘
- 企业级：SOC 2，子 200ms 检索

**被吐槽的点：**
- ❌ 需要 Docker + Neo4j 部署，运维重
- ❌ 社区版功能受限

### Minta

**特点：**
- MIT 许可证最宽松
- 唯一做记忆质量管理的系统
  - 冲突检测 F1=0.81
  - 过期检测
  - 冗余压缩
  - 反驳学习
- 零 LLM 成本（无需调模型做质量控制）

**被吐槽的点：**
- ❌ 不够成熟，社区小
- ❌ 单人研究项目出身

### MemPalace（见 [comparison-mempalace.md](../design-docs/comparison-mempalace.md)）

### ByteRover 2.0

**特点：**
- Context Tree 架构
- LoCoMo 排行榜第一（92.2%）
- 超越了人类基线（87.9%）

## 差异化空间

1. **边缘优先** — 没有系统做纯粹的离线优先
2. **记忆质量** — Minta 在做但还不够成熟
3. **隐私分级**（云侧+端侧）— 你的专利覆盖区域，没有竞品在做
4. **轻量版本** — Letta 在做全量版，我们没有做轻量版
