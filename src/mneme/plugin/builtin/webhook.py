from __future__ import annotations

from dataclasses import dataclass

from mneme.plugin.base import PluginBase
from mneme.plugin.bus import EventBus
from mneme.plugin.event import Event, EventType


@dataclass
class WebhookConfig:
    url: str
    events: list[EventType] | None = None


class WebhookPlugin(PluginBase):
    name = "webhook"

    def __init__(self, bus: EventBus, config: WebhookConfig | None = None) -> None:
        super().__init__(bus)
        self.config = config or WebhookConfig(url="http://localhost:8989/webhook")
        self._handler = self._on_event

    def on_load(self) -> None:
        events = self.config.events or list(EventType)
        for event_type in events:
            self.bus.subscribe(event_type, self._handler)

    def on_unload(self) -> None:
        events = self.config.events or list(EventType)
        for event_type in events:
            self.bus.unsubscribe(event_type, self._handler)

    def _on_event(self, event: Event) -> None:
        import json
        import urllib.request

        payload = json.dumps(
            {
                "event_type": event.type.value,
                "data": event.data,
                "timestamp": event.timestamp.isoformat(),
            }
        ).encode("utf-8")
        try:
            req = urllib.request.Request(
                self.config.url,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            urllib.request.urlopen(req, timeout=5)
        except Exception:
            pass
