# 技术债跟踪器

> 技术债就像高息贷款：持续小量偿还远好于让它累积后痛苦爆发。
> 每次改代码顺手还一点债。

---

## 活跃技术债

| # | 描述 | 领域 | 发现日期 | 优先级 | 状态 |
|:-|:----|:----:|:--------:|:------:|:----:|
| 1 | 测试 Fake 类重复定义 — FakeVectorIndex/FakeEmbeddingModel 在 4 个测试文件中重复，共 8 份重复代码 | 测试基础设施 | 2026-06-14 | 🔴 | ✅ |
| 2 | MCP 服务器无测试 — store_memory/search_memory 等 5 个工具函数零覆盖 | MCP | 2026-06-14 | 🔴 | ⏳ |
| 3 | CLI 命令无测试 — serve/add/search/delete/clear/stats 零覆盖 | CLI | 2026-06-14 | 🔴 | ⏳ |
| 4 | embed/model.py:87 `except Exception` 捕获所有异常，可能吞关键错误 | 嵌入 | 2026-06-14 | 🔴 | ⏳ |
| 5 | routes.py:145 直接访问 `store.db.cursor` 绕过 Store 抽象层 | API | 2026-06-14 | 🟡 | ⏳ |
| 6 | search.py:54-73 分数融合缺陷 — `semantic_weight` 参数形同虚设，关键词结果固定 0 分 | 搜索 | 2026-06-14 | 🟡 | ⏳ |
| 7 | search.py:74-75 融合结果未按分数降序排序 | 搜索 | 2026-06-14 | 🟡 | ⏳ |
| 8 | embed/model.py:108 返回类型 `list[float] \| list[list[float]]` 迫使调用方做 isinstance 检查 | 嵌入 | 2026-06-14 | 🟡 | ⏳ |
| 9 | app.py:52 模块级 `app = create_app()` 硬编码默认 db 路径 | API | 2026-06-14 | 🟡 | ⏳ |
| 10 | cli.py:21 返回类型 `tuple[Any, Any, Any, Any, Any]` 完全抹除类型信息 | CLI | 2026-06-14 | 🟡 | ⏳ |
| 11 | db.py:20-21 `__del__` 调用不可靠，`__init__` 失败时引发 AttributeError | 存储 | 2026-06-14 | 🟡 | ⏳ |
| 12 | mcp/server.py:66 直接调用 `store.db.get_all()` 绕过 Store 层 | MCP | 2026-06-14 | 🟡 | ⏳ |
| 13 | test_embed.py:27-41 集成测试混入单元测试文件，依赖网络下载模型 | 测试 | 2026-06-14 | 🟡 | ⏳ |
| 14 | embed/model.py:125 `max_length=256` 硬编码 | 嵌入 | 2026-06-14 | 🟢 | ⏳ |
| 15 | vector.py:44 insert 实为 upsert 语义，调用方未预期 | 存储 | 2026-06-14 | 🟢 | ⏳ |
| 16 | vector.py:52 distance 与 score 语义不统一 | 存储 | 2026-06-14 | 🟢 | ⏳ |
| 17 | test_api.py:229 / test_db.py:203 / test_types.py:210 文件略超 200 行建议阈值 | 测试 | 2026-06-14 | 🟢 | ⏳ |
| 18 | routes.py:54,65 `type` 遮蔽 Python 内置函数 | API | 2026-06-14 | 🟢 | ⏳ |
| 19 | test_engine_store.py:66-76 用 try/except 而非 pytest.raises | 测试 | 2026-06-14 | 🟢 | ⏳ |
| 20 | embed/model.py:55-57 Tokenizer 加载两阶段有竞态条件 | 嵌入 | 2026-06-14 | 🟢 | ⏳ |

**优先级：** 🔴 阻塞 / 🟡 高 / 🟢 低
**共计：** 4 🔴 / 9 🟡 / 7 🟢

### 立即行动的 3 件事

1. **抽取共享测试工具** — 将 FakeVectorIndex/FakeEmbeddingModel 提取到 `tests/conftest.py`，消除 4 文件重复
2. **修复 `except Exception:`** — `embed/model.py:87` 限定为具体异常类
3. **添加 MCP 和 CLI 测试** — 当前零覆盖

---

## 已解决

| # | 描述 | 解决日期 | PR |
|:-|:----|:--------:|:--:|
| 1 | 测试 Fake 类重复定义 — 提取到 tests/fakes.py，消除 4 文件 ~190 行重复 | 2026-06-14 | 9379e3b |
| 19 | test_engine_store.py try/except 风格 — 改为 pytest.raises | 2026-06-14 | 9379e3b |

---

## 规则

1. 发现技术债 → 加到这里
2. 改代码时 → 看附近有没有债可以顺手还
3. 还完债 → 更新状态 + PR 号
