"""Search engine — semantic + keyword hybrid search for Mneme."""

from __future__ import annotations

from mneme.embed.model import EmbeddingModel
from mneme.engine.types import Memory
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


class Searcher:
    def __init__(
        self, db: Database, vindex: VectorIndex, embed: EmbeddingModel
    ) -> None:
        self.db = db
        self.vindex = vindex
        self.embed = embed

    def search(
        self,
        query: str | None = None,
        type_filter: str | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
        semantic_weight: float = 0.5,
    ) -> list[Memory]:
        if not query:
            return self.db.search(
                query=None, type_filter=type_filter, tags=tags, limit=limit
            )

        kw_results = self.db.search(
            query=query, type_filter=type_filter, tags=tags, limit=limit
        )

        sem_results: list[Memory] = []
        if semantic_weight > 0:
            qvec = self.embed.encode(query)
            if not isinstance(qvec, list):
                qvec = list(qvec)
            vec_hits = self.vindex.search(qvec, limit=limit)
            for vid, _ in vec_hits:
                m = self.db.get(vid)
                if m is None:
                    continue
                if type_filter and m.type.value != type_filter:
                    continue
                if tags and not all(t in m.tags for t in tags):
                    continue
                sem_results.append(m)

        seen: set[str] = set()
        merged: list[Memory] = []

        candidates = (
            sem_results + kw_results
            if semantic_weight >= 0.5
            else kw_results + sem_results
        )

        for m in candidates:
            if m.id not in seen:
                seen.add(m.id)
                merged.append(m)
                if len(merged) >= limit:
                    break

        return merged
