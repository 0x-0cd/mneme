"""Click CLI for Mneme."""

from __future__ import annotations

import os
import sys
from typing import Any, NamedTuple

import click
from rich.console import Console
from rich.table import Table

console = Console()


class _Components(NamedTuple):
    db: Any
    vindex: Any
    embed: Any
    store: Any
    searcher: Any


@click.group()
def cli() -> None:
    """Mneme — Edge-first memory for AI agents."""


def _init_components(db_path: str) -> _Components:
    from mneme.embed.model import EmbeddingModel
    from mneme.engine.search import Searcher
    from mneme.engine.store import Store
    from mneme.storage.db import Database
    from mneme.storage.vector import VectorIndex

    db = Database(db_path)
    db.initialize()
    vindex = VectorIndex(db_path)
    vindex.initialize()
    embed = EmbeddingModel()
    store = Store(db, vindex, embed)
    searcher = Searcher(db, vindex, embed)
    return _Components(db=db, vindex=vindex, embed=embed, store=store, searcher=searcher)


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8989, type=int, show_default=True)
@click.option("--db", default="memories.db", show_default=True, envvar="MNEME_DB_PATH")
@click.option("--reload", is_flag=True, default=False)
def serve(host: str, port: int, db: str, reload: bool) -> None:
    """Start the Mneme HTTP server."""
    os.environ["MNEME_DB_PATH"] = db
    import uvicorn

    uvicorn.run("mneme.api.app:app", host=host, port=port, reload=reload)


@cli.command()
@click.argument("content")
@click.option("--type", "type_", default="fact", show_default=True)
@click.option("--tags", default="", help="Comma-separated tags")
@click.option("--db", default="memories.db", show_default=True, envvar="MNEME_DB_PATH")
def add(content: str, type_: str, tags: str, db: str) -> None:
    """Store a new memory."""
    from mneme.engine.types import Memory, MemoryType

    _db, _vindex, _embed, store, _searcher = _init_components(db)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    memory = Memory(content=content, type=MemoryType(type_), tags=tag_list)
    store.store(memory)
    click.echo(memory.to_dict())


@cli.command()
@click.argument("query", required=False, default=None)
@click.option("--type", "type_", default=None, help="Filter by memory type")
@click.option("--tags", default=None, help="Comma-separated tags to filter")
@click.option("--limit", default=10, type=int, show_default=True)
@click.option("--db", default="memories.db", show_default=True, envvar="MNEME_DB_PATH")
def search(
    query: str | None,
    type_: str | None,
    tags: str | None,
    limit: int,
    db: str,
) -> None:
    """Search memories."""
    _db, _vindex, _embed, _store, searcher = _init_components(db)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    results = searcher.search(query=query, type_filter=type_, tags=tag_list, limit=limit)
    if not results:
        console.print("[yellow]No memories found.[/yellow]")
        return
    table = Table(title=f"Memories ({len(results)})")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Type")
    table.add_column("Content")
    table.add_column("Score")
    table.add_column("Tags")
    table.add_column("Created")
    for m, s in results:
        table.add_row(
            m.id[:8],
            m.type.value,
            m.content[:80] + ("..." if len(m.content) > 80 else ""),
            f"{s:.2f}",
            ",".join(m.tags),
            m.created_at.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@cli.command()
@click.argument("memory_id")
@click.option("--db", default="memories.db", show_default=True, envvar="MNEME_DB_PATH")
def delete(memory_id: str, db: str) -> None:
    """Delete a memory by ID."""
    _db, _vindex, _embed, store, _searcher = _init_components(db)
    existing = store.get(memory_id)
    if not existing:
        click.echo(f"Memory {memory_id} not found.", err=True)
        sys.exit(1)
    store.delete(memory_id)
    click.echo(f"Deleted memory {memory_id}.")


@cli.command()
@click.option("--db", default="memories.db", show_default=True, envvar="MNEME_DB_PATH")
@click.option("--force", is_flag=True, default=False)
def clear(db: str, force: bool) -> None:
    """Delete all memories."""
    if not force:
        click.confirm("Delete all memories?", abort=True)
    _db, _vindex, _embed, store, _searcher = _init_components(db)
    store.clear()
    click.echo("All memories cleared.")


@cli.command()
@click.option("--id", "memory_id", default=None, help="检测特定记忆")
@click.option("--db", default="memories.db", show_default=True, envvar="MNEME_DB_PATH")
def detect(memory_id: str | None, db: str) -> None:
    """检测记忆矛盾."""
    from mneme.engine.quality import ContradictionDetector

    db_obj, vindex, embed, store, searcher = _init_components(db)
    detector = ContradictionDetector(db_obj, vindex, embed, searcher)
    contradictions = detector.detect(memory_id=memory_id)

    if not contradictions:
        console.print("[green]No contradictions found.[/green]")
        return

    table = Table(title=f"Contradictions ({len(contradictions)})")
    table.add_column("Score", style="bold")
    table.add_column("Type")
    table.add_column("Content A")
    table.add_column("Content B")
    table.add_column("Reason")
    for c in contradictions:
        table.add_row(
            f"{c.score:.2f}",
            c.type.value,
            c.content_a[:60] + ("..." if len(c.content_a) > 60 else ""),
            c.content_b[:60] + ("..." if len(c.content_b) > 60 else ""),
            c.reason,
        )
    console.print(table)


@cli.command()
@click.option("--db", default="memories.db", show_default=True, envvar="MNEME_DB_PATH")
def stats(db: str) -> None:
    """Show memory statistics."""
    _db, _vindex, _embed, store, _searcher = _init_components(db)
    total = store.count()
    rows = _db.cursor.execute(
        "SELECT type, COUNT(*) AS cnt FROM memories WHERE deleted_at IS NULL GROUP BY type"
    ).fetchall()
    by_type: dict[str, int] = {r["type"]: r["cnt"] for r in rows}
    console.print(f"Total memories: [bold]{total}[/bold]")
    for t, c in sorted(by_type.items()):
        console.print(f"  {t}: {c}")


@cli.command()
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--db", default="memories.db", show_default=True, envvar="MNEME_DB_PATH")
def sleep(dry_run: bool, db: str) -> None:
    """Run memory consolidation and decay cycle."""
    from mneme.engine.sleep import SleepEngine

    db_obj, vindex, embed, store, searcher = _init_components(db)
    engine = SleepEngine(db_obj, vindex, embed, searcher)
    report = engine.run_cycle(dry_run=dry_run)

    prefix = "[dry-run] " if dry_run else ""
    console.print(f"[bold]{prefix}Sleep cycle complete[/bold]")
    console.print(f"  Consolidations: {report.consolidated}")
    console.print(f"  Decayed:        {report.decayed}")
    console.print(f"  Below threshold:{report.forgotten}")
    console.print(f"  Total before:   {report.total_before}")
    console.print(f"  Total after:    {report.total_after}")
    console.print(f"  Duration:       {report.duration_ms}ms")
