"""Search engine — semantic + keyword hybrid search for Mneme."""

from __future__ import annotations

from mneme.embed.model import EmbeddingModel
from mneme.engine.types import Memory
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


class Searcher:
    def __init__(self, db: Database, vindex: VectorIndex, embed: EmbeddingModel) -> None:
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
        user_id: str | None = None,
    ) -> list[tuple[Memory, float]]:
        """Search and return (Memory, similarity_score) pairs.

        Score is a similarity value in [0, 1] (1 = most similar).
        For keyword-only results without query, score is 0.0.
        """
        if not query:
            memories = self.db.search(query=None, type_filter=type_filter, tags=tags, limit=limit)
            if user_id is not None:
                memories = [m for m in memories if m.user_id == user_id]
            return [(m, 0.0) for m in memories]

        kw_results = self.db.search(query=query, type_filter=type_filter, tags=tags, limit=limit)

        sem_scored: list[tuple[Memory, float]] = []
        if semantic_weight > 0:
            qvec = self.embed.encode(query)
            if not isinstance(qvec, list):
                qvec = list(qvec)
            vec_hits = self.vindex.search(qvec, limit=limit)
            for vid, distance in vec_hits:
                m = self.db.get(vid)
                if m is None:
                    continue
                if type_filter and m.type.value != type_filter:
                    continue
                if tags and not all(t in m.tags for t in tags):
                    continue
                if user_id is not None and m.user_id != user_id:
                    continue
                score = 1.0 - (distance / 2.0)
                sem_scored.append((m, max(0.0, score)))

        seen: set[str] = set()
        merged: list[tuple[Memory, float]] = []

        score_map: dict[str, float] = {}
        for m, s in sem_scored:
            score_map[m.id] = max(score_map.get(m.id, 0.0), s)

        candidates = (
            sem_scored + [(m, 0.0) for m in kw_results]
            if semantic_weight >= 0.5
            else [(m, 0.0) for m in kw_results] + sem_scored
        )

        for m, s in candidates:
            if user_id is not None and m.user_id != user_id:
                continue
            if m.id not in seen:
                seen.add(m.id)
                merged.append((m, score_map.get(m.id, s)))
                if len(merged) >= limit:
                    break

        return merged
