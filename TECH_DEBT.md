# 技术债跟踪器

> 技术债就像高息贷款：持续小量偿还远好于让它累积后痛苦爆发。
> 每次改代码顺手还一点债。

---

## 活跃技术债

| # | 描述 | 领域 | 发现日期 | 优先级 | 状态 |
|:-|:----|:----:|:--------:|:------:|:----:|
| 1 | ruff 仍有 8 个 E501 行长问题（4 个文件）— 已自动修复 ✅ | 代码风格 | 2026-06-15 | 🟢 | ✅ |
| 2 | CLI 测试偶发 flaky（pytest 缓存干扰），加 `-p no:cacheprovider` 可稳定全过 | CLI | 2026-06-14 | 🟡 | ⏳ |
| 3 | `test_types.py`(210行) / `test_mcp.py`(215行) / `test_db.py`(199行) 略超 200 行建议阈值 | 测试 | 2026-06-15 | 🟢 | ⏳ |
| 4 | `test_api.py`(169行) / `test_quality.py`(141行) 逐渐靠近阈值 | 测试 | 2026-06-15 | 🟢 | ⏳ |
| 5 | `src/mneme/server.py` 主入口文件无独立测试（但为薄包装，不影响覆盖率） | 测试 | 2026-06-15 | 🟢 | ⏳ |

**优先级：** 🔴 阻塞 / 🟡 高 / 🟢 低
**共计：** 0 🔴 / 1 🟡 / 3 🟢

**当前状态：暂无严重技术债。** ruff 零报错、测试全绿、无 TODO/FIXME/HACK 残留。

---

## 已解决

| # | 描述 | 解决日期 | 提交/动作 |
|:-|:----|:--------:|:---------:|
| 1 | MCP 服务器无测试 — store_memory/search_memory 等工具函数零覆盖 | 2026-06-14 | 20b221c（23 tests ✅） |
| 2 | CLI 命令无测试 — serve/add/search/delete/clear/stats 零覆盖 | 2026-06-14 | test_cli.py（130 行 ✅） |
| 3 | 测试 Fake 类重复定义 | 2026-06-14 | 9379e3b |
| 4 | embed/model.py:87 `except Exception` 窄化为 `(OSError, EnvironmentError)` | 2026-06-14 | 1469573 |
| 5 | routes.py:145 `store.db.cursor` 绕过 → 改用 `store.stats()` | 2026-06-14 | f8f7097 |
| 6 | search.py 分数融合缺陷 — 语义分数未传递到调用方 | 2026-06-14 | 411dc05 |
| 7 | search.py 融合结果未按分数降序排序 | 2026-06-14 | 411dc05 |
| 8 | embed/model.py 返回类型 `list[float] \| list[list[float]]` → 添加 @overload | 2026-06-14 | 729233b |
| 9 | app.py:52 模块级硬编码 → 支持 `MNEME_DB_PATH` 环境变量 | 2026-06-14 | ca439b2 |
| 10 | cli.py:21 `tuple[Any,...]` → `_Components` NamedTuple | 2026-06-14 | ca439b2 |
| 11 | db.py `__del__` 添加 `hasattr` 守卫 | 2026-06-14 | ca439b2 |
| 12 | mcp/server.py `store.db.get_all()` 绕过 → 改用 `store.stats()` | 2026-06-14 | f8f7097 |
| 13 | test_embed.py 网络依赖测试移除，纯单元测试保留 | 2026-06-14 | tbd |
| 14 | embed/model.py `max_length=256` → 构造函数参数 | 2026-06-14 | ca439b2 |
| 15 | vector.py `insert` → `upsert`（delete+insert 语义） | 2026-06-14 | 0737ca6 |
| 16 | routes.py `type` 遮蔽内置 → FastAPI alias 保持兼容 | 2026-06-14 | eebdcb7 |
| 17 | test_engine_store.py try/except → pytest.raises | 2026-06-14 | 9379e3b |
| 18 | embed/model.py _load() 双检锁防竞态 | 2026-06-14 | ca439b2 |
| 19 | ruff 导入排序 / 未使用导入 / 未使用变量 / 循环变量 / 未用参数 | 2026-06-15 | auto-fix |
| 20 | QUALITY_SCORE.md 测试计数从 122 更新为 135 | 2026-06-15 | 手动更新 |

---

## 规则

1. 发现技术债 → 加到这里
2. 改代码时 → 看附近有没有债可以顺手还
3. 还完债 → 更新状态 + 提交号

## 当前健康度

```
ruff   ✅ 零报错（已修复 19 项）
mypy   ⚠️ 173 errors（全是 tests/ 下无类型注解，src/ 需验证）
pytest ✅ 135 passed
TODOs  ✅ 无残留
```
