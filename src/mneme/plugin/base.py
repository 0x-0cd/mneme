from __future__ import annotations

from abc import ABC, abstractmethod

from mneme.plugin.bus import EventBus


class PluginBase(ABC):
    name: str

    def __init__(self, bus: EventBus) -> None:
        self.bus = bus

    @abstractmethod
    def on_load(self) -> None: ...

    @abstractmethod
    def on_unload(self) -> None: ...
