"""Integration tests for Mneme — end-to-end API lifecycle."""

from __future__ import annotations

import hashlib
import math
import random

import httpx
from httpx import ASGITransport
import pytest

from mneme.api.app import create_app
from mneme.storage.db import Database


class FakeVectorIndex:
    def __init__(self) -> None:
        self.vectors: dict[str, list[float]] = {}

    def initialize(self) -> None:
        pass

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

    def close(self) -> None:
        pass


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


@pytest.fixture
def app():
    db = Database(":memory:")
    db.initialize()
    vindex = FakeVectorIndex()
    vindex.initialize()
    embed = FakeEmbeddingModel()
    return create_app(db=db, vindex=vindex, embed=embed)


@pytest.fixture
async def client(app):
    transport = ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_full_lifecycle(client) -> None:
    # 1. Create 3 memories of different types
    fact_resp = await client.post(
        "/v1/memories",
        json={"content": "Python is a programming language", "type": "fact", "tags": ["python", "language"]},
    )
    assert fact_resp.status_code == 201
    fact_id = fact_resp.json()["id"]

    pref_resp = await client.post(
        "/v1/memories",
        json={"content": "I prefer dark mode", "type": "preference", "tags": ["ui", "theme"]},
    )
    assert pref_resp.status_code == 201
    pref_id = pref_resp.json()["id"]

    event_resp = await client.post(
        "/v1/memories",
        json={"content": "Deployed v2.0 to production", "type": "event", "tags": ["deploy", "v2"]},
    )
    assert event_resp.status_code == 201
    event_id = event_resp.json()["id"]

    # 2. Read by ID
    get_resp = await client.get(f"/v1/memories/{fact_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["content"] == "Python is a programming language"

    # 3. Keyword search
    search_resp = await client.get("/v1/memories", params={"q": "dark"})
    assert search_resp.status_code == 200
    results = search_resp.json()["results"]
    assert len(results) >= 1
    assert results[0]["id"] == pref_id

    # 4. Filter by type
    type_resp = await client.get("/v1/memories", params={"type": "event"})
    assert type_resp.status_code == 200
    type_results = type_resp.json()["results"]
    assert len(type_results) == 1
    assert type_results[0]["id"] == event_id

    # 5. Filter by tags
    tag_resp = await client.get("/v1/memories", params={"tags": "python"})
    assert tag_resp.status_code == 200
    tag_results = tag_resp.json()["results"]
    assert len(tag_results) == 1
    assert tag_results[0]["id"] == fact_id

    # 6. Update content
    update_resp = await client.put(
        f"/v1/memories/{fact_id}",
        json={"content": "Python is a dynamically-typed programming language", "tags": ["python", "language", "dynamic"]},
    )
    assert update_resp.status_code == 200
    assert "dynamically-typed" in update_resp.json()["content"]
    assert "dynamic" in update_resp.json()["tags"]

    # 7. Soft delete
    delete_resp = await client.delete(f"/v1/memories/{pref_id}")
    assert delete_resp.status_code == 200
    assert delete_resp.json() == {"status": "deleted"}
    get_deleted = await client.get(f"/v1/memories/{pref_id}")
    assert get_deleted.status_code == 404

    # 8. Stats
    stats_resp = await client.get("/v1/stats")
    assert stats_resp.status_code == 200
    stats = stats_resp.json()
    assert stats["total"] == 2
    assert stats["by_type"]["fact"] == 1
    assert stats["by_type"]["event"] == 1

    # 9. Clear all
    clear_resp = await client.delete("/v1/memories")
    assert clear_resp.status_code == 200
    assert clear_resp.json() == {"status": "cleared"}
    list_resp = await client.get("/v1/memories")
    assert len(list_resp.json()["results"]) == 0


@pytest.mark.asyncio
async def test_health_endpoint(client) -> None:
    resp = await client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


@pytest.mark.asyncio
async def test_invalid_memory_type(client) -> None:
    resp = await client.post(
        "/v1/memories",
        json={"content": "invalid type test", "type": "unknown_type"},
    )
    assert resp.status_code == 422
