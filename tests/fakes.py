"""Shared fake implementations for Mneme tests."""

from __future__ import annotations

import hashlib
import math
import random


class FakeVectorIndex:
    """In-memory vector index for testing."""

    def __init__(self) -> None:
        self.vectors: dict[str, list[float]] = {}

    def initialize(self) -> None:
        pass

    def upsert(self, memory_id: str, embedding: list[float]) -> None:
        self.vectors[memory_id] = embedding

    def search(
        self, query_vector: list[float], limit: int = 20
    ) -> list[tuple[str, float]]:
        scored: list[tuple[str, float]] = []
        for mid, vec in self.vectors.items():
            dist = self._cosine_distance(query_vector, vec)
            scored.append((mid, dist))
        scored.sort(key=lambda x: x[1])
        return scored[:limit]

    @staticmethod
    def _cosine_distance(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b))
        na = math.sqrt(sum(x * x for x in a))
        nb = math.sqrt(sum(x * x for x in b))
        if na == 0 or nb == 0:
            return 1.0
        return 1.0 - dot / (na * nb)

    def delete(self, memory_id: str) -> None:
        self.vectors.pop(memory_id, None)

    def clear(self) -> None:
        self.vectors.clear()

    def count(self) -> int:
        return len(self.vectors)

    def close(self) -> None:
        pass


class FakeEmbeddingModel:
    """Deterministic fake embedding model for testing."""

    def __init__(self) -> None:
        self.encoded: list[str] = []

    def encode(self, text: str | list[str]) -> list[float] | list[list[float]]:
        if isinstance(text, str):
            self.encoded.append(text)
            return self._vec(text)
        for t in text:
            self.encoded.append(t)
        return [self._vec(t) for t in text]

    @staticmethod
    def _vec(text: str) -> list[float]:
        """Deterministic bag-of-chars embedding.

        Texts sharing more characters produce more similar vectors,
        mimicking real embedding behavior for test purposes.
        """
        # Use character bigrams to capture content similarity
        chars = text.lower()
        vec = [0.0] * 384
        # Simple char-based embedding: position = char code, value = frequency
        for i, c in enumerate(chars):
            idx = (ord(c) * 7 + i * 13) % 384
            vec[idx] += 1.0
        # Normalize
        norm = math.sqrt(sum(v * v for v in vec))
        if norm > 0:
            vec = [v / norm for v in vec]
        return vec
