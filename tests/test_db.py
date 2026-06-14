"""Tests for SQLite storage layer."""

from __future__ import annotations

import pytest

from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database


@pytest.fixture
def db():
    d = Database(":memory:")
    d.initialize()
    yield d
    d.close()


class TestDatabaseInit:
    def test_initialize_creates_tables(self, db):
        row = db.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
        ).fetchone()
        assert row is not None
        assert row["name"] == "memories"

    def test_initialize_creates_indexes(self, db):
        rows = db.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='memories'"
        ).fetchall()
        names = {r["name"] for r in rows}
        assert "idx_memories_type" in names
        assert "idx_memories_deleted" in names


class TestInsert:
    def test_insert_memory(self, db):
        m = Memory(content="hello world")
        db.insert(m)
        row = db.cursor.execute("SELECT * FROM memories WHERE id=?", (m.id,)).fetchone()
        assert row is not None
        assert row["content"] == "hello world"
        assert row["type"] == "fact"
        assert row["version"] == 1
        assert row["deleted_at"] is None


class TestGet:
    def test_get_by_id(self, db):
        m = Memory(content="find me", tags=["test"], metadata={"key": "val"})
        db.insert(m)
        retrieved = db.get(m.id)
        assert retrieved is not None
        assert retrieved.content == "find me"
        assert retrieved.tags == ["test"]
        assert retrieved.metadata == {"key": "val"}
        assert retrieved.id == m.id

    def test_get_nonexistent_returns_none(self, db):
        assert db.get("nonexistent-id") is None

    def test_get_soft_deleted_returns_none(self, db):
        m = Memory(content="to delete")
        db.insert(m)
        db.soft_delete(m.id)
        assert db.get(m.id) is None


class TestSearch:
    def test_search_by_content(self, db):
        db.insert(Memory(content="apple pie recipe"))
        db.insert(Memory(content="banana smoothie"))
        db.insert(Memory(content="apple tart"))
        results = db.search(query="apple")
        assert len(results) == 2

    def test_search_by_type(self, db):
        db.insert(Memory(content="fact one", type="fact"))
        db.insert(Memory(content="pref one", type="preference"))
        db.insert(Memory(content="fact two", type="fact"))
        results = db.search(type_filter="fact")
        assert len(results) == 2
        for r in results:
            assert r.type == MemoryType.FACT

    def test_search_by_tags(self, db):
        db.insert(Memory(content="urgent task", tags=["urgent", "work"]))
        db.insert(Memory(content="fun task", tags=["fun"]))
        db.insert(Memory(content="work report", tags=["work"]))
        results = db.search(tags=["work"])
        assert len(results) == 2
        for r in results:
            assert "work" in r.tags

    def test_search_limit(self, db):
        for i in range(5):
            db.insert(Memory(content=f"item {i}"))
        results = db.search(limit=3)
        assert len(results) == 3

    def test_search_combined_filters(self, db):
        db.insert(Memory(content="apple work", type="fact", tags=["work"]))
        db.insert(Memory(content="apple fun", type="fact", tags=["fun"]))
        db.insert(Memory(content="banana work", type="fact", tags=["work"]))
        results = db.search(query="apple", type_filter="fact", tags=["work"])
        assert len(results) == 1
        assert results[0].content == "apple work"

    def test_search_excludes_soft_deleted(self, db):
        m = Memory(content="deleted item")
        db.insert(m)
        db.soft_delete(m.id)
        results = db.search(query="deleted")
        assert len(results) == 0


class TestUpdate:
    def test_update_memory(self, db):
        m = Memory(content="original", type="fact", tags=["old"])
        db.insert(m)
        original_updated = m.updated_at

        m.content = "updated"
        m.type = MemoryType.PREFERENCE
        m.tags = ["new"]
        m.metadata = {"changed": True}
        db.update(m)

        retrieved = db.get(m.id)
        assert retrieved is not None
        assert retrieved.content == "updated"
        assert retrieved.type == MemoryType.PREFERENCE
        assert retrieved.tags == ["new"]
        assert retrieved.metadata == {"changed": True}
        assert retrieved.version == 2
        assert retrieved.updated_at > original_updated


class TestSoftDelete:
    def test_soft_delete(self, db):
        m = Memory(content="will be deleted")
        db.insert(m)
        db.soft_delete(m.id)
        row = db.cursor.execute("SELECT deleted_at FROM memories WHERE id=?", (m.id,)).fetchone()
        assert row["deleted_at"] is not None

    def test_soft_delete_twice_idempotent(self, db):
        m = Memory(content="delete twice")
        db.insert(m)
        db.soft_delete(m.id)
        db.soft_delete(m.id)
        row = db.cursor.execute("SELECT deleted_at FROM memories WHERE id=?", (m.id,)).fetchone()
        assert row["deleted_at"] is not None


class TestClear:
    def test_clear_all(self, db):
        db.insert(Memory(content="a"))
        db.insert(Memory(content="b"))
        db.clear()
        rows = db.cursor.execute("SELECT * FROM memories").fetchall()
        assert len(rows) == 0


class TestCount:
    def test_count(self, db):
        assert db.count() == 0
        db.insert(Memory(content="a"))
        db.insert(Memory(content="b"))
        assert db.count() == 2

    def test_count_excludes_soft_deleted(self, db):
        db.insert(Memory(content="a"))
        m = Memory(content="b")
        db.insert(m)
        db.soft_delete(m.id)
        assert db.count() == 1


class TestGetAll:
    def test_get_all_memories(self, db):
        db.insert(Memory(content="a", tags=["x"]))
        db.insert(Memory(content="b", tags=["y"]))
        all_memories = db.get_all()
        assert len(all_memories) == 2
        contents = {m.content for m in all_memories}
        assert contents == {"a", "b"}

    def test_soft_deleted_excluded_from_get_all(self, db):
        m = Memory(content="delete me")
        db.insert(m)
        db.insert(Memory(content="keep me"))
        db.soft_delete(m.id)
        all_memories = db.get_all()
        assert len(all_memories) == 1
        assert all_memories[0].content == "keep me"

    def test_get_all_returns_empty_when_none(self, db):
        assert db.get_all() == []
