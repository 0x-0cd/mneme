"""Core storage engine orchestrating embedding, DB, and vector index."""

from __future__ import annotations

from mneme.embed.model import EmbeddingModel
from mneme.engine.types import Memory
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


class Store:
    def __init__(
        self, db: Database, vindex: VectorIndex, embed: EmbeddingModel
    ) -> None:
        self.db = db
        self.vindex = vindex
        self.embed = embed

    def store(self, memory: Memory) -> Memory:
        embedding = self.embed.encode(memory.content)
        self.db.insert(memory)
        self.vindex.insert(memory.id, embedding)
        return memory

    def get(self, memory_id: str) -> Memory | None:
        return self.db.get(memory_id)

    def delete(self, memory_id: str) -> None:
        self.db.soft_delete(memory_id)
        self.vindex.delete(memory_id)

    def clear(self) -> None:
        self.db.clear()
        self.vindex.clear()

    def count(self) -> int:
        return self.db.count()
