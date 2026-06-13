# 技术参考资源

> 更新日期：2026-06-13

## 存储引擎

### SQLite + 向量扩展

| 项目 | 链接 | 说明 |
|:----|:----|:----|
| sqlite-vec | https://github.com/asg017/sqlite-vec | SQLite 向量检索扩展 |
| sqlite-vss | https://github.com/asg017/sqlite-vss | 另一个向量扩展（备选）|

**Benchmark 数据**（来源：[Ninad Pathak](https://ninadpathak.com/blog/local-wasm-vector-benchmarks/)）：

| 指标 | sqlite-vec（二值量化）| PGlite (HNSW) |
|:----|:------------------:|:-------------:|
| p99 延迟 (384d, 10万向量) | **4ms** | 12ms |
| p99 延迟 (3072d, 10万向量) | >100ms | <100ms |
| 内存 (10万向量) | **45MB** | 180MB |
| 包体大小 | **800KB** | 3.2MB |
| 召回率 (vs float32) | 92% (二值) / 99.8% (int8) | 100% |

## MCP 协议

- **官网**：https://modelcontextprotocol.io/
- **规范**：https://spec.modelcontextprotocol.io/
- **SDK**：Python / TypeScript / Java / Kotlin

MCP 是 AI Agent 工具的事实标准。我们如果原生提供 MCP 接口，等于直接接入了整个 MCP 生态。

## Obsidian 插件系统（参考设计）

- **插件 API 文档**：https://docs.obsidian.md/Plugins
- **设计模式**：核心做精做稳，扩展靠社区
- 关键钩子点：存储前预处理、检索后重排序、冲突检测规则

## AI Agent 记忆系统

### 项目 GitHub

| 项目 | Stars | 链接 |
|:----|:----:|:----|
| Mem0 | 58.4k | https://github.com/mem0ai/mem0 |
| Letta (MemGPT) | ~21k | https://github.com/letta-ai/letta |
| MemPalace | 新项目 | https://github.com/mempalace/mempalace（待确认）|
| ByteRover | 4.2k | https://github.com/campfirein/byterover-cli |
| Minta | 新秀 | https://github.com/xinchen03/minta |

### 论文

| 论文 | 链接 |
|:----|:----|
| LoCoMo (ACL 2024) | https://arxiv.org/abs/2402.17753 |
| MemGPT (Berkeley) | https://arxiv.org/abs/2310.08560 |
| Sleep-time Compute | https://arxiv.org/abs/2504.13171 |
| Building Production-Ready AI Agents with Scalable Long-Term Memory (Mem0) | 待查 |

### 文章

| 标题 | 链接 |
|:----|:----|
| Why I Put LLM Memory Back Inside the Context Window | https://medium.com/@keon.me/why-i-put-llm-memory-back-inside-the-context-window-080e86f6a691 |
| Best AI Agent Memory Frameworks 2026 | https://atlan.com/know/best-ai-agent-memory-frameworks-2026/ |
| Mem0 vs Letta vs Zep vs Minta (2026) | https://dev.to/xinchen03/mem0-vs-minta-vs-letta-vs-zep-ai-memory-systems-compared-2026-2k86 |
| Mem0 vs Letta: Memory Layer vs Agent Runtime | https://vectorize.io/articles/mem0-vs-letta |
| HuggingFace: Similarities Between Human Dreaming and LLM Learning | https://huggingface.co/blog/Kukedlc/dreaming-learning |
| Sleep-Time Compute and Memory Consolidation | https://jatinbansal.com/ai-engineering/sleep-time-compute/ |

## sqlite-vec 注意事项

- 对 384 维以下向量表现极佳（4ms p99）
- 3072 维高维向量性能下降明显（>100ms）
- 二值量化召回率约 92%（多数 RAG 场景足够）
- int8 量化召回率 99.8%（推荐生产使用）
- 无索引构建开销（对比 HNSW 的 45s 构建时间）
- 10 万向量以内的场景，综合性价比最高
