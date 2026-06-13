"""Tests for Searcher (hybrid search engine)."""

from __future__ import annotations

import hashlib
import math
import random

from mneme.engine.search import Searcher
from mneme.engine.types import Memory
from mneme.storage.db import Database


class FakeVectorIndex:
    def __init__(self) -> None:
        self.vectors: dict[str, list[float]] = {}

    def insert(self, memory_id: str, embedding: list[float]) -> None:
        self.vectors[memory_id] = embedding

    def search(
        self, query_vector: list[float], limit: int = 20
    ) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for mid, vec in self.vectors.items():
            dist = self._cosine_distance(query_vector, vec)
            scored.append((mid, dist))
        scored.sort(key=lambda x: x[1])
        return scored[:limit]

    @staticmethod
    def _cosine_distance(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 1.0
        return 1.0 - dot / (na * nb)

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
            return self._vec(text)
        for t in text:
            self.encoded.append(t)
        return [self._vec(t) for t in text]

    @staticmethod
    def _vec(text: str) -> list[float]:
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16)
        rng = random.Random(seed)
        return [rng.random() for _ in range(384)]


def make_searcher() -> tuple[Searcher, Database, FakeVectorIndex, FakeEmbeddingModel]:
    db = Database(":memory:")
    db.initialize()
    vindex = FakeVectorIndex()
    embed = FakeEmbeddingModel()
    return Searcher(db, vindex, embed), db, vindex, embed


def test_search_keyword() -> None:
    sr, db, vi, emb = make_searcher()
    m1 = Memory(content="apple pie recipe")
    m2 = Memory(content="banana smoothie")
    m3 = Memory(content="apple tart")
    db.insert(m1)
    db.insert(m2)
    db.insert(m3)
    vi.insert(m1.id, emb.encode(m1.content))
    vi.insert(m2.id, emb.encode(m2.content))
    vi.insert(m3.id, emb.encode(m3.content))

    results = sr.search(query="apple", semantic_weight=0)
    assert len(results) == 2
    assert all("apple" in r.content for r in results)


def test_search_by_type() -> None:
    sr, db, vi, emb = make_searcher()
    m1 = Memory(content="fact one", type="fact")
    m2 = Memory(content="pref one", type="preference")
    m3 = Memory(content="fact two", type="fact")
    db.insert(m1)
    db.insert(m2)
    db.insert(m3)
    for m in (m1, m2, m3):
        vi.insert(m.id, emb.encode(m.content))

    results = sr.search(type_filter="fact")
    assert len(results) == 2
    assert all(r.type.value == "fact" for r in results)


def test_search_by_tags() -> None:
    sr, db, vi, emb = make_searcher()
    m1 = Memory(content="urgent task", tags=["urgent", "work"])
    m2 = Memory(content="fun task", tags=["fun"])
    m3 = Memory(content="work report", tags=["work"])
    db.insert(m1)
    db.insert(m2)
    db.insert(m3)
    for m in (m1, m2, m3):
        vi.insert(m.id, emb.encode(m.content))

    results = sr.search(tags=["work"])
    assert len(results) == 2
    assert all("work" in r.tags for r in results)


def test_search_semantic() -> None:
    sr, db, vi, emb = make_searcher()
    m1 = Memory(content="python programming")
    m2 = Memory(content="java programming")
    db.insert(m1)
    db.insert(m2)
    vi.insert(m1.id, emb.encode(m1.content))
    vi.insert(m2.id, emb.encode(m2.content))

    zero = sr.search(query="python", semantic_weight=0)
    assert len(zero) == 1

    positive = sr.search(query="python", semantic_weight=0.5)
    assert len(positive) >= 1


def test_search_hybrid() -> None:
    sr, db, vi, emb = make_searcher()
    m1 = Memory(content="apple pie recipe")
    m2 = Memory(content="apple tart")
    m3 = Memory(content="banana bread")
    db.insert(m1)
    db.insert(m2)
    db.insert(m3)
    vi.insert(m1.id, emb.encode(m1.content))
    vi.insert(m2.id, emb.encode(m2.content))
    vi.insert(m3.id, emb.encode(m3.content))

    results = sr.search(query="apple", semantic_weight=0.5, limit=5)
    assert len(results) <= 3
    ids = {r.id for r in results}
    assert m1.id in ids
    assert m2.id in ids


def test_search_limit() -> None:
    sr, db, vi, emb = make_searcher()
    for i in range(10):
        m = Memory(content=f"item {i}")
        db.insert(m)
        vi.insert(m.id, emb.encode(m.content))

    results = sr.search(query="item", semantic_weight=0, limit=3)
    assert len(results) == 3
