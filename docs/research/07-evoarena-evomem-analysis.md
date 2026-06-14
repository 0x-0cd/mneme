# EvoArena + EvoMem 论文分析

> **标题:** EvoArena: Tracking Memory Evolution for Robust LLM Agents in Dynamic Environments
> **来源:** arXiv:2606.13681 (2026-06-11)
> **分类:** cs.CL
> **链接:** https://arxiv.org/abs/2606.13681
> **代码:** 论文声称开源

---

## 一、核心问题

### 静态 vs 动态的鸿沟
> "大多数评测假设静态环境。但真实部署中环境持续演变——API 升级、代码库迁移、用户偏好变化。"

### State Collapse（状态坍塌）
现有记忆系统的致命缺陷：
- 记忆存成"最新单一状态"
- v2 的规则更新直接覆盖了 v1 仍有效的规则
- Agent 不知道"什么变了、什么还成立、当前版本该怎么行动"

---

## 二、EvoArena 基准

### 2.1 三大领域

| 领域 | 来源 | 规模 | 演变类型 |
|:----|:----|:----:|:----|
| **Terminal-Bench-Evo** | 可执行工作流链 | 89 链 → 441 实例 | CLI/路径/权限/策略 |
| **SWE-Chain-Evo** | 真实仓库的里程碑版本 | 50 链, 12 仓库, 493 实例 | API/逻辑/测试 |
| **PersonaMem-Evo** | 长程用户偏好交互 | 10 对话, 505 题, ~175K tokens | 偏好随时间演变 |

### 2.2 双指标

- **Step Accuracy** — 单版本任务是否解决
- **Chain Accuracy** — 整条演变链全部通过才算对（更难）

### 2.3 Terminal-Bench-Evo

**示例链（Figure 4）：** 推送 `hello.html` → 8080 端口服务
- Evo1: 通过 post-receive hook 部署（非手动拷贝）
- Evo2: 修复服务路径（nginx 不匹配）
- Evo3: 安全 web 根目录的组权限
- Evo4: 拒绝 `master` 推送，仅用 `main`

**演变类别分布：** I/O/协议约定 49.1%、工作区/模块/暂存流 13.4%、CLI/API 调用面 10.5%、依赖/工具链 8.0%、语义/策略/评估规则 4.6%

### 2.4 SWE-Chain-Evo

**示例链（Figure 5 — aiohttp）：**
- 里程碑1: 安全遗留 cookie 反序列化
- 里程碑2: 阻止 multipart header 注入
- 里程碑3: 保留空摘要挑战值
- 里程碑4: 动态 DST 修正时区格式

**统计：** 链长 5-15 步（均值 9.86），Go 81.9%、Python 18.1%
**跨步依赖：** 29.8% 的里程碑修改了之前步骤涉及的文件，14.2% 修改紧邻上一步

### 2.5 PersonaMem-Evo

**示例链（Figure 6）：** 咖啡偏好演变
> Coffee → 仅周一咖啡 → 平日茶 → 周末卡布奇诺

**问题类型（平衡设计）：**
- Single-Pattern Transfer（130 题）
- Multi-Pattern Synthesis（129 题）
- Temporal Trajectory Prediction（129 题）
- Conflict Resolution（117 题）

**难度：** Easy 120, Medium 186, Hard 199
**上下文长度：** 中位 597 条消息（174.7K tokens, 136K 词）
**Temporal 题需要 2-10 条来源偏好（中位 6）**

---

## 三、EvoMem 核心方法

### 3.1 补丁结构

```
p_t = <τ_t, C⁻_t, C⁺_t, r_t, z_t, e_t>
```

| 字段 | 含义 |
|:----|:-----|
| τ_t | 时间元数据（turn/session/时间戳） |
| C⁻_t | 更新前的记忆内容 |
| C⁺_t | 更新后的记忆内容 |
| r_t | 更新原因（rationale） |
| z_t | 语义摘要 |
| e_t | 支撑证据（触发上下文/执行反馈） |

### 3.2 什么时候打补丁？

- ✅ **非增量更新**（改写、覆盖、重新解释）→ 生成补丁
- ❌ 纯新增信息 → 直接加入基础记忆，不打补丁

### 3.3 检索策略

- 默认返回最新记忆 MT
- 如果查询涉及被覆盖/冲突的状态，额外检索相关补丁 Pq
- 最终上下文：`c(q) = Concat(c_mem, Pq)`

### 3.4 4 种 Agent 实现

| Agent | 领域 | 补丁策略 |
|:----|:----|:---------|
| **Terminus2** | Terminal | 链作用域终端记忆，记录策略切换示例。防止盲目复制旧工件 |
| **OpenHands** | SWE | 特征级补丁记录，语义+结构检索（文件路径、符号名）。防止回归 |
| **A-Mem** | 对话 | 图 diff 补丁，记录笔记节点和链接变化 |
| **Memento-Skill** | 工具/通用 | 版本化 TIP.md 文件族，BM25 检索任务特定技巧 |

---

## 四、实验结果

### 4.1 EvoArena 主结果

| 基准 | Base Step | +EvoMem Step | Δ | Base Chain | +EvoMem Chain | Δ |
|:----|:--------:|:----------:|:--:|:---------:|:------------:|:--:|
| Terminal-Bench-Evo | 43.6% | 46.0% | **+2.4%** | 21.5% | 27.6% | **+6.1%** |
| SWE-Chain-Evo | 27.9% | 28.3% | +0.4% | 10.0% | 12.1% | +2.1% |
| PersonaMem-Evo | 47.3% | 49.0% | +1.7% | 40.0% | 43.2% | +3.2% |

> **平均准确率 39.6%** — 当前 agent 在动态环境下表现很差

### 4.2 标准基准迁移

| 基准 | Base | +EvoMem | Δ |
|:----|:---:|:-------:|:-:|
| **GAIA** (Memento-S) | 65.8% | 72.3% | **+6.5%** |
| **LoCoMo** (A-Mem) | 39.7% | 43.0% | **+4.8%** |

### 4.3 关键发现

- Chain Accuracy 增益 > Step Accuracy 增益 → 补丁记忆在长程任务中优势更明显
- Terminal 域的 Chain Accuracy **+6.1%** 最高 — 因为终端策略变化需要清晰的版本追踪
- 效率方面：EvoMem 在所有 backbone 上**同时提升准确率和降低 token 消耗**
- 机制分析（Table 8）：EvoMem 提升了"证据捕获"（evidence capture），即更好地保留完整的演变环境状态

---

## 五、对 Mneme 的启发与对比

### 差异化定位

| 对比项 | EvoMem | Mneme |
|:------|:------|:------|
| 记忆分层 | 补丁链（最新 + 历史补丁） | 艾宾浩斯衰减（即时→短期→长期） |
| 更新策略 | 非增量更新才打补丁 | 暂未区分增量和改写 |
| 检索策略 | 默认取最新，需要时 +Pq | 向量搜索 + 标签过滤 |
| Agent 集成 | 4 种 agent 非侵入适配 | MnemeClient 适配器 |
| LoCoMo 分数 | **43.0%**（A-Mem + EvoMem） | 烟雾测试 100%（3/3），全量跑中 |
| 运行环境 | 云端大模型 | Edge-first, sqlite-vec 零依赖 |
| 时间复杂度 | 补丁链随更新增长 | 艾宾浩斯衰减自动清理 |

### 可以借鉴的点

1. **非增量更新的概念** — 区分"新增"和"改写"两种操作，改写生成 patch/版本记录
2. **检索时注入历史上下文** — 不只是搜最新状态，也可以捎带相关的历史变更
3. **Chain Accuracy 指标** — 我们也可以考虑把"连续多轮正确"作为一个评估维度
4. **EvoMem 在 LoCoMo 上只有 43.0%** — 我们的天花板还很高

### 我们的优势

- **LoCoMo 烟雾测试 100%（3/3）** 表明方向正确
- Edge-first + sqlite-vec 零外部依赖，部署成本远低于 EvoMem
- 艾宾浩斯遗忘曲线比补丁链更适合"遗忘"场景（EvoMem 不打补丁时旧信息就丢失了）

---

## 六、论文中的图

论文包含 8 张主要图片（已下载到本地）：

| 图号 | 内容 | 文件 |
|:---:|:----|:----|
| Figure 1 | Step accuracy vs chain accuracy 散点图 | x1.png |
| Figure 2 | EvoArena 构造流程 | x2.png |
| Figure 3 | 三大域的分布（饼图） | x3.png |
| Figure 4 | Terminal-Bench-Evo 示例（hello.html 版本链） | x4.png |
| Figure 5 | SWE-Chain-Evo 示例（aiohttp 里程碑链） | x5.png |
| Figure 6 | PersonaMem-Evo 示例（咖啡偏好演变） | x6.png |
| Figure 7 | EvoMem 架构概览 | x7.png |
| Figure 8 | 准确率 vs token 使用量 | x8.png |

图片路径：`/tmp/evoarena_figs/`

---

*分析日期: 2026-06-14*
*关联: [research index](index.md)*
