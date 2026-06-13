"""FastAPI application factory for Mneme."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI

from mneme.embed.model import EmbeddingModel
from mneme.engine.search import Searcher
from mneme.engine.store import Store
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


def create_app(
    db_path: str = "memories.db",
    db: Database | None = None,
    vindex: VectorIndex | None = None,
    embed: EmbeddingModel | None = None,
) -> FastAPI:
    _db = db or Database(db_path)
    if db is None:
        _db.initialize()

    _vindex = vindex or VectorIndex(db_path)
    if vindex is None:
        _vindex.initialize()

    _embed = embed or EmbeddingModel()
    store = Store(_db, _vindex, _embed)
    searcher = Searcher(_db, _vindex, _embed)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> Any:
        yield
        _db.close()
        _vindex.close()

    app = FastAPI(title="Mneme", lifespan=lifespan)
    app.state.store = store
    app.state.searcher = searcher

    from mneme.api.routes import router

    app.include_router(router)

    return app


app = create_app()
