from __future__ import annotations

from mneme.plugin.base import PluginBase
from mneme.plugin.bus import EventBus
from mneme.plugin.event import Event, EventType


class LoggerPlugin(PluginBase):
    name = "logger"

    def __init__(self, bus: EventBus) -> None:
        super().__init__(bus)
        self._handler = self._on_event

    def on_load(self) -> None:
        for event_type in EventType:
            self.bus.subscribe(event_type, self._handler)

    def on_unload(self) -> None:
        for event_type in EventType:
            self.bus.unsubscribe(event_type, self._handler)

    def _on_event(self, event: Event) -> None:
        keys = ", ".join(sorted(event.data.keys()))
        print(f"LoggerPlugin: {event.type.value} event fired with {{{keys}}}")
