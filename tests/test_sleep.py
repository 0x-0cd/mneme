"""Tests for SleepEngine — memory consolidation, decay, and forgetting."""

from __future__ import annotations

import os
import tempfile
from datetime import UTC, datetime, timedelta

import httpx
import pytest
from click.testing import CliRunner
from httpx import ASGITransport

from mneme.api.app import create_app
from mneme.engine.search import Searcher
from mneme.engine.sleep import SleepEngine, SleepReport
from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database
from tests.fakes import FakeEmbeddingModel, FakeVectorIndex


def make_engine() -> tuple[SleepEngine, Database, FakeVectorIndex, FakeEmbeddingModel]:
    db = Database(":memory:")
    db.initialize()
    vindex = FakeVectorIndex()
    embed = FakeEmbeddingModel()
    searcher = Searcher(db, vindex, embed)
    engine = SleepEngine(db, vindex, embed, searcher)
    return engine, db, vindex, embed


def _store_memory(
    db: Database, vindex: FakeVectorIndex, embed: FakeEmbeddingModel, **kwargs
) -> Memory:
    m = Memory(**kwargs)
    db.insert(m)
    vec = embed.encode(m.content)
    vindex.upsert(m.id, vec)
    return m


class TestConsolidate:
    def test_consolidate_identical(self) -> None:
        engine, db, vindex, embed = make_engine()
        m1 = _store_memory(db, vindex, embed, content="hello world")
        m2 = _store_memory(db, vindex, embed, content="hello world")

        pairs = engine.consolidate()
        assert pairs == 1

        assert db.get(m1.id) is not None
        assert db.get(m2.id) is None

        survivor = db.get(m1.id)
        assert survivor is not None
        assert survivor.weight == 2.0
        assert survivor.tags == []
        assert survivor.superseded_by is None

    def test_consolidate_similar(self) -> None:
        engine, db, vindex, embed = make_engine()
        m1 = _store_memory(db, vindex, embed, content="hello world")
        m2 = _store_memory(db, vindex, embed, content="hello world!")

        pairs = engine.consolidate()
        assert pairs == 1
        assert db.get(m1.id) is not None
        assert db.get(m2.id) is None

    def test_consolidate_different(self) -> None:
        engine, db, vindex, embed = make_engine()
        m1 = _store_memory(db, vindex, embed, content="aaaaa")
        m2 = _store_memory(db, vindex, embed, content="zzzzz")

        pairs = engine.consolidate()
        assert pairs == 0
        assert db.get(m1.id) is not None
        assert db.get(m2.id) is not None

    def test_consolidate_different_types(self) -> None:
        engine, db, vindex, embed = make_engine()
        m1 = _store_memory(db, vindex, embed, content="hello world", type=MemoryType.FACT)
        m2 = _store_memory(db, vindex, embed, content="hello world", type=MemoryType.EVENT)

        pairs = engine.consolidate()
        assert pairs == 0
        assert db.get(m1.id) is not None
        assert db.get(m2.id) is not None

    def test_consolidate_merges_tags(self) -> None:
        engine, db, vindex, embed = make_engine()
        m1 = _store_memory(db, vindex, embed, content="hello world", tags=["a", "b"])
        _store_memory(db, vindex, embed, content="hello world", tags=["b", "c"])

        engine.consolidate()
        survivor = db.get(m1.id)
        assert survivor is not None
        assert set(survivor.tags) == {"a", "b", "c"}

    def test_consolidate_merges_metadata(self) -> None:
        engine, db, vindex, embed = make_engine()
        m1 = _store_memory(db, vindex, embed, content="hello world", metadata={"x": 1})
        _store_memory(db, vindex, embed, content="hello world", metadata={"y": 2})

        engine.consolidate()
        survivor = db.get(m1.id)
        assert survivor is not None
        assert survivor.metadata == {"x": 1, "y": 2}

    def test_consolidate_keeps_longer_content(self) -> None:
        engine, db, vindex, embed = make_engine()
        m1 = _store_memory(db, vindex, embed, content="hello world")
        m2 = _store_memory(db, vindex, embed, content="hello world")
        # Override m2 content to be longer — embedding was stored with
        # identical content, so similarity=1.0, but actual content differs
        m2.content = "hello world with extra details"
        db.update(m2)

        engine.consolidate()
        survivor = db.get(m1.id)
        assert survivor is not None
        assert survivor.content == "hello world with extra details"

    def test_consolidate_keeps_older(self) -> None:
        engine, db, vindex, embed = make_engine()
        older_time = datetime(2025, 1, 1, tzinfo=UTC)
        newer_time = datetime(2025, 6, 1, tzinfo=UTC)
        m1 = _store_memory(db, vindex, embed, content="hello world", created_at=older_time)
        m2 = _store_memory(db, vindex, embed, content="hello world", created_at=newer_time)

        engine.consolidate()
        assert db.get(m1.id) is not None
        assert db.get(m2.id) is None

    def test_consolidate_empty_db(self) -> None:
        engine, db, vindex, embed = make_engine()
        pairs = engine.consolidate()
        assert pairs == 0

    def test_consolidate_single_memory(self) -> None:
        engine, db, vindex, embed = make_engine()
        _store_memory(db, vindex, embed, content="hello world")
        pairs = engine.consolidate()
        assert pairs == 0

    def test_consolidate_dry_run(self) -> None:
        engine, db, vindex, embed = make_engine()
        m1 = _store_memory(db, vindex, embed, content="hello world")
        m2 = _store_memory(db, vindex, embed, content="hello world")

        pairs = engine.consolidate(dry_run=True)
        assert pairs == 1

        assert db.get(m1.id) is not None
        assert db.get(m2.id) is not None
        assert db.get(m2.id).superseded_by is None  # type: ignore[union-attr]

    def test_consolidate_with_superseded_by_set(self) -> None:
        engine, db, vindex, embed = make_engine()
        m1 = _store_memory(db, vindex, embed, content="hello world")
        m2 = _store_memory(db, vindex, embed, content="hello world")

        engine.consolidate()
        deleted = db.cursor.execute(
            "SELECT superseded_by FROM memories WHERE id = ?", (m2.id,)
        ).fetchone()
        assert deleted is not None
        assert deleted["superseded_by"] == m1.id


class TestDecay:
    def test_decay_old_memory(self) -> None:
        engine, db, vindex, embed = make_engine()
        old_time = datetime.now(UTC) - timedelta(days=30)
        _store_memory(db, vindex, embed, content="old memory", updated_at=old_time, weight=1.0)

        decayed, forgotten = engine.decay(halflife_days=30, forget_threshold=0.05)
        assert decayed == 1
        assert forgotten == 0

        memory = db.get_all()[0]
        assert memory.weight < 1.0
        assert memory.weight > 0.05

    def test_decay_below_threshold(self) -> None:
        engine, db, vindex, embed = make_engine()
        old_time = datetime(2020, 1, 1, tzinfo=UTC)
        _store_memory(db, vindex, embed, content="very old", updated_at=old_time, weight=1.0)

        decayed, forgotten = engine.decay(halflife_days=30, forget_threshold=0.05)
        assert decayed == 1
        assert forgotten == 1

    def test_decay_dry_run(self) -> None:
        engine, db, vindex, embed = make_engine()
        old_time = datetime.now(UTC) - timedelta(days=30)
        m = _store_memory(db, vindex, embed, content="old memory", updated_at=old_time, weight=1.0)

        decayed, forgotten = engine.decay(halflife_days=30, forget_threshold=0.05, dry_run=True)
        assert decayed == 1
        assert forgotten == 0

        memory = db.get(m.id)
        assert memory is not None
        assert memory.weight == 1.0

    def test_decay_recent_memory_not_decayed(self) -> None:
        engine, db, vindex, embed = make_engine()
        recent_time = datetime.now(UTC) - timedelta(hours=1)
        _store_memory(db, vindex, embed, content="fresh memory", updated_at=recent_time, weight=1.0)

        decayed, forgotten = engine.decay(halflife_days=30, forget_threshold=0.05)
        assert decayed == 0
        assert forgotten == 0

    def test_decay_empty_db(self) -> None:
        engine, db, vindex, embed = make_engine()
        decayed, forgotten = engine.decay()
        assert decayed == 0
        assert forgotten == 0


class TestRunCycle:
    def test_run_cycle(self) -> None:
        engine, db, vindex, embed = make_engine()
        _store_memory(db, vindex, embed, content="hello world", weight=1.0)
        _store_memory(db, vindex, embed, content="hello world", weight=1.0)
        old_time = datetime.now(UTC) - timedelta(days=30)
        _store_memory(db, vindex, embed, content="old memory", updated_at=old_time, weight=1.0)

        report = engine.run_cycle()
        assert isinstance(report, SleepReport)
        assert report.consolidated == 1
        assert report.decayed == 1
        assert report.total_before == 3
        assert report.total_after == 2
        assert report.duration_ms >= 0

    def test_run_cycle_dry_run(self) -> None:
        engine, db, vindex, embed = make_engine()
        m1 = _store_memory(db, vindex, embed, content="hello world")
        m2 = _store_memory(db, vindex, embed, content="hello world")

        report = engine.run_cycle(dry_run=True)
        assert report.consolidated == 1
        assert report.total_before == 2
        assert report.total_after == 1

        assert db.get(m1.id) is not None
        assert db.get(m2.id) is not None

    def test_sleep_report_to_dict(self) -> None:
        report = SleepReport(
            consolidated=3,
            decayed=12,
            forgotten=2,
            total_before=100,
            total_after=85,
            duration_ms=156,
        )
        d = report.to_dict()
        assert d["consolidated"] == 3
        assert d["decayed"] == 12
        assert d["forgotten"] == 2
        assert d["total_before"] == 100
        assert d["total_after"] == 85
        assert d["duration_ms"] == 156


class TestCLISleep:
    @pytest.fixture
    def runner(self):
        return CliRunner()

    @pytest.fixture
    def db_path(self):
        fd, path = tempfile.mkstemp(suffix=".db")
        os.close(fd)
        os.unlink(path)
        yield path
        if os.path.exists(path):
            os.unlink(path)

    def test_sleep_command(self, runner, db_path) -> None:
        from mneme.cli import cli

        result = runner.invoke(cli, ["sleep", "--db", db_path])
        assert result.exit_code == 0
        assert "Sleep cycle complete" in result.output

    def test_sleep_dry_run_flag(self, runner, db_path) -> None:
        from mneme.cli import cli

        result = runner.invoke(cli, ["sleep", "--dry-run", "--db", db_path])
        assert result.exit_code == 0
        assert "dry-run" in result.output.lower() or "Sleep cycle complete" in result.output


class TestAPISleep:
    @pytest.fixture
    def app(self):
        db = Database(":memory:")
        db.initialize()
        vindex = FakeVectorIndex()
        embed = FakeEmbeddingModel()
        return create_app(db=db, vindex=vindex, embed=embed)

    @pytest.fixture
    async def client(self, app):
        transport = ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
            yield ac

    async def test_post_sleep(self, client) -> None:
        resp = await client.post("/v1/sleep")
        assert resp.status_code == 200
        data = resp.json()
        assert "consolidated" in data
        assert "decayed" in data
        assert "forgotten" in data
        assert "total_before" in data
        assert "total_after" in data
        assert "duration_ms" in data

    async def test_post_sleep_dry_run(self, client) -> None:
        resp = await client.post("/v1/sleep?dry_run=true")
        assert resp.status_code == 200
        data = resp.json()
        assert data["consolidated"] == 0
        assert data["total_before"] == 0
        assert data["total_after"] == 0

    async def test_get_sleep_stats(self, client) -> None:
        resp = await client.get("/v1/sleep/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "last_sleep" in data
        assert "last_report" in data

    async def test_sleep_stats_updated_after_sleep(self, client) -> None:
        resp_before = await client.get("/v1/sleep/stats")
        assert resp_before.json()["last_sleep"] is None

        await client.post("/v1/sleep")

        resp_after = await client.get("/v1/sleep/stats")
        assert resp_after.json()["last_sleep"] is not None
        assert resp_after.json()["last_report"] is not None
