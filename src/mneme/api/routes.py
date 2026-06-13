"""HTTP API routes for Mneme."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from mneme.engine.types import Memory, MemoryType

router = APIRouter()


class CreateMemoryRequest(BaseModel):
    content: str = Field(min_length=1)
    type: str = "fact"
    tags: list[str] = Field(default_factory=list)
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)


class UpdateMemoryRequest(BaseModel):
    content: str | None = None
    type: str | None = None
    tags: list[str] | None = None
    weight: float | None = None
    metadata: dict[str, Any] | None = None


@router.post("/v1/memories", status_code=201)
async def create_memory(req: Request, body: CreateMemoryRequest) -> dict[str, Any]:
    store = req.app.state.store
    memory = Memory(
        content=body.content,
        type=MemoryType(body.type),
        tags=body.tags,
        weight=body.weight,
        metadata=body.metadata,
    )
    store.store(memory)
    return memory.to_dict()


@router.get("/v1/memories")
async def list_memories(
    req: Request,
    q: str | None = None,
    type: str | None = None,
    tags: str | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    searcher = req.app.state.searcher
    tag_list = tags.split(",") if tags else None
    results = searcher.search(
        query=q, type_filter=type, tags=tag_list, limit=limit
    )
    return {"results": [m.to_dict() for m in results]}


@router.get("/v1/memories/{memory_id}")
async def get_memory(memory_id: str, req: Request) -> dict[str, Any]:
    store = req.app.state.store
    memory = store.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory.to_dict()


@router.put("/v1/memories/{memory_id}")
async def update_memory(
    memory_id: str, body: UpdateMemoryRequest, req: Request
) -> dict[str, Any]:
    store = req.app.state.store
    existing = store.get(memory_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Memory not found")

    if body.content is not None:
        existing.content = body.content
    if body.type is not None:
        existing.type = MemoryType(body.type)
    if body.tags is not None:
        existing.tags = body.tags
    if body.weight is not None:
        existing.weight = body.weight
    if body.metadata is not None:
        existing.metadata = body.metadata

    embedding = store.embed.encode(existing.content)
    if not isinstance(embedding, list):
        embedding = list(embedding)

    store.vindex.delete(memory_id)
    store.vindex.insert(memory_id, embedding)
    store.db.update(existing)

    return existing.to_dict()


@router.delete("/v1/memories/{memory_id}")
async def delete_memory(memory_id: str, req: Request) -> dict[str, str]:
    store = req.app.state.store
    existing = store.get(memory_id)
    if not existing:
        raise HTTPException(status_code=404, detail="Memory not found")
    store.delete(memory_id)
    return {"status": "deleted"}


@router.delete("/v1/memories")
async def clear_memories(req: Request) -> dict[str, str]:
    store = req.app.state.store
    store.clear()
    return {"status": "cleared"}


@router.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/stats")
async def stats(req: Request) -> dict[str, Any]:
    store = req.app.state.store
    total = store.count()
    rows = store.db.cursor.execute(
        "SELECT type, COUNT(*) AS cnt FROM memories WHERE deleted_at IS NULL GROUP BY type"
    ).fetchall()
    by_type: dict[str, int] = {r["type"]: r["cnt"] for r in rows}
    return {"total": total, "by_type": by_type}
