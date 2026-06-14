# Sleep-time Compute（AI 梦境系统）

## 脑科学依据

记忆巩固的科学基础：

- **慢波睡眠 + REM 睡眠**期间，大脑**重放白天的神经序列**（Wilson & Lee, 2001）
- 老鼠在睡眠中会"跑迷宫"——白天迷宫活动的神经放电模式在梦中重现
- **梦到过特定任务的人，醒来后表现更好**（Wamsley et al., 2010）
- 睡眠功能：强化近期学习 + 整合新旧记忆 + 修剪不重要的信息

> "LLMs show more robust memory consolidation when patterns are repeated, comparable to the repetition and consolidation of experiences observed in dreams."
> — HuggingFace Blog, "The Similarities Between Human Dreaming and Learning in LLMs"

## 业界实现

### Letta Sleep-time Compute（2025.4）

**论文**：arXiv:2504.13171
**报道**：WIRED、Fast Company

**双 Agent 架构**：

| Agent | 角色 | 权限 |
|:-----|:----|:----|
| **主 Agent** | 与用户交互 | 读取记忆，**不能改写**核心记忆块 |
| **睡眠 Agent** | 后台整理 | 有**唯一写权限**，管理两个 Agent 的记忆块 |

**沟通方式**：仅通过共享记忆状态，不直接传消息。

**效果数据**：

| 指标 | 改善 |
|:----|:----:|
| 测试时计算量 | 降低 **5x** |
| 每次查询平均成本 | 降低 **2.5x** |
| Stateful AIME 准确率 | 提升 **18%** |

**最佳实践**：主 Agent 用快模型（如 GPT-4o-mini），睡眠 Agent 用大模型（Sonnet 3.7）。

### Claude Code Auto-dream

**触发条件**：24 小时活跃 + 至少 5 个新 session

**四阶段循环**：
1. 扫描记忆目录和 `MEMORY.md`
2. 搜索历史记录提取高价值模式（纠错、关键决策）
3. 合并新事实到持久记忆文件，删除矛盾
4. 裁剪索引到 200 行以内

**沙箱**：dream 循环中只能读写记忆文件，**不能接触源代码**。

**用户可见**：通过 `/dream` 命令手动触发，有节奏通知。

### 数据库类比

```
睡眠 = PostgreSQL 的 VACUUM + 物化视图刷新
  VACUUM → 清理过时/矛盾的记忆
  物化视图 → 预计算"用户可能问什么"的回答缓存
```

## 在我们的系统中的应用

系统空闲时自动运行：

1. 权重衰减计算（艾宾浩斯曲线）
2. 矛盾检测（"爱吃辣"vs"胃不好"）
3. 冷热记忆分层整理
4. 预计算常见查询的响应缓存

SQLite 单文件架构让睡眠整理只需一个后台线程，零运维成本。

## 参考资源

- Letta 官方博客：[Sleep-time Compute](https://www.letta.com/blog/sleep-time-compute)
- WIRED 报道：[Do Large Language Models Dream of AI Agents?](https://www.wired.com)
- arXiv 论文：[Sleep-time Compute: Beyond Inference Scaling at Test-time](https://arxiv.org/abs/2504.13171)
- Jatin Bansal 的分析：[Sleep-Time Compute and Memory Consolidation](https://jatinbansal.com/ai-engineering/sleep-time-compute/)
