"""Sleep computation engine — memory consolidation, decay, and forgetting."""

from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from mneme.embed.model import EmbeddingModel
from mneme.engine.search import Searcher
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex

if TYPE_CHECKING:
    from mneme.engine.weight import WeightCalibrator


@dataclass
class SleepReport:
    consolidated: int
    decayed: int
    forgotten: int
    total_before: int
    total_after: int
    duration_ms: int

    def to_dict(self) -> dict:
        return {
            "consolidated": self.consolidated,
            "decayed": self.decayed,
            "forgotten": self.forgotten,
            "total_before": self.total_before,
            "total_after": self.total_after,
            "duration_ms": self.duration_ms,
        }


class SleepEngine:
    def __init__(
        self,
        db: Database,
        vindex: VectorIndex,
        embed: EmbeddingModel,
        searcher: Searcher,
        calibrator: WeightCalibrator | None = None,
    ) -> None:
        self.db = db
        self.vindex = vindex
        self.embed = embed
        self.searcher = searcher
        self.calibrator = calibrator

    def consolidate(self, threshold: float = 0.92, dry_run: bool = False) -> int:
        memories = self.db.get_all()
        merged_ids: set[str] = set()
        pairs = 0

        for m in memories:
            if m.id in merged_ids:
                continue

            embedding = self.embed.encode(m.content)
            if not isinstance(embedding, list):
                embedding = list(embedding)

            neighbors = self.vindex.search(embedding, limit=20)

            for nid, distance in neighbors:
                if nid == m.id:
                    continue
                if nid in merged_ids:
                    continue

                similarity = 1.0 - distance
                if similarity <= threshold:
                    break

                n_memory = self.db.get(nid)
                if n_memory is None:
                    continue
                if n_memory.type != m.type:
                    continue

                if m.created_at <= n_memory.created_at:
                    survivor, replaced = m, n_memory
                else:
                    survivor, replaced = n_memory, m
                    merged_ids.add(m.id)

                if len(replaced.content) > len(survivor.content):
                    survivor.content = replaced.content
                survivor.tags = list(set(survivor.tags) | set(replaced.tags))
                survivor.weight = min(survivor.weight + replaced.weight, 2.0)
                survivor.metadata = {**survivor.metadata, **replaced.metadata}

                if not dry_run:
                    replaced.superseded_by = survivor.id
                    self.db.update(replaced)
                    self.db.soft_delete(replaced.id)
                    self.vindex.delete(replaced.id)

                    new_embedding = self.embed.encode(survivor.content)
                    if not isinstance(new_embedding, list):
                        new_embedding = list(new_embedding)
                    self.db.update(survivor)
                    self.vindex.upsert(survivor.id, new_embedding)

                merged_ids.add(replaced.id)
                pairs += 1

                if m.id in merged_ids:
                    break

        return pairs

    def decay(
        self,
        halflife_days: float = 30.0,
        forget_threshold: float = 0.05,
        dry_run: bool = False,
        now: datetime | None = None,
    ) -> tuple[int, int]:
        decayed = 0
        forgotten = 0
        now = now or datetime.now(UTC)

        for m in self.db.get_all():
            days = (now - m.updated_at).days
            if days <= 0:
                continue

            new_weight = m.weight * (0.5 ** (days / halflife_days))

            if new_weight < m.weight:
                decayed += 1

            if new_weight < forget_threshold:
                forgotten += 1
                if not dry_run:
                    m.weight = max(new_weight, 0.0)
                    self.db.update(m)
            elif new_weight < m.weight and not dry_run:
                m.weight = max(new_weight, 0.0)
                self.db.update(m)

        return decayed, forgotten

    def run_cycle(self, dry_run: bool = False, now: datetime | None = None) -> SleepReport:
        total_before = self.db.count()
        t0 = time.time()
        consolidated = self.consolidate(dry_run=dry_run)
        decayed, forgotten = self.decay(dry_run=dry_run, now=now)

        if self.calibrator and not dry_run:
            self.calibrator.decay_calibrations()

        total_after = self.db.count() if not dry_run else max(0, total_before - consolidated)
        duration_ms = int((time.time() - t0) * 1000)

        return SleepReport(
            consolidated=consolidated,
            decayed=decayed,
            forgotten=forgotten,
            total_before=total_before,
            total_after=total_after,
            duration_ms=duration_ms,
        )
