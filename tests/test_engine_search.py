"""Tests for Searcher (hybrid search engine)."""

from __future__ import annotations

from mneme.engine.search import Searcher
from mneme.engine.types import Memory
from mneme.storage.db import Database
from tests.fakes import FakeEmbeddingModel, FakeVectorIndex


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
    vi.upsert(m1.id, emb.encode(m1.content))
    vi.upsert(m2.id, emb.encode(m2.content))
    vi.upsert(m3.id, emb.encode(m3.content))

    results = sr.search(query="apple", semantic_weight=0)
    assert len(results) == 2
    for m, _s in results:
        assert "apple" in m.content


def test_search_by_type() -> None:
    sr, db, vi, emb = make_searcher()
    m1 = Memory(content="fact one", type="fact")
    m2 = Memory(content="pref one", type="preference")
    m3 = Memory(content="fact two", type="fact")
    db.insert(m1)
    db.insert(m2)
    db.insert(m3)
    for m in (m1, m2, m3):
        vi.upsert(m.id, emb.encode(m.content))

    results = sr.search(type_filter="fact")
    assert len(results) == 2
    for m, _s in results:
        assert m.type.value == "fact"


def test_search_by_tags() -> None:
    sr, db, vi, emb = make_searcher()
    m1 = Memory(content="urgent task", tags=["urgent", "work"])
    m2 = Memory(content="fun task", tags=["fun"])
    m3 = Memory(content="work report", tags=["work"])
    db.insert(m1)
    db.insert(m2)
    db.insert(m3)
    for m in (m1, m2, m3):
        vi.upsert(m.id, emb.encode(m.content))

    results = sr.search(tags=["work"])
    assert len(results) == 2
    for m, _s in results:
        assert "work" in m.tags


def test_search_semantic() -> None:
    sr, db, vi, emb = make_searcher()
    m1 = Memory(content="python programming")
    m2 = Memory(content="java programming")
    db.insert(m1)
    db.insert(m2)
    vi.upsert(m1.id, emb.encode(m1.content))
    vi.upsert(m2.id, emb.encode(m2.content))

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
    vi.upsert(m1.id, emb.encode(m1.content))
    vi.upsert(m2.id, emb.encode(m2.content))
    vi.upsert(m3.id, emb.encode(m3.content))

    results = sr.search(query="apple", semantic_weight=0.5, limit=5)
    assert len(results) <= 3
    ids = {m.id for m, s in results}
    assert m1.id in ids
    assert m2.id in ids


def test_search_limit() -> None:
    sr, db, vi, emb = make_searcher()
    for i in range(10):
        m = Memory(content=f"item {i}")
        db.insert(m)
        vi.upsert(m.id, emb.encode(m.content))

    results = sr.search(query="item", semantic_weight=0, limit=3)
    assert len(results) == 3
