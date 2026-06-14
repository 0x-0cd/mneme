"""Tests for HTTP API (FastAPI routes)."""

from __future__ import annotations

import httpx
from httpx import ASGITransport
import pytest

from mneme.api.app import create_app
from mneme.engine.types import Memory
from mneme.storage.db import Database

from tests.fakes import FakeVectorIndex, FakeEmbeddingModel


@pytest.fixture
def app():
    db = Database(":memory:")
    db.initialize()
    vindex = FakeVectorIndex()
    embed = FakeEmbeddingModel()
    return create_app(db=db, vindex=vindex, embed=embed)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
def sample_memory_id(app):
    store = app.state.store
    m = Memory(content="hello world", tags=["test"], metadata={"key": "val"})
    store.store(m)
    return m.id


class TestCreateMemory:
    async def test_create_memory(self, client) -> None:
        resp = await client.post(
            "/v1/memories", json={"content": "hello world"}
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "hello world"
        assert data["type"] == "fact"
        assert "id" in data

    async def test_create_memory_all_fields(self, client) -> None:
        resp = await client.post(
            "/v1/memories",
            json={
                "content": "full memory",
                "type": "preference",
                "tags": ["a", "b"],
                "weight": 2.0,
                "metadata": {"key": 42},
            },
        )
        assert resp.status_code == 201
        data = resp.json()
        assert data["content"] == "full memory"
        assert data["type"] == "preference"
        assert data["tags"] == ["a", "b"]
        assert data["weight"] == 2.0
        assert data["metadata"] == {"key": 42}

    async def test_create_memory_empty_content_422(self, client) -> None:
        resp = await client.post(
            "/v1/memories", json={"content": ""}
        )
        assert resp.status_code == 422


class TestGetMemory:
    async def test_get_memory(self, client, sample_memory_id) -> None:
        resp = await client.get(f"/v1/memories/{sample_memory_id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "hello world"
        assert data["tags"] == ["test"]
        assert data["metadata"] == {"key": "val"}

    async def test_get_memory_404(self, client) -> None:
        resp = await client.get("/v1/memories/nonexistent-id")
        assert resp.status_code == 404


class TestSearchMemories:
    async def test_search_memories(self, client, sample_memory_id) -> None:
        resp = await client.get("/v1/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert "results" in data
        assert len(data["results"]) >= 1

    async def test_search_with_filters(self, client, sample_memory_id) -> None:
        await client.post("/v1/memories", json={"content": "urgent work task", "tags": ["urgent", "work"]})
        await client.post("/v1/memories", json={"content": "fun task", "tags": ["fun"]})
        resp = await client.get("/v1/memories", params={"type": "fact", "tags": "urgent"})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 1


class TestUpdateMemory:
    async def test_update_memory(self, client, sample_memory_id) -> None:
        resp = await client.put(
            f"/v1/memories/{sample_memory_id}",
            json={"content": "updated content", "type": "preference"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["content"] == "updated content"
        assert data["type"] == "preference"

    async def test_update_memory_partial(self, client, sample_memory_id) -> None:
        resp = await client.put(
            f"/v1/memories/{sample_memory_id}",
            json={"tags": ["new-tag"]},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["tags"] == ["new-tag"]
        assert data["content"] == "hello world"

    async def test_update_memory_404(self, client) -> None:
        resp = await client.put(
            "/v1/memories/nonexistent",
            json={"content": "nope"},
        )
        assert resp.status_code == 404


class TestDeleteMemory:
    async def test_delete_memory(self, client, sample_memory_id) -> None:
        resp = await client.delete(f"/v1/memories/{sample_memory_id}")
        assert resp.status_code == 200
        assert resp.json() == {"status": "deleted"}
        get_resp = await client.get(f"/v1/memories/{sample_memory_id}")
        assert get_resp.status_code == 404

    async def test_delete_memory_nonexistent(self, client) -> None:
        resp = await client.delete("/v1/memories/nonexistent")
        assert resp.status_code == 404


class TestClearAll:
    async def test_clear_all(self, client) -> None:
        await client.post("/v1/memories", json={"content": "a"})
        await client.post("/v1/memories", json={"content": "b"})
        resp = await client.delete("/v1/memories")
        assert resp.status_code == 200
        assert resp.json() == {"status": "cleared"}
        list_resp = await client.get("/v1/memories")
        assert len(list_resp.json()["results"]) == 0


class TestHealthAndStats:
    async def test_health(self, client) -> None:
        resp = await client.get("/v1/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    async def test_stats(self, client) -> None:
        resp = await client.get("/v1/stats")
        assert resp.status_code == 200
        data = resp.json()
        assert "total" in data
        assert "by_type" in data
