"""Tests for vector index layer."""

from __future__ import annotations

import pytest

from mneme.storage.vector import VectorIndex


@pytest.fixture
def idx():
    v = VectorIndex(":memory:")
    v.initialize()
    yield v
    v.close()


def _v(val: float) -> list[float]:
    """Helper: build a 384-dim vector with all values set to val."""
    return [val] * 384


class TestInitialize:
    def test_initialize_creates_virtual_table(self, idx):
        row = idx.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories_vec'"
        ).fetchone()
        assert row is not None
        assert row["name"] == "memories_vec"


class TestInsert:
    def test_insert_vector(self, idx):
        mid = "mem-1"
        idx.upsert(mid, _v(1.0))
        row = idx.cursor.execute("SELECT id FROM memories_vec WHERE id=?", (mid,)).fetchone()
        assert row is not None
        assert row["id"] == mid

    def test_insert_replaces_existing(self, idx):
        mid = "mem-1"
        idx.upsert(mid, _v(1.0))
        idx.upsert(mid, _v(2.0))
        rows = idx.cursor.execute("SELECT id FROM memories_vec WHERE id=?", (mid,)).fetchall()
        assert len(rows) == 1


class TestSearch:
    def test_search_returns_nearest(self, idx):
        idx.upsert("mem-a", _v(1.0))
        idx.upsert("mem-b", _v(0.9))
        idx.upsert("mem-c", _v(0.0))

        results = idx.search(_v(1.0), limit=3)
        assert len(results) == 3
        assert results[0][0] == "mem-a"
        assert results[0][1] == pytest.approx(0.0, abs=1e-3)
        assert results[1][0] == "mem-b"
        assert results[-1][0] == "mem-c"

    def test_search_limit(self, idx):
        for i in range(10):
            idx.upsert(f"mem-{i}", _v(float(i) / 10.0))
        results = idx.search(_v(0.5), limit=3)
        assert len(results) == 3

    def test_empty_index_returns_empty(self, idx):
        results = idx.search(_v(1.0))
        assert results == []


class TestDelete:
    def test_delete_vector(self, idx):
        idx.upsert("mem-1", _v(1.0))
        idx.delete("mem-1")
        row = idx.cursor.execute("SELECT id FROM memories_vec WHERE id=?", ("mem-1",)).fetchone()
        assert row is None


class TestCount:
    def test_count(self, idx):
        assert idx.count() == 0
        idx.upsert("mem-1", _v(1.0))
        idx.upsert("mem-2", _v(0.0))
        assert idx.count() == 2

    def test_count_after_delete(self, idx):
        idx.upsert("mem-1", _v(1.0))
        idx.delete("mem-1")
        assert idx.count() == 0
