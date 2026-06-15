from __future__ import annotations

import importlib
import pkgutil
import sys
from pathlib import Path
from typing import Any

from mneme.plugin.base import PluginBase
from mneme.plugin.bus import EventBus


class PluginRegistry:
    def __init__(self, bus: EventBus | None = None) -> None:
        self._bus = bus or EventBus.get_instance()
        self._plugins: dict[str, PluginBase] = {}

    def load(self, plugin_cls: type[PluginBase]) -> PluginBase:
        instance = plugin_cls(self._bus)
        instance.on_load()
        self._plugins[plugin_cls.name] = instance
        return instance

    def unload(self, name: str) -> None:
        if name not in self._plugins:
            raise KeyError(f"Plugin '{name}' is not loaded")
        plugin = self._plugins[name]
        plugin.on_unload()
        del self._plugins[name]

    def list(self) -> dict[str, dict[str, Any]]:
        return {
            name: {"name": name, "loaded": True, "class": type(plugin).__name__}
            for name, plugin in self._plugins.items()
        }

    def discover(self, plugin_dir: str | None = None) -> list[type[PluginBase]]:
        discovered: list[type[PluginBase]] = []
        paths: list[str] = []

        if plugin_dir:
            paths.append(plugin_dir)

        builtin_path = Path(__file__).parent / "builtin"
        if builtin_path.is_dir():
            paths.append(str(builtin_path))

        for path in paths:
            p = Path(path)
            if not p.is_dir():
                continue
            str(p.parent) if p.parent != Path(".") else str(p)
            for finder, name, _is_pkg in pkgutil.iter_modules([str(p)]):
                try:
                    spec = finder.find_spec(name)  # type: ignore[union-attr]
                    if spec is None:
                        continue
                    module = importlib.util.module_from_spec(spec)
                    # Register in sys.modules so @dataclass etc. can resolve __module__
                    sys.modules[name] = module
                    spec.loader.exec_module(module)  # type: ignore[union-attr]
                    for attr_name in dir(module):
                        attr = getattr(module, attr_name)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, PluginBase)
                            and attr is not PluginBase
                        ):
                            discovered.append(attr)
                except Exception:
                    pass
        return discovered
