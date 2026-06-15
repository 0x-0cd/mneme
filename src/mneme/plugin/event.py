from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class EventType(StrEnum):
    BEFORE_CREATE = "before_create"
    AFTER_CREATE = "after_create"
    BEFORE_SEARCH = "before_search"
    AFTER_SEARCH = "after_search"
    BEFORE_DELETE = "before_delete"
    AFTER_DELETE = "after_delete"
    BEFORE_UPDATE = "before_update"
    AFTER_UPDATE = "after_update"
    BEFORE_CONSOLIDATE = "before_consolidate"
    AFTER_SLEEP = "after_sleep"


@dataclass
class Event:
    type: EventType
    data: dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(UTC))
