# 记忆系统 Benchmark 标准

> 更新日期：2026-06-13

## 三大 Benchmark

### 1️⃣ LoCoMo（最主流）

**来源**：Snap Research + UNC Chapel Hill + USC，ACL 2024
**论文**：[Evaluating Very Long-Term Conversational Memory of LLM Agents](https://arxiv.org/abs/2402.17753)
**仓库**：[snap-research/locomo](https://github.com/snap-research/locomo)

**数据**：
- 10 组长对话，272 个 session
- 每段约 16,000 token
- 最多 35 个 session 跨度的对话

**题目（1,982 题）**：

| 题型 | 题数 | 考察能力 |
|:----|:---:|:--------|
| 单跳 (Single-hop) | 841 | 单一 session 内事实回顾 |
| 多跳 (Multi-hop) | 282 | 跨多个 session 串联信息 |
| 时间 (Temporal) | 321 | 事件顺序、变化感知 |
| 开放域 (Open Domain) | 92 | 推理和常识 |
| 对抗 (Adversarial) | 446 | 干扰题（正确回答是"没提过"）|

**基线**：
- GPT-4 zero-shot：32.1 F1
- 人类：87.9 F1

### 2️⃣ LongMemEval（更深）

- 长话题多主题对话
- 考察深度回忆和干扰抵抗
- 6 个类别，500 题

### 3️⃣ BEAM（最硬核）

- 考察记忆修正、实体干扰
- 两个子集：
  - BEAM 1M（700 题，35 段对话）
  - BEAM 10M（200 题，10 段对话）
- 当前最高分：64.1% / 48.6%（Mem0）

---

## 当前排行榜（LoCoMo）

| 排名 | 系统 | 总分 | 单跳 | 多跳 | 时间 | 开放域 | 架构 |
|:---:|:----|:---:|:---:|:---:|:---:|:-----:|:----|
| 🥇 | **ByteRover 2.0** | **92.2%** | 95.4% | 85.1% | 94.4% | 77.2% | Context Tree |
| 🥈 | Hindsight (Gemini-3) | 89.6% | 86.2% | 70.8% | 83.8% | 95.1% | LLM 即时回顾 |
| 🥉 | Memobase v0.0.37 | 75.8% | 70.9% | 46.9% | 85.1% | 77.2% | - |
| 4 | Zep | 75.1% | 74.1% | 66.0% | 79.8% | 67.7% | 知识图谱 |
| 5 | Mem0-Graph | 68.4% | 65.7% | 47.2% | 58.1% | 75.7% | 向量+图谱 |
| 6 | **Mem0** | 66.9% | 67.1% | 51.2% | 55.5% | 72.9% | 向量检索 |
| 7 | OpenAI Memory | 52.9% | 63.8% | 42.9% | 21.7% | 62.3% | 云端原生 |

### Mem0 新算法自报数据（非第三方验证）

| Benchmark | 得分 | Token 消耗 |
|:---------|:---:|:---------:|
| LoCoMo | 92.5% | 6,956 |
| LongMemEval | 94.4% | 6,787 |
| BEAM 1M | 64.1% | 6,719 |
| BEAM 10M | 48.6% | 6,914 |

> 注意：Mem0 博客自报的 92.5% LoCoMo 分数与 ByteRover 排行榜上 Mem0 的 66.9% 差异很大，可能是评估方法和版本不同导致。

---

## 我们的目标

### MVP 阶段
- ✅ LoCoMo ≥ **75%**（追上 Zep/Memobase，证明基础能力过关）
- ✅ LongMemEval ≥ **80%**
- 🚀 BEAM 争取 **≥ 50%**（大家在这块都不好，落后不丢人）

### V2 阶段
- 🎯 LoCoMo ≥ **90%**（进入第一梯队）
- 🎯 BEAM ≥ **60%**（当前无人能及，做成了就是独家优势）

---

## 关于 Benchmark 的认知

Mem0 博客说了句大实话：

> "Memory benchmarks for AI agents look simple on paper, yet they rarely predict real production behavior. Systems that pass academic tests often fail once prompts get messy, sessions get long, and users behave unpredictably."

所以 benchmark 是**及格线**，真正的较量在**实际使用体验**上。
