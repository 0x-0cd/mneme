from __future__ import annotations

import contextlib
from collections import defaultdict
from collections.abc import Callable
from typing import Any

from mneme.plugin.event import Event, EventType


class EventBus:
    _instance: EventBus | None = None

    def __init__(self) -> None:
        self._subscribers: dict[EventType, list[Callable[[Event], None]]] = defaultdict(list)

    @classmethod
    def get_instance(cls) -> EventBus:
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        cls._instance = None

    def subscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: EventType, callback: Callable[[Event], None]) -> None:
        subscribers = self._subscribers[event_type]
        if callback in subscribers:
            subscribers.remove(callback)

    def emit(self, event_type: EventType, **data: Any) -> None:
        event = Event(type=event_type, data=data)
        for callback in self._subscribers.get(event_type, []):
            with contextlib.suppress(Exception):
                callback(event)

    def clear(self) -> None:
        self._subscribers.clear()
