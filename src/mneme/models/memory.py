from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class MemoryCreate(BaseModel):
    content: str = Field(min_length=1)
    type: str = "fact"
    tags: list[str] = Field(default_factory=list)
    weight: float = 1.0
    metadata: dict[str, Any] = Field(default_factory=dict)
    user_id: str = "default"


class MemoryUpdate(BaseModel):
    content: str | None = None
    type: str | None = None
    tags: list[str] | None = None
    weight: float | None = None
    metadata: dict[str, Any] | None = None
    user_id: str | None = None
