"""Core storage engine orchestrating embedding, DB, and vector index."""

from __future__ import annotations

from mneme.embed.model import EmbeddingModel
from mneme.engine.types import Memory
from mneme.plugin.bus import EventBus
from mneme.plugin.event import EventType
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


class Store:
    def __init__(
        self,
        db: Database,
        vindex: VectorIndex,
        embed: EmbeddingModel,
        event_bus: EventBus | None = None,
    ) -> None:
        self.db = db
        self.vindex = vindex
        self.embed = embed
        self.event_bus = event_bus

    def store(self, memory: Memory) -> Memory:
        if self.event_bus:
            self.event_bus.emit(EventType.BEFORE_CREATE, memory=memory.to_dict())
        embedding = self.embed.encode(memory.content)
        self.db.insert(memory)
        self.vindex.upsert(memory.id, embedding)
        if self.event_bus:
            self.event_bus.emit(EventType.AFTER_CREATE, memory=memory.to_dict())
        return memory

    def get(self, memory_id: str) -> Memory | None:
        return self.db.get(memory_id)

    def delete(self, memory_id: str) -> None:
        if self.event_bus:
            self.event_bus.emit(EventType.BEFORE_DELETE, memory_id=memory_id)
        self.db.soft_delete(memory_id)
        self.vindex.delete(memory_id)
        if self.event_bus:
            self.event_bus.emit(EventType.AFTER_DELETE, memory_id=memory_id)

    def update(self, memory: Memory) -> Memory:
        if self.event_bus:
            self.event_bus.emit(EventType.BEFORE_UPDATE, memory=memory.to_dict())
        embedding = self.embed.encode(memory.content)
        if not isinstance(embedding, list):
            embedding = list(embedding)
        self.vindex.delete(memory.id)
        self.vindex.upsert(memory.id, embedding)
        self.db.update(memory)
        if self.event_bus:
            self.event_bus.emit(EventType.AFTER_UPDATE, memory=memory.to_dict())
        return memory

    def clear(self) -> None:
        self.db.clear()
        self.vindex.clear()

    def count(self, user_id: str | None = None) -> int:
        return self.db.count(user_id=user_id)

    def stats(self, user_id: str | None = None) -> dict:
        """Get memory statistics: total count, per-type, and vector count."""
        db_stats = self.db.get_stats(user_id=user_id)
        db_stats["vector_count"] = self.vindex.count()
        return db_stats
