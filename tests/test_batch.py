"""Tests for batch operations, pagination, export/import."""

from __future__ import annotations

import httpx
import pytest
from httpx import ASGITransport

from mneme.api.app import create_app
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


def _make_memory(
    content: str, type_: str = "fact", tags: list[str] | None = None, weight: float = 1.0
) -> dict:
    return {"content": content, "type": type_, "tags": tags or [], "weight": weight}


class TestListPagination:
    async def test_list_pagination(self, client) -> None:
        for i in range(25):
            await client.post("/v1/memories", json={"content": f"memory {i:02d}"})

        resp = await client.get("/v1/memories", params={"offset": 0, "limit": 10})
        assert resp.status_code == 200
        data = resp.json()
        assert len(data["results"]) == 10
        assert data["total"] == 25
        assert data["offset"] == 0
        assert data["limit"] == 10

        resp2 = await client.get("/v1/memories", params={"offset": 10, "limit": 10})
        assert resp2.status_code == 200
        data2 = resp2.json()
        assert len(data2["results"]) == 10
        assert data2["total"] == 25

        resp3 = await client.get("/v1/memories", params={"offset": 20, "limit": 10})
        data3 = resp3.json()
        assert len(data3["results"]) == 5
        assert data3["total"] == 25

    async def test_list_empty_db(self, client) -> None:
        resp = await client.get("/v1/memories")
        assert resp.status_code == 200
        data = resp.json()
        assert data["results"] == []
        assert data["total"] == 0

    async def test_list_offset_beyond_range(self, client) -> None:
        await client.post("/v1/memories", json={"content": "only one"})
        resp = await client.get("/v1/memories", params={"offset": 100})
        data = resp.json()
        assert data["results"] == []
        assert data["total"] == 1


class TestListFilterByType:
    async def test_list_filter_by_type(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("fact one", "fact"))
        await client.post("/v1/memories", json=_make_memory("pref one", "preference"))
        await client.post("/v1/memories", json=_make_memory("fact two", "fact"))

        resp = await client.get("/v1/memories", params={"type": "fact"})
        data = resp.json()
        assert data["total"] == 2
        for r in data["results"]:
            assert r["type"] == "fact"

    async def test_list_filter_type_no_match(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("fact one", "fact"))
        resp = await client.get("/v1/memories", params={"type": "event"})
        data = resp.json()
        assert data["total"] == 0
        assert data["results"] == []


class TestListFilterByTags:
    async def test_list_filter_by_tags(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("urgent work", tags=["urgent", "work"]))
        await client.post("/v1/memories", json=_make_memory("fun task", tags=["fun"]))
        await client.post("/v1/memories", json=_make_memory("work report", tags=["work"]))

        resp = await client.get("/v1/memories", params={"tags": "work"})
        data = resp.json()
        assert data["total"] == 2
        for r in data["results"]:
            assert "work" in r["tags"]

    async def test_list_filter_multiple_tags(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("a", tags=["urgent", "work"]))
        await client.post("/v1/memories", json=_make_memory("b", tags=["urgent"]))
        await client.post("/v1/memories", json=_make_memory("c", tags=["work"]))

        resp = await client.get("/v1/memories", params={"tags": "urgent,work"})
        data = resp.json()
        assert data["total"] == 1
        assert data["results"][0]["tags"] == ["urgent", "work"]


class TestListSortOrder:
    async def test_list_sort_by_weight_asc(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("low", weight=0.5))
        await client.post("/v1/memories", json=_make_memory("high", weight=2.0))
        await client.post("/v1/memories", json=_make_memory("mid", weight=1.0))

        resp = await client.get("/v1/memories", params={"sort_by": "weight", "sort_order": "asc"})
        data = resp.json()
        assert len(data["results"]) == 3
        weights = [r["weight"] for r in data["results"]]
        assert weights == sorted(weights)

    async def test_list_sort_created_desc(self, client) -> None:
        await client.post("/v1/memories", json={"content": "first"})
        await client.post("/v1/memories", json={"content": "second"})

        resp = await client.get("/v1/memories", params={"sort_order": "desc"})
        data = resp.json()
        assert data["results"][0]["content"] == "second"

    async def test_list_invalid_sort_column(self, client) -> None:
        resp = await client.get("/v1/memories", params={"sort_by": "invalid"})
        assert resp.status_code == 422


class TestListIncludeDeleted:
    async def test_list_include_deleted(self, client) -> None:
        await client.post("/v1/memories", json={"content": "alive"})
        resp2 = await client.post("/v1/memories", json={"content": "dead"})
        dead_id = resp2.json()["id"]

        await client.delete(f"/v1/memories/{dead_id}")

        resp = await client.get("/v1/memories", params={"include_deleted": "true"})
        data = resp.json()
        assert data["total"] == 2

        resp_no = await client.get("/v1/memories")
        data_no = resp_no.json()
        assert data_no["total"] == 1


class TestBatchDelete:
    async def test_batch_delete_by_type(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("fact a", "fact"))
        await client.post("/v1/memories", json=_make_memory("fact b", "fact"))
        await client.post("/v1/memories", json=_make_memory("pref x", "preference"))

        resp = await client.post("/v1/memories/batch/delete", json={"type": "fact"})
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2

        list_resp = await client.get("/v1/memories", params={"type": "fact"})
        assert list_resp.json()["total"] == 0
        pref_resp = await client.get("/v1/memories", params={"type": "preference"})
        assert pref_resp.json()["total"] == 1

    async def test_batch_delete_by_tags(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("a", tags=["temp"]))
        await client.post("/v1/memories", json=_make_memory("b", tags=["temp", "draft"]))
        await client.post("/v1/memories", json=_make_memory("c", tags=["keep"]))

        resp = await client.post("/v1/memories/batch/delete", json={"tags": ["temp"]})
        assert resp.status_code == 200
        assert resp.json()["deleted"] == 2

        remaining = await client.get("/v1/memories")
        assert remaining.json()["total"] == 1

    async def test_batch_delete_no_match(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("only", tags=["keep"]))
        resp = await client.post("/v1/memories/batch/delete", json={"tags": ["nonexistent"]})
        assert resp.json()["deleted"] == 0

    async def test_batch_delete_cleans_vector_index(self, client) -> None:
        resp = await client.post("/v1/memories", json=_make_memory("to delete", tags=["temp"]))
        memory_id = resp.json()["id"]

        vindex = client._transport.app.state.store.vindex
        assert memory_id in vindex.vectors

        await client.post("/v1/memories/batch/delete", json={"tags": ["temp"]})
        assert memory_id not in vindex.vectors


class TestBatchUpdate:
    async def test_batch_update_tags(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("a", tags=["old"]))
        await client.post("/v1/memories", json=_make_memory("b", tags=["old"]))
        await client.post("/v1/memories", json=_make_memory("c", tags=["keep"]))

        resp = await client.post(
            "/v1/memories/batch/update",
            json={"tags": ["old"], "updates": {"tags": ["new"]}},
        )
        assert resp.status_code == 200
        assert resp.json()["updated"] == 2

        results = await client.get("/v1/memories", params={"tags": "new"})
        assert results.json()["total"] == 2

    async def test_batch_update_weight(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("a", "fact", weight=1.0))
        await client.post("/v1/memories", json=_make_memory("b", "preference", weight=1.0))
        await client.post("/v1/memories", json=_make_memory("c", "fact", weight=1.0))

        resp = await client.post(
            "/v1/memories/batch/update",
            json={"type": "fact", "updates": {"weight": 2.5}},
        )
        assert resp.json()["updated"] == 2

        results = await client.get("/v1/memories", params={"type": "fact"})
        for r in results.json()["results"]:
            assert r["weight"] == 2.5

    async def test_batch_update_type(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("legacy", "fact", tags=["migrate"]))
        await client.post("/v1/memories", json=_make_memory("keep", "fact"))

        resp = await client.post(
            "/v1/memories/batch/update",
            json={"tags": ["migrate"], "updates": {"type": "event"}},
        )
        assert resp.json()["updated"] == 1

    async def test_batch_update_empty_updates(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("a"))
        resp = await client.post("/v1/memories/batch/update", json={"type": "fact", "updates": {}})
        assert resp.json()["updated"] == 0


class TestRestore:
    async def test_restore_single(self, client) -> None:
        resp = await client.post("/v1/memories", json={"content": "will be back"})
        memory_id = resp.json()["id"]

        await client.delete(f"/v1/memories/{memory_id}")
        get_resp = await client.get(f"/v1/memories/{memory_id}")
        assert get_resp.status_code == 404

        restore_resp = await client.post(f"/v1/memories/{memory_id}/restore")
        assert restore_resp.status_code == 200
        assert restore_resp.json() == {"status": "restored"}

        get_again = await client.get(f"/v1/memories/{memory_id}")
        assert get_again.status_code == 200

    async def test_restore_nonexistent(self, client) -> None:
        resp = await client.post("/v1/memories/nonexistent-id/restore")
        assert resp.status_code == 404

    async def test_restore_not_deleted(self, client) -> None:
        resp = await client.post("/v1/memories", json={"content": "alive"})
        memory_id = resp.json()["id"]

        restore_resp = await client.post(f"/v1/memories/{memory_id}/restore")
        assert restore_resp.status_code == 404

    async def test_restore_batch(self, client) -> None:
        resp1 = await client.post("/v1/memories", json={"content": "a"})
        resp2 = await client.post("/v1/memories", json={"content": "b"})
        resp3 = await client.post("/v1/memories", json={"content": "c"})
        ids = [resp1.json()["id"], resp2.json()["id"], resp3.json()["id"]]

        for mid in ids:
            await client.delete(f"/v1/memories/{mid}")

        restore_resp = await client.post("/v1/memories/batch/restore", json=ids[:2])
        assert restore_resp.json()["restored"] == 2

        deleted = await client.get("/v1/memories/deleted")
        assert len(deleted.json()["results"]) == 1


class TestExportImport:
    async def test_export_import_roundtrip(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("alpha", "fact", ["test"]))
        await client.post("/v1/memories", json=_make_memory("beta", "preference", ["ref"]))
        # Soft-delete one
        resp = await client.post("/v1/memories", json=_make_memory("gamma", tags=["del"]))
        gamma_id = resp.json()["id"]
        await client.delete(f"/v1/memories/{gamma_id}")

        export_resp = await client.get("/v1/export")
        assert export_resp.status_code == 200
        exported = export_resp.json()
        assert len(exported) == 3

        # Clear everything
        await client.delete("/v1/memories")
        list_resp = await client.get("/v1/memories")
        assert list_resp.json()["total"] == 0

        # Import
        import_resp = await client.post("/v1/import", json=exported)
        assert import_resp.status_code == 200
        assert import_resp.json()["imported"] == 3

        # Verify all are back
        verify = await client.get("/v1/memories", params={"include_deleted": "true"})
        assert verify.json()["total"] == 3

        # Verify vector index rebuilt
        vindex = client._transport.app.state.store.vindex
        assert vindex.count() == 3

    async def test_import_duplicate_ids_ignored(self, client) -> None:
        resp = await client.post("/v1/memories", json={"content": "existing"})
        existing_data = resp.json()

        import_resp = await client.post("/v1/import", json=[existing_data])
        assert import_resp.json()["imported"] == 0

    async def test_export_empty(self, client) -> None:
        resp = await client.get("/v1/export")
        assert resp.status_code == 200
        assert resp.json() == []


class TestDeletedList:
    async def test_list_deleted(self, client) -> None:
        resp = await client.post("/v1/memories", json={"content": "deleted one"})
        mid = resp.json()["id"]
        await client.delete(f"/v1/memories/{mid}")

        resp = await client.get("/v1/memories/deleted")
        data = resp.json()
        assert len(data["results"]) == 1
        assert data["results"][0]["id"] == mid

    async def test_list_deleted_empty(self, client) -> None:
        await client.post("/v1/memories", json={"content": "alive"})
        resp = await client.get("/v1/memories/deleted")
        assert resp.json()["results"] == []


class TestStatsDetailed:
    async def test_stats_detailed(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("a", "fact", ["urgent"], weight=1.0))
        await client.post(
            "/v1/memories", json=_make_memory("b", "preference", ["urgent"], weight=2.0)
        )
        await client.post("/v1/memories", json=_make_memory("c", "fact", ["nice"], weight=0.5))
        # Create and delete one
        resp = await client.post("/v1/memories", json=_make_memory("d", tags=["temp"]))
        await client.delete(f"/v1/memories/{resp.json()['id']}")

        resp = await client.get("/v1/stats/detailed")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] == 3
        assert data["by_type"] == {"fact": 2, "preference": 1}
        assert data["total_weight"] == 3.5
        assert data["deleted_count"] == 1
        assert data["vector_count"] == 3
        assert "by_tag" in data


class TestDateFilter:
    async def test_list_filter_by_date_range(self, client) -> None:
        import time
        from datetime import UTC, datetime

        await client.post("/v1/memories", json={"content": "old"})
        time.sleep(0.1)

        future_date = datetime.now(UTC).isoformat()
        resp = await client.get("/v1/memories", params={"date_to": future_date})
        assert resp.json()["total"] >= 1


class TestWeightFilter:
    async def test_list_filter_by_weight_range(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("low", weight=0.3))
        await client.post("/v1/memories", json=_make_memory("mid", weight=1.0))
        await client.post("/v1/memories", json=_make_memory("high", weight=2.5))

        resp = await client.get("/v1/memories", params={"weight_min": 0.5, "weight_max": 2.0})
        data = resp.json()
        assert data["total"] == 1
        assert data["results"][0]["content"] == "mid"

    async def test_list_weight_min_only(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("low", weight=0.2))
        await client.post("/v1/memories", json=_make_memory("high", weight=3.0))

        resp = await client.get("/v1/memories", params={"weight_min": 1.0})
        assert resp.json()["total"] == 1

    async def test_list_weight_max_only(self, client) -> None:
        await client.post("/v1/memories", json=_make_memory("low", weight=0.2))
        await client.post("/v1/memories", json=_make_memory("high", weight=3.0))

        resp = await client.get("/v1/memories", params={"weight_max": 1.0})
        assert resp.json()["total"] == 1


class TestSearchWithQ:
    async def test_search_with_q_uses_searcher(self, client) -> None:
        await client.post("/v1/memories", json={"content": "hello world"})
        await client.post("/v1/memories", json={"content": "goodbye moon"})

        resp = await client.get("/v1/memories", params={"q": "hello"})
        data = resp.json()
        assert "results" in data
        # Searcher returns results with score field (no total/offset/limit)
        assert "score" in data["results"][0]
