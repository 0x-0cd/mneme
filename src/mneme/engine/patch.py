"""Patch tracker — records non-incremental memory updates as structured patches.

Distinguishes incremental updates (tag/weight/metadata tweaks) from non-incremental
updates (content rewrite / type change) which are recorded as `MemoryPatch` rows.
"""

from __future__ import annotations

import uuid
from typing import Any

from mneme.engine.types import Memory, MemoryPatch
from mneme.storage.db import Database


class PatchTracker:
    """Tracks non-incremental memory updates and reconstructs version history."""

    def __init__(self, db: Database) -> None:
        self.db = db

    @staticmethod
    def should_patch(old: Memory, new: Memory) -> bool:
        """Return True when an update is non-incremental (content/type changed).

        Tag/weight/metadata-only edits are considered incremental and do not
        generate a patch.
        """
        if old.content != new.content:
            return True
        return str(old.type) != str(new.type)

    @staticmethod
    def _tag_str(memory: Memory) -> str:
        return ",".join(memory.tags)

    def create_patch(self, old: Memory, new: Memory, rationale: str = "") -> MemoryPatch:
        """Build and persist a patch capturing the (old -> new) non-incremental change.

        `version_to` is projected as `old.version + 1` mirroring the SQL trigger
        `version = version + 1` performed by `Database.update`.
        """
        patch = MemoryPatch(
            id=str(uuid.uuid4()),
            memory_id=old.id,
            version_from=old.version,
            version_to=old.version + 1,
            content_before=old.content,
            content_after=new.content,
            type_before=str(old.type),
            type_after=str(new.type),
            tags_before=self._tag_str(old),
            tags_after=self._tag_str(new),
            rationale=rationale,
        )
        self.db.insert_patch(patch)
        return patch

    def get_patches(self, memory_id: str) -> list[MemoryPatch]:
        return self.db.get_patches(memory_id)

    def get_patch_count(self, memory_id: str) -> int:
        return len(self.db.get_patches(memory_id))

    def get_history(self, memory_id: str) -> list[dict[str, Any]]:
        """Reconstruct version history for a memory.

        Returns chronological entries (oldest first). When patches exist, the first
        entry is the pre-patch snapshot extracted from the oldest patch's `_before`
        fields. Each subsequent patch produces an entry with its `_after` fields.
        If the current DB version exceeds the last patch's `version_to` (incremental
        updates after the latest non-incremental change), a final `current` entry is
        appended so callers can see the live state.
        """
        patches = self.db.get_patches(memory_id)
        current = self.db.get(memory_id)
        history: list[dict[str, Any]] = []

        if patches:
            oldest = patches[0]
            history.append(
                {
                    "version": oldest.version_from,
                    "content": oldest.content_before,
                    "type": oldest.type_before,
                    "tags": oldest.tags_before.split(",") if oldest.tags_before else [],
                    "source": "snapshot",
                    "created_at": None,
                }
            )
            for p in patches:
                history.append(
                    {
                        "version": p.version_to,
                        "content": p.content_after,
                        "type": p.type_after,
                        "tags": p.tags_after.split(",") if p.tags_after else [],
                        "source": "patch",
                        "patch_id": p.id,
                        "rationale": p.rationale,
                        "created_at": p.to_dict()["created_at"],
                    }
                )

        if current is not None:
            current_version = current.version
            last_patch_version = patches[-1].version_to if patches else 0
            if not patches or current_version > last_patch_version:
                history.append(
                    {
                        "version": current_version,
                        "content": current.content,
                        "type": str(current.type),
                        "tags": current.tags,
                        "user_id": current.user_id,
                        "weight": current.weight,
                        "source": "current",
                        "created_at": current.updated_at.isoformat(),
                    }
                )

        return history
