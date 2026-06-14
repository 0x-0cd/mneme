"""Tests for MCP server tools."""

from __future__ import annotations

import pytest

from mneme.engine.search import Searcher
from mneme.engine.store import Store
from mneme.mcp.server import create_mcp_server
from mneme.storage.db import Database

from tests.fakes import FakeVectorIndex, FakeEmbeddingModel


@pytest.fixture
def mcp():
    db = Database(":memory:")
    db.initialize()
    vindex = FakeVectorIndex()
    embed = FakeEmbeddingModel()
    store = Store(db, vindex, embed)
    searcher = Searcher(db, vindex, embed)
    server = create_mcp_server(store, searcher)
    return server


def _tool_fn(mcp, name):
    return mcp._tool_manager.get_tool(name).fn


class TestStoreMemory:
    def test_store_memory(self, mcp):
        fn = _tool_fn(mcp, "store_memory")
        result = fn(content="hello world", type="fact")
        assert result["content"] == "hello world"
        assert result["type"] == "fact"
        assert "id" in result
        assert "created_at" in result

    def test_store_memory_default_type(self, mcp):
        fn = _tool_fn(mcp, "store_memory")
        result = fn(content="test")
        assert result["type"] == "fact"

    def test_store_memory_with_tags_and_weight(self, mcp):
        fn = _tool_fn(mcp, "store_memory")
        result = fn(content="important", type="event", tags=["urgent", "work"], weight=2.0)
        assert result["tags"] == ["urgent", "work"]
        assert result["weight"] == 2.0
        assert result["type"] == "event"

    def test_store_memory_empty_content_raises(self, mcp):
        fn = _tool_fn(mcp, "store_memory")
        with pytest.raises(ValueError):
            fn(content="")

    def test_store_memory_blank_content_raises(self, mcp):
        fn = _tool_fn(mcp, "store_memory")
        with pytest.raises(ValueError):
            fn(content="   ")


class TestSearchMemory:
    def test_search_no_results(self, mcp):
        fn = _tool_fn(mcp, "search_memory")
        result = fn(query="nothing")
        assert result == {"results": []}

    def test_search_with_query(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        search_fn = _tool_fn(mcp, "search_memory")
        store_fn(content="python programming")
        store_fn(content="java programming")
        result = search_fn(query="python")
        assert len(result["results"]) >= 1
        contents = [r["content"] for r in result["results"]]
        assert "python programming" in contents

    def test_search_by_type(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        search_fn = _tool_fn(mcp, "search_memory")
        store_fn(content="fact one", type="fact")
        store_fn(content="pref one", type="preference")
        result = search_fn(type="preference")
        assert len(result["results"]) == 1
        assert result["results"][0]["type"] == "preference"

    def test_search_by_tags(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        search_fn = _tool_fn(mcp, "search_memory")
        store_fn(content="urgent task", tags=["urgent", "work"])
        store_fn(content="fun task", tags=["fun"])
        result = search_fn(tags="work")
        assert len(result["results"]) == 1
        assert "work" in result["results"][0]["tags"]

    def test_search_limit(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        search_fn = _tool_fn(mcp, "search_memory")
        for i in range(10):
            store_fn(content=f"item {i}")
        result = search_fn(query="item", limit=3)
        assert len(result["results"]) == 3

    def test_search_empty_query_returns_all(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        search_fn = _tool_fn(mcp, "search_memory")
        store_fn(content="alpha")
        store_fn(content="beta")
        result = search_fn(query="")
        assert len(result["results"]) == 2

    def test_search_result_has_score(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        search_fn = _tool_fn(mcp, "search_memory")
        store_fn(content="unique search term")
        result = search_fn(query="unique")
        assert len(result["results"]) == 1
        assert "score" in result["results"][0]


class TestForgetMemory:
    def test_forget_memory(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        forget_fn = _tool_fn(mcp, "forget_memory")
        stored = store_fn(content="to delete")
        result = forget_fn(memory_id=stored["id"])
        assert result["status"] == "deleted"
        assert result["id"] == stored["id"]

    def test_forget_memory_removes_from_search(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        forget_fn = _tool_fn(mcp, "forget_memory")
        search_fn = _tool_fn(mcp, "search_memory")
        stored = store_fn(content="to delete")
        forget_fn(memory_id=stored["id"])
        result = search_fn(query="delete")
        assert len(result["results"]) == 0

    def test_forget_nonexistent_memory(self, mcp):
        fn = _tool_fn(mcp, "forget_memory")
        result = fn(memory_id="nonexistent-id")
        assert result["status"] == "deleted"


class TestWipeMemories:
    def test_wipe_without_confirm_cancelled(self, mcp):
        fn = _tool_fn(mcp, "wipe_memories")
        result = fn(confirm=False)
        assert result["status"] == "cancelled"

    def test_wipe_with_confirm_clears(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        wipe_fn = _tool_fn(mcp, "wipe_memories")
        store_fn(content="a")
        store_fn(content="b")
        result = wipe_fn(confirm=True)
        assert result["status"] == "cleared"

    def test_wipe_with_confirm_stats_show_zero(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        wipe_fn = _tool_fn(mcp, "wipe_memories")
        stats_fn = _tool_fn(mcp, "memory_stats")
        store_fn(content="a")
        store_fn(content="b")
        wipe_fn(confirm=True)
        stats = stats_fn()
        assert stats["total_memories"] == 0

    def test_wipe_on_empty_db(self, mcp):
        fn = _tool_fn(mcp, "wipe_memories")
        result = fn(confirm=True)
        assert result["status"] == "cleared"


class TestMemoryStats:
    def test_stats_empty(self, mcp):
        fn = _tool_fn(mcp, "memory_stats")
        result = fn()
        assert result["total_memories"] == 0
        assert result["by_type"] == {}
        assert result["vector_count"] == 0

    def test_stats_with_data(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        stats_fn = _tool_fn(mcp, "memory_stats")
        store_fn(content="fact one", type="fact")
        store_fn(content="pref one", type="preference")
        store_fn(content="fact two", type="fact")
        result = stats_fn()
        assert result["total_memories"] == 3
        assert result["by_type"]["fact"] == 2
        assert result["by_type"]["preference"] == 1
        assert result["vector_count"] == 3

    def test_stats_after_delete(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        forget_fn = _tool_fn(mcp, "forget_memory")
        stats_fn = _tool_fn(mcp, "memory_stats")
        stored = store_fn(content="fact one", type="fact")
        store_fn(content="pref one", type="preference")
        forget_fn(memory_id=stored["id"])
        result = stats_fn()
        assert result["total_memories"] == 1
        assert result["by_type"].get("fact") is None
        assert result["by_type"]["preference"] == 1

    def test_stats_vector_count_matches_total(self, mcp):
        store_fn = _tool_fn(mcp, "store_memory")
        stats_fn = _tool_fn(mcp, "memory_stats")
        store_fn(content="a")
        store_fn(content="b")
        store_fn(content="c")
        result = stats_fn()
        assert result["total_memories"] == 3
        assert result["vector_count"] == 3
