"""Tests for multi-user support: isolation, filtering, and user endpoints."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from mneme.api.app import create_app
from mneme.engine.types import Memory
from mneme.storage.db import Database
from tests.fakes import FakeEmbeddingModel, FakeVectorIndex


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


class TestMultiUserIsolation:
    async def test_user_a_memory_not_visible_to_user_b(self, client) -> None:
        # Create memory for user_a
        resp = await client.post(
            "/v1/memories",
            json={"content": "user a secret", "user_id": "user_a"},
        )
        assert resp.status_code == 201

        # Search as user_b should not find it
        resp = await client.get("/v1/memories", params={"user_id": "user_b"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

        # Search as user_a should find it
        resp = await client.get("/v1/memories", params={"user_id": "user_a"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["results"][0]["content"] == "user a secret"

    async def test_user_b_memory_not_visible_to_user_a(self, client) -> None:
        # Create memory for user_b
        resp = await client.post(
            "/v1/memories",
            json={"content": "user b data", "user_id": "user_b"},
        )
        assert resp.status_code == 201

        # user_a should not find it
        resp = await client.get("/v1/memories", params={"user_id": "user_a"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_default_user_id(self, client) -> None:
        # No user_id specified -> defaults to "default"
        resp = await client.post(
            "/v1/memories",
            json={"content": "default user content"},
        )
        assert resp.status_code == 201

        # Should be visible when querying without user_id filter
        resp = await client.get("/v1/memories")
        assert resp.status_code == 200
        assert resp.json()["total"] == 1
        assert resp.json()["results"][0]["user_id"] == "default"

        # Should be visible when querying with user_id="default"
        resp = await client.get("/v1/memories", params={"user_id": "default"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

        # Should NOT be visible when querying with user_id="other"
        resp = await client.get("/v1/memories", params={"user_id": "other"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_batch_delete_by_user_id(self, client) -> None:
        # Create memories for two users
        await client.post(
            "/v1/memories",
            json={"content": "a1", "user_id": "user_a"},
        )
        await client.post(
            "/v1/memories",
            json={"content": "a2", "user_id": "user_a"},
        )
        await client.post(
            "/v1/memories",
            json={"content": "b1", "user_id": "user_b"},
        )

        # Batch delete only user_a's memories
        resp = await client.post(
            "/v1/memories/batch/delete",
            json={"user_id": "user_a"},
        )
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2

        # user_b should still have 1 memory
        resp = await client.get("/v1/memories", params={"user_id": "user_b"})
        assert resp.status_code == 200
        assert resp.json()["total"] == 1

    async def test_stats_by_user_id(self, client) -> None:
        await client.post(
            "/v1/memories",
            json={"content": "a", "user_id": "user_a", "type": "fact"},
        )
        await client.post(
            "/v1/memories",
            json={"content": "b", "user_id": "user_a", "type": "preference"},
        )

        # Stats filtered by user_a
        resp = await client.get("/v1/stats", params={"user_id": "user_a"})
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        assert data["by_type"]["fact"] == 1
        assert data["by_type"]["preference"] == 1

    async def test_get_user_memories_route(self, client) -> None:
        await client.post(
            "/v1/memories",
            json={"content": "a1", "user_id": "user_a"},
        )
        await client.post(
            "/v1/memories",
            json={"content": "a2", "user_id": "user_a"},
        )
        await client.post(
            "/v1/memories",
            json={"content": "b1", "user_id": "user_b"},
        )

        resp = await client.get("/v1/users/user_a/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 2
        contents = {r["content"] for r in data["results"]}
        assert contents == {"a1", "a2"}

    async def test_get_user_memories_returns_empty_for_unknown_user(self, client) -> None:
        resp = await client.get("/v1/users/nonexistent/memories")
        assert resp.status_code == 200
        assert resp.json()["total"] == 0

    async def test_get_memory_by_id_with_user_id(self, client) -> None:
        resp = await client.post(
            "/v1/memories",
            json={"content": "secret", "user_id": "user_a"},
        )
        assert resp.status_code == 201
        mem_id = resp.json()["id"]

        # Can access without user_id filter
        resp = await client.get(f"/v1/memories/{mem_id}")
        assert resp.status_code == 200

        # Can access with matching user_id
        resp = await client.get(f"/v1/memories/{mem_id}", params={"user_id": "user_a"})
        assert resp.status_code == 200

        # Cannot access with wrong user_id
        resp = await client.get(f"/v1/memories/{mem_id}", params={"user_id": "user_b"})
        assert resp.status_code == 404

    async def test_list_memories_with_q_and_user_id(self, client) -> None:
        # Two users, distinct content, different character profile
        await client.post(
            "/v1/memories",
            json={"content": "planning a trip to the mountains", "user_id": "user_a"},
        )
        await client.post(
            "/v1/memories",
            json={"content": "buying groceries at the market", "user_id": "user_b"},
        )

        # user_a searches — should only get user_a's content, not user_b's
        resp = await client.get(
            "/v1/memories",
            params={"q": "mountains", "user_id": "user_a"},
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) >= 1
        assert all(r["user_id"] == "user_a" for r in results)

        # user_b searches — should only get user_b's content, not user_a's
        resp = await client.get(
            "/v1/memories",
            params={"q": "groceries", "user_id": "user_b"},
        )
        assert resp.status_code == 200
        results = resp.json()["results"]
        assert len(results) >= 1
        assert all(r["user_id"] == "user_b" for r in results)

    async def test_search_post_with_user_id(self, client) -> None:
        await client.post(
            "/v1/memories",
            json={"content": "cat", "user_id": "user_a"},
        )

        resp = await client.post(
            "/v1/memories/search",
            json={"query": "cat", "user_id": "user_a"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 1

        resp = await client.post(
            "/v1/memories/search",
            json={"query": "cat", "user_id": "user_b"},
        )
        assert resp.status_code == 200
        assert len(resp.json()["results"]) == 0


class TestMultiUserStore:
    def test_user_id_in_memory_object(self, app) -> None:
        store = app.state.store
        m = Memory(content="test", user_id="custom_user")
        store.store(m)

        retrieved = store.get(m.id)
        assert retrieved is not None
        assert retrieved.user_id == "custom_user"

    def test_user_id_roundtrip_through_db(self, app) -> None:
        store = app.state.store
        m = Memory(content="persist me", user_id="user_42")
        store.store(m)

        retrieved = store.get(m.id)
        assert retrieved is not None
        assert retrieved.user_id == "user_42"
        assert retrieved.content == "persist me"

    def test_default_user_id_no_args(self) -> None:
        m = Memory(content="implicit")
        assert m.user_id == "default"
