"""HTTP API routes for Mneme."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, HTTPException, Query, Request
from pydantic import BaseModel, Field

from mneme.engine.types import Memory, MemoryType

router = APIRouter()


class CreateMemoryRequest(BaseModel):
    content: str = Field(min_length=1)
    type: str = "fact"
    tags: list[str] = Field(default_factory=list)
    weight: float | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default"


class UpdateMemoryRequest(BaseModel):
    content: str | None = None
    type: str | None = None
    tags: list[str] | None = None
    weight: float | None = None
    metadata: dict[str, Any] | None = None
    user_id: str | None = None


@router.post("/v1/memories", status_code=201)
async def create_memory(req: Request, body: CreateMemoryRequest) -> dict[str, Any]:
    store = req.app.state.store
    try:
        mem_type = MemoryType(body.type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid type: {body.type}")
    memory_kwargs: dict[str, Any] = {
        "content": body.content,
        "type": mem_type,
        "tags": body.tags,
        "metadata": body.metadata,
        "user_id": body.user_id,
    }
    if body.weight is not None:
        memory_kwargs["weight"] = body.weight
    memory = Memory(**memory_kwargs)
    store.store(memory)
    return memory.to_dict()


@router.get("/v1/memories")
async def list_memories(
    req: Request,
    q: str | None = None,
    type_filter: str | None = Query(default=None, alias="type"),
    tags: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
    weight_min: float | None = None,
    weight_max: float | None = None,
    sort_by: str = "created_at",
    sort_order: str = "desc",
    include_deleted: bool = False,
    offset: int = 0,
    limit: int = 20,
    user_id: str | None = None,
) -> dict[str, Any]:
    store = req.app.state.store
    searcher = req.app.state.searcher

    if q:
        tag_list = tags.split(",") if tags else None
        results = searcher.search(
            query=q, type_filter=type_filter, tags=tag_list, limit=limit, user_id=user_id
        )
        return {"results": [dict(m.to_dict(), score=round(s, 4)) for m, s in results]}

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    try:
        memories, total = store.db.list_memories(
            offset=offset,
            limit=limit,
            type_filter=type_filter,
            tags=tag_list,
            date_from=date_from,
            date_to=date_to,
            weight_min=weight_min,
            weight_max=weight_max,
            sort_by=sort_by,
            sort_order=sort_order,
            include_deleted=include_deleted,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "results": [m.to_dict() for m in memories],
        "total": total,
        "offset": offset,
        "limit": limit,
    }


class SearchRequest(BaseModel):
    query: str = Field(default="")
    limit: int = 20
    type_filter: str | None = Field(default=None, alias="type")
    tags: list[str] | None = None
    user_id: str | None = None

    model_config = {"populate_by_name": True}


class FeedbackRequest(BaseModel):
    memory_id: str | None = None
    signal: str
    user_id: str = "default"


@router.post("/v1/memories/search")
async def search_memories(req: Request, body: SearchRequest) -> dict[str, Any]:
    """Search memories via POST (for LoCoMo benchmark compatibility)."""
    searcher = req.app.state.searcher
    tag_list = body.tags if body.tags else None
    results = searcher.search(
        query=body.query,
        type_filter=body.type_filter,
        tags=tag_list,
        limit=body.limit,
        user_id=body.user_id,
    )
    return {"results": [dict(m.to_dict(), score=round(s, 4)) for m, s in results]}


@router.get("/v1/memories/{memory_id}")
async def get_memory(memory_id: str, req: Request, user_id: str | None = None) -> dict[str, Any]:
    store = req.app.state.store
    memory = store.get(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")
    if user_id is not None and memory.user_id != user_id:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory.to_dict()


@router.put("/v1/memories/{memory_id}")
async def update_memory(memory_id: str, body: UpdateMemoryRequest, req: Request) -> dict[str, Any]:
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
    if body.user_id is not None:
        existing.user_id = body.user_id

    store.update(existing)
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
async def clear_memories(req: Request, user_id: str | None = None) -> dict[str, str]:
    store = req.app.state.store
    if user_id is not None:
        memories, _ = store.db.list_memories(offset=0, limit=100000, user_id=user_id)
        for m in memories:
            store.delete(m.id)
        return {"status": "cleared"}
    store.clear()
    return {"status": "cleared"}


@router.get("/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/v1/contradictions")
async def get_contradictions(
    req: Request,
    memory_id: str | None = None,
) -> dict[str, Any]:
    from mneme.engine.quality import ContradictionDetector

    store = req.app.state.store
    searcher = req.app.state.searcher
    detector = ContradictionDetector(
        db=store.db,
        vindex=store.vindex,
        embed=store.embed,
        searcher=searcher,
    )
    contradictions = detector.detect(memory_id=memory_id)
    return {
        "contradictions": [c.to_dict() for c in contradictions],
        "total": len(contradictions),
    }


@router.get("/v1/stats/detailed")
async def stats_detailed(req: Request, user_id: str | None = None) -> dict[str, Any]:
    store = req.app.state.store
    stats = store.db.get_detailed_stats(user_id=user_id)
    stats["vector_count"] = store.vindex.count()
    return stats


@router.get("/v1/stats")
async def stats(req: Request, user_id: str | None = None) -> dict[str, Any]:
    store = req.app.state.store
    return store.stats(user_id=user_id)


@router.post("/v1/sleep")
async def trigger_sleep(req: Request, dry_run: bool = False) -> dict[str, Any]:
    engine = req.app.state.sleep_engine
    report = engine.run_cycle(dry_run=dry_run)
    if not dry_run:
        req.app.state.sleep_stats = {
            "last_sleep": datetime.now(UTC).isoformat(),
            "last_report": report.to_dict(),
        }
    return report.to_dict()


@router.get("/v1/sleep/stats")
async def sleep_stats(req: Request) -> dict[str, Any]:
    return req.app.state.sleep_stats


@router.post("/v1/feedback")
async def submit_feedback(req: Request, body: FeedbackRequest) -> dict[str, Any]:
    calibrator = req.app.state.calibrator
    if not calibrator:
        raise HTTPException(status_code=503, detail="Calibrator not available")

    user_id = body.user_id
    mem_type: str | None = None

    if body.memory_id:
        store = req.app.state.store
        memory = store.get(body.memory_id)
        if memory:
            user_id = memory.user_id
            mem_type = str(memory.type)

    if not mem_type:
        raise HTTPException(status_code=422, detail="Could not determine memory type")

    result = calibrator.apply_feedback(
        user_id, mem_type, body.signal, memory_id=body.memory_id,
    )
    return {"status": "ok", **result}


@router.get("/v1/users/{user_id}/memories")
async def get_user_memories(
    user_id: str,
    req: Request,
    offset: int = 0,
    limit: int = 20,
    sort_by: str = "created_at",
    sort_order: str = "desc",
) -> dict[str, Any]:
    store = req.app.state.store
    try:
        memories, total = store.db.list_memories(
            offset=offset,
            limit=limit,
            sort_by=sort_by,
            sort_order=sort_order,
            user_id=user_id,
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    return {
        "results": [m.to_dict() for m in memories],
        "total": total,
        "offset": offset,
        "limit": limit,
    }
