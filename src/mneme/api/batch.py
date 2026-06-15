"""Batch operations and export/import routes for Mneme."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

router = APIRouter()


class BatchDeleteRequest(BaseModel):
    type: str | None = None
    tags: list[str] | None = None
    date_from: str | None = None
    date_to: str | None = None
    weight_min: float | None = None
    weight_max: float | None = None
    user_id: str | None = None


class BatchUpdateRequest(BatchDeleteRequest):
    updates: dict[str, Any]


@router.post("/v1/memories/batch/delete")
async def batch_delete(req: Request, body: BatchDeleteRequest) -> dict[str, Any]:
    store = req.app.state.store
    deleted_count, deleted_ids = store.db.batch_delete(
        type_filter=body.type,
        tags=body.tags,
        date_from=body.date_from,
        date_to=body.date_to,
        weight_min=body.weight_min,
        weight_max=body.weight_max,
        user_id=body.user_id,
    )
    for mid in deleted_ids:
        store.vindex.delete(mid)
    return {"deleted": deleted_count}


@router.post("/v1/memories/batch/update")
async def batch_update(req: Request, body: BatchUpdateRequest) -> dict[str, Any]:
    store = req.app.state.store
    updated = store.db.batch_update(
        updates=body.updates,
        type_filter=body.type,
        tags=body.tags,
        date_from=body.date_from,
        date_to=body.date_to,
        weight_min=body.weight_min,
        weight_max=body.weight_max,
        user_id=body.user_id,
    )
    return {"updated": updated}


@router.post("/v1/memories/batch/restore")
async def batch_restore(req: Request, memory_ids: list[str]) -> dict[str, Any]:
    store = req.app.state.store
    restored = 0
    for mid in memory_ids:
        if store.db.restore(mid):
            restored += 1
    return {"restored": restored}


@router.get("/v1/memories/deleted")
async def list_deleted(req: Request, limit: int = 50) -> dict[str, Any]:
    store = req.app.state.store
    memories = store.db.get_deleted(limit=limit)
    return {"results": [m.to_dict() for m in memories]}


@router.post("/v1/memories/{memory_id}/restore")
async def restore_memory(memory_id: str, req: Request) -> dict[str, Any]:
    store = req.app.state.store
    if not store.db.restore(memory_id):
        raise HTTPException(status_code=404, detail="Memory not found or not deleted")
    return {"status": "restored"}


@router.get("/v1/export")
async def export_memories(req: Request) -> list[dict[str, Any]]:
    store = req.app.state.store
    return store.db.export_all()


@router.post("/v1/import")
async def import_memories(req: Request, memories: list[dict[str, Any]]) -> dict[str, Any]:
    store = req.app.state.store
    count, imported = store.db.import_memories(memories)
    for mem in imported:
        content = mem.get("content", "")
        if content:
            embedding = store.embed.encode(content)
            if not isinstance(embedding, list):
                embedding = list(embedding)
            store.vindex.upsert(mem["id"], embedding)
    return {"imported": count}
