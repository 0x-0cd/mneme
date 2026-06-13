"""Memory type definitions and data model for Mneme."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class MemoryType(StrEnum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    CONVERSATION = "conversation"
    SKILL = "skill"


@dataclass
class Memory:
    content: str
    type: MemoryType = MemoryType.FACT
    weight: float = 1.0
    tags: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    version: int = 1
    superseded_by: str | None = None
    deleted_at: datetime | None = None

    def __post_init__(self) -> None:
        if not self.content or not self.content.strip():
            raise ValueError("content must not be empty")
        if self.weight <= 0:
            raise ValueError("weight must be > 0")
        if isinstance(self.type, str):
            self.type = MemoryType(self.type)

    def to_dict(self) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for f in self.__dataclass_fields__:
            val = getattr(self, f)
            if isinstance(val, datetime):
                result[f] = val.isoformat()
            elif isinstance(val, MemoryType):
                result[f] = val.value
            else:
                result[f] = val
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Memory:
        content = data.get("content")
        if not content or not content.strip():
            raise ValueError("content must not be empty")
        clean = dict(data)
        for key in ("created_at", "updated_at", "deleted_at"):
            if key in clean and isinstance(clean[key], str):
                clean[key] = datetime.fromisoformat(clean[key])
        return cls(**clean)
