"""Tests for Store engine."""

from __future__ import annotations

import pytest

from mneme.engine.store import Store
from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database

from tests.fakes import FakeVectorIndex, FakeEmbeddingModel


def make_store() -> tuple[Store, Database, FakeVectorIndex, FakeEmbeddingModel]:
    db = Database(":memory:")
    db.initialize()
    vindex = FakeVectorIndex()
    embed = FakeEmbeddingModel()
    return Store(db, vindex, embed), db, vindex, embed


class TestStoreMemory:
    def test_store_memory(self) -> None:
        store, _, _, _ = make_store()
        m = Memory(content="hello world", type=MemoryType.FACT)
        result = store.store(m)
        assert result is m
        retrieved = store.get(m.id)
        assert retrieved is not None
        assert retrieved.content == "hello world"
        assert retrieved.type == MemoryType.FACT

    def test_store_generates_embedding(self) -> None:
        store, _, vindex, embed = make_store()
        m = Memory(content="hello world")
        store.store(m)
        assert embed.encoded == ["hello world"]
        assert m.id in vindex.vectors

    def test_store_with_empty_content_fails(self) -> None:
        with pytest.raises(ValueError):
            Memory(content="")
        with pytest.raises(ValueError):
            Memory(content="   ")


class TestGetMemory:
    def test_get_memory(self) -> None:
        store, _, _, _ = make_store()
        m = Memory(content="hello")
        store.store(m)
        assert store.get(m.id) is not None
        assert store.get("nonexistent") is None


class TestDeleteMemory:
    def test_delete_memory(self) -> None:
        store, _, vindex, _ = make_store()
        m = Memory(content="hello")
        store.store(m)
        store.delete(m.id)
        assert store.get(m.id) is None
        assert m.id not in vindex.vectors


class TestClearAll:
    def test_clear_all(self) -> None:
        store, _, vindex, _ = make_store()
        store.store(Memory(content="a"))
        store.store(Memory(content="b"))
        assert store.count() == 2
        store.clear()
        assert store.count() == 0
        assert vindex.count() == 0
