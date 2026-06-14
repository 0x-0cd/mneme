"""MCP Protocol server for Mneme."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from mneme.engine.search import Searcher
    from mneme.engine.store import Store


def create_mcp_server(store: Store, searcher: Searcher) -> FastMCP:
    from mcp.server.fastmcp import FastMCP

    mcp = FastMCP("mneme", instructions="Edge-first memory for AI agents.")

    @mcp.tool()
    def store_memory(
        content: str,
        type: str = "fact",
        tags: list[str] | None = None,
        weight: float = 1.0,
    ) -> dict:
        from mneme.engine.types import Memory

        memory = Memory(content=content, type=type, tags=tags or [], weight=weight)
        store.store(memory)
        return memory.to_dict()

    @mcp.tool()
    def search_memory(
        query: str = "",
        type: str | None = None,
        tags: str | None = None,
        limit: int = 20,
    ) -> dict:
        tag_list = tags.split(",") if tags else None
        results = searcher.search(
            query=query or None,
            type_filter=type,
            tags=tag_list,
            limit=limit,
        )
        return {"results": [dict(m.to_dict(), score=round(s, 4)) for m, s in results]}

    @mcp.tool()
    def forget_memory(memory_id: str) -> dict:
        store.delete(memory_id)
        return {"status": "deleted", "id": memory_id}

    @mcp.tool()
    def wipe_memories(confirm: bool = False) -> dict:
        if not confirm:
            return {"status": "cancelled", "message": "wipe requires confirm=True"}
        store.clear()
        return {"status": "cleared"}

    @mcp.tool()
    def memory_stats() -> dict:
        from mneme.engine.types import MemoryType

        total = store.count()
        by_type: dict[str, int] = {mt.value: 0 for mt in MemoryType}
        for m in store.db.get_all():
            by_type[m.type.value] = by_type.get(m.type.value, 0) + 1
        vector_count = store.vindex.count()
        return {
            "total_memories": total,
            "by_type": by_type,
            "vector_count": vector_count,
        }

    return mcp
