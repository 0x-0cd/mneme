"""FastAPI application factory for Mneme."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from mneme.embed.model import EmbeddingModel
from mneme.engine.search import Searcher
from mneme.engine.sleep import SleepEngine
from mneme.engine.store import Store
from mneme.engine.weight import WeightCalibrator
from mneme.plugin.bus import EventBus
from mneme.plugin.registry import PluginRegistry
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


def create_app(
    db_path: str | None = None,
    db: Database | None = None,
    vindex: VectorIndex | None = None,
    embed: EmbeddingModel | None = None,
) -> FastAPI:
    resolved_path = db_path or os.environ.get("MNEME_DB_PATH", "memories.db")
    _db = db or Database(resolved_path)
    if db is None:
        _db.initialize()

    _vindex = vindex or VectorIndex(resolved_path)
    if vindex is None:
        _vindex.initialize()

    _embed = embed or EmbeddingModel()
    event_bus = EventBus()
    calibrator = WeightCalibrator(resolved_path)
    store = Store(_db, _vindex, _embed, event_bus=event_bus, calibrator=calibrator)
    searcher = Searcher(_db, _vindex, _embed)
    plugin_registry = PluginRegistry(bus=event_bus)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> Any:
        yield
        _db.close()
        _vindex.close()
        calibrator.close()

    app = FastAPI(title="Mneme", lifespan=lifespan)
    app.state.store = store
    app.state.searcher = searcher
    app.state.sleep_engine = SleepEngine(_db, _vindex, _embed, searcher, calibrator=calibrator)
    app.state.sleep_stats = {"last_sleep": None, "last_report": None}
    app.state.event_bus = event_bus
    app.state.plugin_registry = plugin_registry
    app.state.calibrator = calibrator

    # Auto-load builtin plugins
    builtin_plugins = plugin_registry.discover()
    for plugin_cls in builtin_plugins:
        plugin_registry.load(plugin_cls)

    from mneme.api.batch import router as batch_router
    from mneme.api.routes import router

    app.include_router(batch_router)
    app.include_router(router)

    return app


app = create_app()
