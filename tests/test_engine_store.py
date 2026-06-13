"""Tests for Store engine."""

from __future__ import annotations

from mneme.engine.store import Store
from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database


class FakeVectorIndex:
    def __init__(self) -> None:
        self.vectors: dict[str, list[float]] = {}

    def insert(self, memory_id: str, embedding: list[float]) -> None:
        self.vectors[memory_id] = embedding

    def delete(self, memory_id: str) -> None:
        self.vectors.pop(memory_id, None)

    def clear(self) -> None:
        self.vectors.clear()

    def count(self) -> int:
        return len(self.vectors)


class FakeEmbeddingModel:
    def __init__(self) -> None:
        self.encoded: list[str] = []

    def encode(self, text: str | list[str]) -> list[float] | list[list[float]]:
        if isinstance(text, str):
            self.encoded.append(text)
            return [0.1] * 384
        for t in text:
            self.encoded.append(t)
        return [[0.1] * 384 for _ in text]


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
        try:
            Memory(content="")
            assert False, "expected ValueError"
        except ValueError:
            pass
        try:
            Memory(content="   ")
            assert False, "expected ValueError"
        except ValueError:
            pass


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
