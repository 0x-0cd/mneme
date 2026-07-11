"""Tests for memory patch chain (version management) module."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from mneme.engine.patch import PatchTracker
from mneme.engine.types import Memory, MemoryPatch, MemoryType
from mneme.storage.db import Database


@pytest.fixture
def db() -> Database:
    d = Database(":memory:")
    d.initialize()
    yield d
    d.close()


@pytest.fixture
def tracker(db: Database) -> PatchTracker:
    return PatchTracker(db=db)


def _make_memory(content: str = "hello", **kwargs) -> Memory:
    return Memory(content=content, **kwargs)


class TestMemoryPatchModel:
    def test_to_dict_contains_all_fields(self) -> None:
        p = MemoryPatch(
            id="p1",
            memory_id="m1",
            version_from=1,
            version_to=2,
            content_before="old",
            content_after="new",
            type_before="fact",
            type_after="preference",
            tags_before="a,b",
            tags_after="a,c",
            rationale="corrected",
        )
        d = p.to_dict()
        assert d["id"] == "p1"
        assert d["memory_id"] == "m1"
        assert d["version_from"] == 1
        assert d["version_to"] == 2
        assert d["content_before"] == "old"
        assert d["content_after"] == "new"
        assert d["type_before"] == "fact"
        assert d["type_after"] == "preference"
        assert d["tags_before"] == "a,b"
        assert d["tags_after"] == "a,c"
        assert d["rationale"] == "corrected"
        assert "created_at" in d

    def test_from_dict_roundtrip(self) -> None:
        p = MemoryPatch(
            id="p1",
            memory_id="m1",
            version_from=1,
            version_to=2,
            content_before="old",
            content_after="new",
        )
        d = p.to_dict()
        p2 = MemoryPatch.from_dict(d)
        assert p2.id == p.id
        assert p2.memory_id == p.memory_id
        assert p2.version_from == p.version_from
        assert p2.version_to == p.version_to
        assert p2.content_before == p.content_before
        assert p2.content_after == p.content_after

    def test_from_dict_parses_iso_created_at(self) -> None:
        d = {
            "id": "p1",
            "memory_id": "m1",
            "version_from": 1,
            "version_to": 2,
            "content_before": "a",
            "content_after": "b",
            "created_at": "2026-07-12T10:00:00+00:00",
        }
        p = MemoryPatch.from_dict(d)
        assert isinstance(p.created_at, datetime)
        assert p.created_at == datetime(2026, 7, 12, 10, 0, 0, tzinfo=UTC)


class TestDatabasePatchesTable:
    def test_table_created_on_initialize(self, db: Database) -> None:
        row = db.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memory_patches'"
        ).fetchone()
        assert row is not None
        assert row["name"] == "memory_patches"

    def test_index_created_on_initialize(self, db: Database) -> None:
        rows = db.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND tbl_name='memory_patches'"
        ).fetchall()
        names = {r["name"] for r in rows}
        assert "idx_patches_memory_id" in names

    def test_insert_and_get_patch(self, db: Database) -> None:
        p = MemoryPatch(
            id="p1",
            memory_id="m1",
            version_from=1,
            version_to=2,
            content_before="old",
            content_after="new",
            type_before="fact",
            type_after="preference",
            tags_before="a",
            tags_after="a,b",
            rationale="fix",
        )
        db.insert_patch(p)
        patches = db.get_patches("m1")
        assert len(patches) == 1
        got = patches[0]
        assert got.id == "p1"
        assert got.memory_id == "m1"
        assert got.version_from == 1
        assert got.version_to == 2
        assert got.content_before == "old"
        assert got.content_after == "new"
        assert got.type_before == "fact"
        assert got.type_after == "preference"
        assert got.tags_before == "a"
        assert got.tags_after == "a,b"
        assert got.rationale == "fix"

    def test_get_patches_empty_for_unknown(self, db: Database) -> None:
        assert db.get_patches("nonexistent") == []

    def test_get_patches_chronological(self, db: Database) -> None:
        m = _make_memory()
        db.insert(m)
        # create three patches for same memory at different times
        for i in range(3):
            db.insert_patch(
                MemoryPatch(
                    id=f"p{i}",
                    memory_id=m.id,
                    version_from=i + 1,
                    version_to=i + 2,
                    content_before=f"v{i}",
                    content_after=f"v{i + 1}",
                    created_at=datetime(2026, 1, 1, 0, i, 0, tzinfo=UTC),
                )
            )
        patches = db.get_patches(m.id)
        assert [p.id for p in patches] == ["p0", "p1", "p2"]
        assert [p.version_from for p in patches] == [1, 2, 3]


class TestShouldPatch:
    def test_content_change_returns_true(self, tracker: PatchTracker) -> None:
        old = _make_memory(content="I like apples")
        new = _make_memory(content="I like bananas")
        assert tracker.should_patch(old, new) is True

    def test_type_change_returns_true(self, tracker: PatchTracker) -> None:
        old = _make_memory(content="x", type=MemoryType.FACT)
        new = _make_memory(content="x", type=MemoryType.PREFERENCE)
        assert tracker.should_patch(old, new) is True

    def test_tags_only_returns_false(self, tracker: PatchTracker) -> None:
        old = _make_memory(content="x", tags=["a"])
        new = _make_memory(content="x", tags=["a", "b"])
        assert tracker.should_patch(old, new) is False

    def test_weight_only_returns_false(self, tracker: PatchTracker) -> None:
        old = _make_memory(content="x", weight=1.0)
        new = _make_memory(content="x", weight=0.5)
        assert tracker.should_patch(old, new) is False

    def test_metadata_only_returns_false(self, tracker: PatchTracker) -> None:
        old = _make_memory(content="x", metadata={"a": 1})
        new = _make_memory(content="x", metadata={"b": 2})
        assert tracker.should_patch(old, new) is False

    def test_no_change_returns_false(self, tracker: PatchTracker) -> None:
        old = _make_memory(content="x")
        new = _make_memory(content="x")
        assert tracker.should_patch(old, new) is False

    def test_tags_and_content_change_returns_true(self, tracker: PatchTracker) -> None:
        old = _make_memory(content="apples", tags=["a"])
        new = _make_memory(content="bananas", tags=["a", "b"])
        assert tracker.should_patch(old, new) is True


class TestCreatePatch:
    def test_returns_patch_with_correct_versions(self, tracker: PatchTracker, db: Database) -> None:
        m = _make_memory(content="orig")
        db.insert(m)
        old = db.get(m.id)
        assert old is not None
        new = _make_memory(content="updated", id=m.id)
        patch = tracker.create_patch(old, new, rationale="correction")
        assert patch.version_from == old.version
        assert patch.version_to == old.version + 1
        assert patch.content_before == "orig"
        assert patch.content_after == "updated"
        assert patch.rationale == "correction"

    def test_persists_patch_to_db(self, tracker: PatchTracker, db: Database) -> None:
        m = _make_memory(content="orig")
        db.insert(m)
        old = db.get(m.id)
        assert old is not None
        new = _make_memory(content="updated", id=m.id)
        tracker.create_patch(old, new)
        assert tracker.get_patch_count(m.id) == 1

    def test_rationale_default_empty(self, tracker: PatchTracker, db: Database) -> None:
        m = _make_memory(content="orig")
        db.insert(m)
        old = db.get(m.id)
        assert old is not None
        new = _make_memory(content="updated", id=m.id)
        patch = tracker.create_patch(old, new)
        assert patch.rationale == ""

    def test_records_type_changes(self, tracker: PatchTracker, db: Database) -> None:
        m = _make_memory(content="x", type=MemoryType.FACT)
        db.insert(m)
        old = db.get(m.id)
        assert old is not None
        new = _make_memory(content="x", type=MemoryType.PREFERENCE, id=m.id)
        patch = tracker.create_patch(old, new)
        assert patch.type_before == "fact"
        assert patch.type_after == "preference"

    def test_records_tags_snapshot(self, tracker: PatchTracker, db: Database) -> None:
        m = _make_memory(content="x", tags=["a", "b"])
        db.insert(m)
        old = db.get(m.id)
        assert old is not None
        new = _make_memory(content="y", tags=["a", "b", "c"], id=m.id)
        patch = tracker.create_patch(old, new)
        assert patch.tags_before == "a,b"
        assert patch.tags_after == "a,b,c"


class TestGetPatches:
    def test_empty_for_unknown_memory(self, tracker: PatchTracker) -> None:
        assert tracker.get_patches("unknown") == []

    def test_returns_chronological_order(self, tracker: PatchTracker, db: Database) -> None:
        m = _make_memory(content="v1")
        db.insert(m)
        # Patch three times in sequence
        contents = ["v2", "v3", "v4"]
        for c in contents:
            old = db.get(m.id)
            assert old is not None
            new = _make_memory(content=c, id=m.id)
            tracker.create_patch(old, new)
            # Manually update the row to mimic db.update bumping version
            new.version = old.version
            db.update(new)
        patches = tracker.get_patches(m.id)
        assert len(patches) == 3
        assert [p.version_to for p in patches] == [2, 3, 4]
        assert [p.content_after for p in patches] == ["v2", "v3", "v4"]


class TestGetPatchCount:
    def test_zero_when_none(self, tracker: PatchTracker) -> None:
        assert tracker.get_patch_count("unknown") == 0

    def test_counts_per_memory(self, tracker: PatchTracker, db: Database) -> None:
        m = _make_memory(content="v1")
        db.insert(m)
        for c in ["v2", "v3"]:
            old = db.get(m.id)
            assert old is not None
            new = _make_memory(content=c, id=m.id)
            tracker.create_patch(old, new)
            new.version = old.version
            db.update(new)
        assert tracker.get_patch_count(m.id) == 2


class TestGetHistory:
    def test_no_patches_returns_current_only(self, tracker: PatchTracker, db: Database) -> None:
        m = _make_memory(content="hello")
        db.insert(m)
        history = tracker.get_history(m.id)
        assert len(history) == 1
        assert history[0]["version"] == 1
        assert history[0]["content"] == "hello"
        assert history[0]["source"] == "current"

    def test_patches_produce_history_entries(self, tracker: PatchTracker, db: Database) -> None:
        m = _make_memory(content="v1")
        db.insert(m)
        for c in ["v2", "v3"]:
            old = db.get(m.id)
            assert old is not None
            new = _make_memory(content=c, id=m.id)
            tracker.create_patch(old, new)
            new.version = old.version
            db.update(new)
        history = tracker.get_history(m.id)
        # Expect original snapshot + 2 patch snapshots = 3 entries
        assert len(history) == 3
        assert history[0]["version"] == 1
        assert history[0]["content"] == "v1"
        assert history[0]["source"] == "snapshot"
        assert history[1]["source"] == "patch"
        assert history[1]["version"] == 2
        assert history[1]["content"] == "v2"
        assert history[2]["source"] == "patch"
        assert history[2]["version"] == 3
        assert history[2]["content"] == "v3"

    def test_history_includes_current_after_incremental_updates(
        self, tracker: PatchTracker, db: Database
    ) -> None:
        m = _make_memory(content="v1")
        db.insert(m)
        # Non-incremental patch (content change)
        old = db.get(m.id)
        assert old is not None
        new = _make_memory(content="v2", id=m.id)
        tracker.create_patch(old, new)
        new.version = old.version
        db.update(new)
        # Incremental update (tags only — no patch)
        old = db.get(m.id)
        assert old is not None
        new2 = _make_memory(content="v2", tags=["extra"], id=m.id)
        db.update(new2)
        history = tracker.get_history(m.id)
        # snapshot + patch + current-after-incremental
        assert len(history) == 3
        assert history[-1]["source"] == "current"
        assert history[-1]["version"] == 3
        assert history[-1]["tags"] == ["extra"]

    def test_history_unknown_memory_empty(self, tracker: PatchTracker) -> None:
        assert tracker.get_history("unknown") == []


class TestStoreUpdateIntegration:
    """Integration tests for Store.update with patch tracking."""

    @pytest.fixture
    def store(self, db: Database):
        from mneme.engine.store import Store
        from tests.fakes import FakeEmbeddingModel, FakeVectorIndex

        vindex = FakeVectorIndex()
        embed = FakeEmbeddingModel()
        tracker = PatchTracker(db=db)
        return Store(db, vindex, embed, patch_tracker=tracker)

    def test_content_update_creates_patch(self, store, db: Database) -> None:
        m = _make_memory(content="original")
        store.store(m)
        m.content = "changed"
        store.update(m, rationale="corrected")
        patches = db.get_patches(m.id)
        assert len(patches) == 1
        assert patches[0].content_before == "original"
        assert patches[0].content_after == "changed"
        assert patches[0].rationale == "corrected"

    def test_tags_only_update_creates_no_patch(self, store, db: Database) -> None:
        m = _make_memory(content="x", tags=["a"])
        store.store(m)
        m.tags = ["a", "b"]
        store.update(m)
        assert db.get_patches(m.id) == []

    def test_update_without_tracker_works(self, db: Database) -> None:
        """Regression: Store works fine when patch_tracker is not provided."""
        from mneme.engine.store import Store
        from tests.fakes import FakeEmbeddingModel, FakeVectorIndex

        vindex = FakeVectorIndex()
        embed = FakeEmbeddingModel()
        store = Store(db, vindex, embed)
        m = _make_memory(content="orig")
        store.store(m)
        m.content = "new"
        store.update(m)
        assert store.get(m.id).content == "new"
        assert db.get_patches(m.id) == []


class TestPatchTrackerRealDb:
    def test_works_with_file_db(self, tmp_path: Path) -> None:
        path = str(tmp_path / "patches.db")
        db = Database(path)
        db.initialize()
        try:
            tracker = PatchTracker(db=db)
            m = _make_memory(content="orig")
            db.insert(m)
            old = db.get(m.id)
            assert old is not None
            new = _make_memory(content="updated", id=m.id)
            tracker.create_patch(old, new, rationale="fix")
            patches = tracker.get_patches(m.id)
            assert len(patches) == 1
            assert patches[0].rationale == "fix"
            assert tracker.get_patch_count(m.id) == 1
        finally:
            db.close()
