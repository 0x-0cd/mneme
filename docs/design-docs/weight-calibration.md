# Mneme 权重自适应校准 — 设计文档

> 让记忆权重从一个静态固定值进化为一个**区间浮动 + 用户反馈闭环**的动态属性。
> 通过自然对话中的隐式反馈信号，系统持续自适应校准记入权重，让重要记忆天然更易被召回。

---

## 1. 动机

### 现状问题

当前 Mneme 的初始权重设计：

```python
weight: float = 1.0  # 统一默认值，调用方可覆盖
```

- 所有类型（fact/preference/event/...）共享同一个默认值
- 没有类型区分，没有内容感知
- 权重的精准度完全依赖调用方手动指定
- 系统无法从使用中学习

简言之：**weight 是一个被静态被动存储的属性，不是自我进化的参数。**

### 设计目标

1. **类型感知** — 不同类型的记忆天然重要性不同
2. **自适应** — 系统从用户反馈中学习，逐步校准
3. **抗漂移** — 单一极端反馈不会过度修正
4. **可解释** — 权重调整路径清晰可审计
5. **渐进** — 可增量落地，不破坏现有行为

---

## 2. 核心概念

### 2.1 权重区间

每个记忆类型有一个 `[base_min, base_max]` 区间，而非固定值：

```python
TYPE_WEIGHT_RANGES = {
    "preference":   [0.7, 1.0],  # 偏好类：偏高，用户喜好是核心记忆
    "event":        [0.5, 0.9],  # 事件类：中等偏上，有时效性但有价值
    "fact":         [0.3, 0.8],  # 事实类：范围宽，重要性取决于具体内容
    "conversation": [0.2, 0.6],  # 闲聊类：偏低，上下文性强
    "skill":        [0.6, 1.0],  # 技能类：偏高，学会的东西值得记住
}
```

### 2.2 校准偏差

每个 `(user_id, memory_type)` 对维护一个 `calibration_bias`，在区间内浮动：

```
effective_weight = midpoint + calibration_bias
          约束于 [base_min, base_max]
```

- `calibration_bias` 初始为 0
- 范围限幅在 `±0.2` 以内（防极端漂移）
- 持久化存储，跨会话持久

### 2.3 反馈信号

从用户自然对话中检测两类强反馈信号：

| 信号类型 | 触发语料示例 | 语义 |
|:---------|:-------------|:-----|
| **强正反馈** 👍 | "你居然还记得！"、"记性不错嘛"、"没错就是那个！"、"哈哈对！就是这个" | 确认当前校准合理 |
| **强负反馈** 👎 | "你怎么忘了！"、"我不是说过了吗"、"这都不记得"、"刚说过就忘了？" | 当前权重偏低，需要上调 |

---

## 3. 校准算法

### 3.1 核心公式

```
feedback_delta = 正反馈时: +0.01  (微调确认)
                 负反馈时: -0.05  (修正，幅度较大)

单次修正:
  raw_bias = current_bias + feedback_delta
  
正反馈抵消逻辑:
  若 raw_bias 与最近一次 feedback 方向相反:
    → 以当前 feedback 的 delta 的 30% 幅度"往回拉"
    → 防止负反馈过度修正

限幅:
  new_bias = clamp(raw_bias, -0.2, +0.2)
```

### 3.2 正反馈的"阻尼器"角色

正反馈**不主动驱动**校准偏差向上。它的作用是：

1. **确认信号** — 记录一次正反馈，表示当前校准是合理的
2. **抵消过调** — 如果之前发生过负反馈修正，正反馈会往回拉 30%
3. **衰减阻力** — 连续正反馈会降低负反馈的修正幅度

```
示例时序：
  t0: bias = 0.00
  t1: 负反馈 → delta = -0.05 → bias = -0.05  (用户说"你忘了")
  t2: 正反馈 → delta = +0.03 → bias = -0.02  (用户说"你还记得！" → 拉回 60%)
  t3: 负反馈 → delta = -0.05 → bias = -0.07  (又忘了一次)
  t4: 正反馈 → delta = +0.03 → bias = -0.04  (确认有效，拉回)
  t5: 正反馈 → delta = +0.01 → bias = -0.03  (连续确认，幅度降低)
```

### 3.3 反馈衰减（遗忘）

如果用户长期不反馈，`calibration_bias` 应缓慢向零回归：

```python
# 在睡眠计算（已有）中新增
def decay_calibrations(self):
    for key, bias in self._calibrations.items():
        # 每执行一次睡眠周期，bias 向零靠近 10%
        self._calibrations[key] *= 0.9
        if abs(self._calibrations[key]) < 0.001:
            del self._calibrations[key]  # 归零即清除
```

---

## 4. 融合到 Mneme 现有架构

```
┌─────────────────────────────────────────────────────┐
│                  记入流程                            │
│                                                     │
│  POST /v1/memories {content, type, user_id}         │
│       │                                             │
│       ▼                                             │
│  WeightCalibrator                                   │
│  ┌──────────────────────────────┐                   │
│  │ get_effective_weight(        │                   │
│  │   user_id, type              │                   │
│  │ ) → weight  ∈ [min, max]     │                   │
│  └──────────┬───────────────────┘                   │
│             │                                       │
│             ▼                                       │
│  Memory(weight=calculated_weight)                    │
│       │                                             │
│       ▼                                             │
│  Store.store(memory)  ← 已有逻辑，零改动            │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                  反馈流程                            │
│                                                     │
│  POST /v1/feedback {memory_id, signal, user_id}     │
│       │                                             │
│       ▼                                             │
│  WeightCalibrator                                   │
│  ┌──────────────────────────────┐                   │
│  │ apply_feedback(              │                   │
│  │   user_id, type, signal      │                   │
│  │ ) → 更新 calibration_bias    │                   │
│  └──────────────────────────────┘                   │
│       │                                             │
│       ▼                                             │
│  db.calibrations 持久化                              │
└─────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────┐
│                  消费流程（已有，融合点）              │
│                                                     │
│  睡眠计算: weight 参与遗忘决策 (已有)                │
│  搜索排序: weight 影响召回排序 (已有)                │
│  矛盾检测: weight 影响保留策略 (已有)                │
└─────────────────────────────────────────────────────┘
```

---

## 5. 存储设计

### 5.1 calibrations 表

```sql
CREATE TABLE IF NOT EXISTS weight_calibrations (
    user_id     TEXT NOT NULL,
    mem_type    TEXT NOT NULL,
    bias        REAL NOT NULL DEFAULT 0.0,
    pos_count   INTEGER NOT NULL DEFAULT 0,   -- 正反馈计数
    neg_count   INTEGER NOT NULL DEFAULT 0,   -- 负反馈计数
    last_pos_at TEXT,                          -- 上次正反馈时间
    last_neg_at TEXT,                          -- 上次负反馈时间
    updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (user_id, mem_type)
);
```

### 5.2 反馈日志表（可选，用于审计和调试）

```sql
CREATE TABLE IF NOT EXISTS feedback_log (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    memory_id   TEXT NOT NULL,
    user_id     TEXT NOT NULL,
    mem_type    TEXT NOT NULL,
    signal      TEXT NOT NULL CHECK(signal IN ('positive', 'negative')),
    weight_before REAL,
    weight_after  REAL,
    bias_before   REAL,
    bias_after    REAL,
    created_at  TEXT NOT NULL DEFAULT (datetime('now'))
);
```

---

## 6. 冷启动策略

| 场景 | 行为 |
|:-----|:-----|
| **新用户首次写入** | 从区间中点开始：`weight = (min + max) / 2` |
| **新用户首次反馈** | 正常触发校准，但 delta 幅度减半（保守） |
| **旧用户新类型** | 从区间中点开始，独立于其他类型的校准状态 |
| **累计反馈 < 3 条** | 校准偏差虽然生效，但标记为"低置信度" |

---

## 7. 实施计划

### Phase 1 — 区间定义 + 类型感知权重（半天）

- 新增 `mneme/engine/weight.py`：`WeightCalibrator` 类
- 定义 `TYPE_WEIGHT_RANGES`
- 创建 `weight_calibrations` 表
- 修改 `CreateMemoryRequest` 和 `store()` 流程，集成 `get_effective_weight()`
- 向后兼容：不传 user_id 时走原有逻辑（weight=1.0 或调用方指定的值）

### Phase 2 — 反馈信号 API + 校准逻辑（半天）

- `POST /v1/feedback` 端点
- 阻尼器校准算法实现
- 反馈日志表 + 日志记录
- 单元测试覆盖所有校准路径

### Phase 3 — 睡眠阶段衰减 + 集成测试（半天）

- 睡眠计算中集成 `decay_calibrations()`
- 全面集成测试
- 端到端验证：记入 → 反馈 → 校准 → 衰减 → 重校准

---

## 8. 开放问题

| 问题 | 当前思考 |
|:-----|:---------|
| **反馈信号检测在哪层？** | Mneme 本身不处理 NLU —— 建议客户端/使用方检测信号后调用 `POST /v1/feedback`。Mneme 只负责存储+校准 |
| **多个用户共享一个 memory？** | 目前 Mneme 是 user_id 隔离的，校准时自然按 `(user_id, type)` 隔离 |
| **bias 边界 ±0.2 是否合理？** | 初始值，可通过配置暴露给用户调。后续根据实际数据验证 |
| **连续负反馈的叠加效应？** | 建议每条负反馈独立触发，但 delta 不变。连续 3 条负反馈应告警而非继续下调 |

---

## 9. 参考

- [Mem0: Memory Eviction and Forgetting in AI Agents](https://mem0.ai/blog/memory-eviction-and-forgetting-in-ai-agents) — write-time LLM operation selection
- [DeltaMemory: How AI Agents Forget](https://www.deltamemory.com/blog/how-ai-agents-forget) — salience decay + access reinforcement
- [Adaptive Budgeted Forgetting Framework (arXiv:2604.02280)](https://arxiv.org/html/2604.02280v1) — multi-factor relevance scoring
- [Attanix: Building Agent Memory That Doesn't Suck](https://www.attanix.com/blog/building-agent-memory) — type-based priority weighting
