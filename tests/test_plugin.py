"""Tests for plugin system: EventBus, PluginBase, PluginRegistry."""

from __future__ import annotations

from mneme.plugin.base import PluginBase
from mneme.plugin.bus import EventBus
from mneme.plugin.event import Event, EventType
from mneme.plugin.registry import PluginRegistry

# ── Test Plugin classes ──────────────────────────────────────────


class _TestPlugin(PluginBase):
    name = "test_plugin"

    def __init__(self, bus: EventBus) -> None:
        super().__init__(bus)
        self.events_received: list[Event] = []

    def on_load(self) -> None:
        self.bus.subscribe(EventType.AFTER_CREATE, self._on_event)

    def on_unload(self) -> None:
        self.bus.unsubscribe(EventType.AFTER_CREATE, self._on_event)

    def _on_event(self, event: Event) -> None:
        self.events_received.append(event)


class _MultiEventPlugin(PluginBase):
    name = "multi_event"

    def __init__(self, bus: EventBus) -> None:
        super().__init__(bus)
        self.events: list[EventType] = []

    def on_load(self) -> None:
        for et in (EventType.BEFORE_CREATE, EventType.AFTER_CREATE):
            self.bus.subscribe(et, self._on_event)

    def on_unload(self) -> None:
        for et in (EventType.BEFORE_CREATE, EventType.AFTER_CREATE):
            self.bus.unsubscribe(et, self._on_event)

    def _on_event(self, event: Event) -> None:
        self.events.append(event.type)


class _BrokenPlugin(PluginBase):
    name = "broken_plugin"

    def __init__(self, bus: EventBus) -> None:
        super().__init__(bus)
        self.called = False

    def on_load(self) -> None:
        self.bus.subscribe(EventType.AFTER_CREATE, self._on_event)

    def on_unload(self) -> None:
        self.bus.unsubscribe(EventType.AFTER_CREATE, self._on_event)

    def _on_event(self, event: Event) -> None:
        self.called = True
        raise RuntimeError("deliberate failure")


# ── Fixtures ──────────────────────────────────────────────────────


class TestEventBus:
    def test_subscribe_and_emit(self) -> None:
        bus = EventBus()
        received: list[Event] = []

        def handler(event: Event) -> None:
            received.append(event)

        bus.subscribe(EventType.AFTER_CREATE, handler)
        bus.emit(EventType.AFTER_CREATE, memory={"id": "123", "content": "test"})

        assert len(received) == 1
        assert received[0].type == EventType.AFTER_CREATE
        assert received[0].data["memory"] == {"id": "123", "content": "test"}

    def test_before_create_event_carries_memory_data(self) -> None:
        bus = EventBus()
        received_data: dict = {}

        def handler(event: Event) -> None:
            nonlocal received_data
            received_data = event.data

        bus.subscribe(EventType.BEFORE_CREATE, handler)
        bus.emit(EventType.BEFORE_CREATE, memory={"id": "abc", "content": "hello"})

        assert received_data["memory"]["id"] == "abc"
        assert received_data["memory"]["content"] == "hello"

    def test_after_create_event_fires(self) -> None:
        bus = EventBus()
        fired = False

        def handler(event: Event) -> None:
            nonlocal fired
            fired = True

        bus.subscribe(EventType.AFTER_CREATE, handler)
        bus.emit(EventType.AFTER_CREATE, memory={"id": "x"})

        assert fired

    def test_exception_isolation(self) -> None:
        bus = EventBus()

        def raising_handler(event: Event) -> None:
            raise RuntimeError("fail")

        received = False

        def good_handler(event: Event) -> None:
            nonlocal received
            received = True

        bus.subscribe(EventType.AFTER_CREATE, raising_handler)
        bus.subscribe(EventType.AFTER_CREATE, good_handler)
        bus.emit(EventType.AFTER_CREATE, memory={"id": "1"})

        assert received

    def test_before_search_carries_query_and_filters(self) -> None:
        bus = EventBus()
        received: dict = {}

        def handler(event: Event) -> None:
            nonlocal received
            received = event.data

        bus.subscribe(EventType.BEFORE_SEARCH, handler)
        bus.emit(
            EventType.BEFORE_SEARCH,
            query="hello",
            type_filter="fact",
            tags=["a", "b"],
        )

        assert received["query"] == "hello"
        assert received["type_filter"] == "fact"
        assert received["tags"] == ["a", "b"]

    def test_unsubscribe_stops_events(self) -> None:
        bus = EventBus()
        count = 0

        def handler(event: Event) -> None:
            nonlocal count
            count += 1

        bus.subscribe(EventType.AFTER_DELETE, handler)
        bus.emit(EventType.AFTER_DELETE, memory_id="x")
        assert count == 1

        bus.unsubscribe(EventType.AFTER_DELETE, handler)
        bus.emit(EventType.AFTER_DELETE, memory_id="y")
        assert count == 1

    def test_multiple_plugins_same_event(self) -> None:
        bus = EventBus()
        c1 = 0
        c2 = 0

        def h1(event: Event) -> None:
            nonlocal c1
            c1 += 1

        def h2(event: Event) -> None:
            nonlocal c2
            c2 += 1

        bus.subscribe(EventType.BEFORE_DELETE, h1)
        bus.subscribe(EventType.BEFORE_DELETE, h2)
        bus.emit(EventType.BEFORE_DELETE, memory_id="abc")

        assert c1 == 1
        assert c2 == 1

    def test_clear_removes_all_subscribers(self) -> None:
        bus = EventBus()
        count = 0

        def handler(event: Event) -> None:
            nonlocal count
            count += 1

        bus.subscribe(EventType.AFTER_CREATE, handler)
        bus.clear()
        bus.emit(EventType.AFTER_CREATE, memory={"id": "1"})

        assert count == 0

    def test_no_subscribers_no_error(self) -> None:
        bus = EventBus()
        bus.emit(EventType.AFTER_SLEEP, data="test")

    def test_event_timestamp_is_set(self) -> None:
        bus = EventBus()
        ts = None

        def handler(event: Event) -> None:
            nonlocal ts
            ts = event.timestamp

        bus.subscribe(EventType.AFTER_CREATE, handler)
        bus.emit(EventType.AFTER_CREATE, memory={"id": "1"})

        assert ts is not None


class TestPluginBase:
    def test_plugin_subclass_receives_events(self) -> None:
        bus = EventBus()
        plugin = _TestPlugin(bus)
        plugin.on_load()

        bus.emit(EventType.AFTER_CREATE, memory={"id": "123"})
        assert len(plugin.events_received) == 1
        assert plugin.events_received[0].data["memory"]["id"] == "123"

    def test_plugin_unload_stops_events(self) -> None:
        bus = EventBus()
        plugin = _TestPlugin(bus)
        plugin.on_load()

        bus.emit(EventType.AFTER_CREATE, memory={"id": "1"})
        assert len(plugin.events_received) == 1

        plugin.on_unload()
        bus.emit(EventType.AFTER_CREATE, memory={"id": "2"})
        assert len(plugin.events_received) == 1

    def test_multi_event_plugin(self) -> None:
        bus = EventBus()
        plugin = _MultiEventPlugin(bus)
        plugin.on_load()

        bus.emit(EventType.BEFORE_CREATE, memory={"id": "x"})
        bus.emit(EventType.AFTER_CREATE, memory={"id": "x"})

        assert len(plugin.events) == 2
        assert plugin.events[0] == EventType.BEFORE_CREATE
        assert plugin.events[1] == EventType.AFTER_CREATE

    def test_broken_plugin_exception_isolation(self) -> None:
        bus = EventBus()
        broken = _BrokenPlugin(bus)
        broken.on_load()

        good_received = False

        def good_handler(event: Event) -> None:
            nonlocal good_received
            good_received = True

        bus.subscribe(EventType.AFTER_CREATE, good_handler)

        bus.emit(EventType.AFTER_CREATE, memory={"id": "1"})

        assert broken.called
        assert good_received


class TestPluginRegistry:
    def test_load_and_list(self) -> None:
        bus = EventBus()
        registry = PluginRegistry(bus=bus)
        registry.load(_TestPlugin)

        plugins = registry.list()
        assert "test_plugin" in plugins
        assert plugins["test_plugin"]["loaded"]

    def test_unload_removes_from_registry(self) -> None:
        bus = EventBus()
        registry = PluginRegistry(bus=bus)
        registry.load(_TestPlugin)

        assert "test_plugin" in registry.list()

        registry.unload("test_plugin")
        assert "test_plugin" not in registry.list()

    def test_unload_nonexistent_raises(self) -> None:
        bus = EventBus()
        registry = PluginRegistry(bus=bus)

        try:
            registry.unload("nonexistent")
            raise AssertionError("Expected KeyError")
        except KeyError:
            pass

    def test_discover_builtin_plugins(self) -> None:
        bus = EventBus()
        registry = PluginRegistry(bus=bus)
        discovered = registry.discover()

        names = {cls.name for cls in discovered}
        assert "logger" in names
        assert "webhook" in names

    def test_load_builtin_plugin(self) -> None:
        bus = EventBus()
        registry = PluginRegistry(bus=bus)
        discovered = registry.discover()

        for cls in discovered:
            if cls.name == "logger":
                registry.load(cls)
                break

        assert "logger" in registry.list()

    def test_event_emitted_to_loaded_plugin(self) -> None:
        bus = EventBus()
        registry = PluginRegistry(bus=bus)

        registry.load(_TestPlugin)
        bus.emit(EventType.AFTER_CREATE, memory={"id": "ev1"})

        plugins = registry.list()
        assert "test_plugin" in plugins
