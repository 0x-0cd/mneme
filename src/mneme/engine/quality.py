"""Contradiction detection — quality module for Mneme memory system."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import Any

from mneme.embed.model import EmbeddingModel
from mneme.engine.search import Searcher
from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


class ContradictionType(StrEnum):
    DIRECT = "direct"
    TEMPORAL = "temporal"
    VALUE = "value"


@dataclass
class Contradiction:
    memory_a_id: str
    memory_b_id: str
    content_a: str
    content_b: str
    type: ContradictionType
    similarity: float
    score: float
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "memory_a_id": self.memory_a_id,
            "memory_b_id": self.memory_b_id,
            "content_a": self.content_a,
            "content_b": self.content_b,
            "type": self.type.value,
            "similarity": self.similarity,
            "score": self.score,
            "reason": self.reason,
        }


ANTONYM_PAIRS: list[tuple[str, str]] = [
    ("喜欢", "讨厌"),
    ("爱", "恨"),
    ("喜欢", "不喜欢"),
    ("喜爱", "厌恶"),
    ("like", "hate"),
    ("love", "hate"),
    ("like", "dislike"),
    ("good", "bad"),
    ("excellent", "terrible"),
    ("always", "never"),
    ("总是", "从不"),
    ("永远", "从不"),
    ("yes", "no"),
    ("true", "false"),
    ("agree", "disagree"),
    ("同意", "反对"),
    ("支持", "反对"),
    ("happy", "sad"),
    ("开心", "难过"),
    ("高兴", "悲伤"),
    ("好", "坏"),
    ("好", "差"),
    ("增加", "减少"),
    ("上升", "下降"),
    ("涨", "跌"),
    ("多", "少"),
    ("大", "小"),
    ("高", "低"),
    ("成功", "失败"),
    ("正确", "错误"),
    ("对", "错"),
    ("便宜", "贵"),
    ("容易", "困难"),
    ("简单", "复杂"),
    ("积极", "消极"),
    ("正面", "负面"),
]


class ContradictionDetector:
    def __init__(
        self,
        db: Database,
        vindex: VectorIndex,
        embed: EmbeddingModel,
        searcher: Searcher,
    ) -> None:
        self.db = db
        self.vindex = vindex
        self.embed = embed
        self.searcher = searcher

    def detect(self, memory_id: str | None = None) -> list[Contradiction]:
        if memory_id is not None:
            memory = self.db.get(memory_id)
            if memory is None:
                return []
            memories = [memory]
        else:
            memories = self.db.get_all()

        results: list[Contradiction] = []
        seen: set[tuple[str, str]] = set()

        for memory in memories:
            candidates = self._find_candidates(memory)
            for candidate, similarity in candidates:
                pair_key = tuple(sorted([memory.id, candidate.id]))
                if pair_key in seen:
                    continue
                seen.add(pair_key)

                contradiction = self._judge(memory, candidate, similarity)
                if contradiction is not None:
                    results.append(contradiction)

        results.sort(key=lambda c: c.score, reverse=True)
        return results

    def _find_candidates(self, memory: Memory) -> list[tuple[Memory, float]]:
        search_results = self.searcher.search(query=memory.content, limit=20)
        return [
            (m, s)
            for m, s in search_results
            if m.id != memory.id and s > 0.6
        ]

    def _judge(
        self, a: Memory, b: Memory, similarity: float
    ) -> Contradiction | None:
        # 1. Direct contradiction: antonym word pairs
        for word_a, word_b in ANTONYM_PAIRS:
            if word_a in a.content and word_b in b.content:
                ctype = ContradictionType.VALUE if a.type == MemoryType.PREFERENCE else ContradictionType.DIRECT
                return Contradiction(
                    memory_a_id=a.id,
                    memory_b_id=b.id,
                    content_a=a.content,
                    content_b=b.content,
                    type=ctype,
                    similarity=similarity,
                    score=min(similarity * 0.9, 1.0),
                    reason=f"反义词 '{word_a}' 与 '{word_b}' 直接对立",
                )
            if word_b in a.content and word_a in b.content:
                ctype = ContradictionType.VALUE if a.type == MemoryType.PREFERENCE else ContradictionType.DIRECT
                return Contradiction(
                    memory_a_id=a.id,
                    memory_b_id=b.id,
                    content_a=a.content,
                    content_b=b.content,
                    type=ctype,
                    similarity=similarity,
                    score=min(similarity * 0.9, 1.0),
                    reason=f"反义词 '{word_b}' 与 '{word_a}' 直接对立",
                )

        # 2. Temporal: same type + shared tags + overlapping content
        if a.type == b.type and a.tags and b.tags:
            shared = set(a.tags) & set(b.tags)
            if shared:
                overlap = self._char_overlap(a.content, b.content)
                if overlap > 0.3:
                    return Contradiction(
                        memory_a_id=a.id,
                        memory_b_id=b.id,
                        content_a=a.content,
                        content_b=b.content,
                        type=ContradictionType.TEMPORAL,
                        similarity=similarity,
                        score=min(similarity * 0.6, 1.0),
                        reason=f"相同标签 {sorted(shared)} 下可能存在不同属性值",
                    )

        # 3. Temporal (no tags): shared entity context
        if a.type == b.type:
            overlap = self._char_overlap(a.content, b.content)
            if 0.4 < overlap < 0.9:
                return Contradiction(
                    memory_a_id=a.id,
                    memory_b_id=b.id,
                    content_a=a.content,
                    content_b=b.content,
                    type=ContradictionType.TEMPORAL,
                    similarity=similarity,
                    score=min(similarity * 0.5, 1.0),
                    reason="同一实体可能存在不同状态",
                )

        return None

    @staticmethod
    def _char_overlap(a: str, b: str) -> float:
        chars_a = set(a)
        chars_b = set(b)
        if not chars_a or not chars_b:
            return 0.0
        intersection = chars_a & chars_b
        return len(intersection) / min(len(chars_a), len(chars_b))
