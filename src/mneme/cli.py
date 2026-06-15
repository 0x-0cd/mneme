"""Click CLI for Mneme."""

from __future__ import annotations

import contextlib
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


_DB_DEFAULT = os.environ.get("MNEME_DB_PATH", "memories.db")


@click.group()
def cli() -> None:
    """Mneme — Edge-first memory for AI agents."""


def _init_components(db_path: str) -> _Components:
    from mneme.embed.model import EmbeddingModel
    from mneme.engine.search import Searcher
    from mneme.engine.store import Store
    from mneme.plugin.bus import EventBus
    from mneme.storage.db import Database
    from mneme.storage.vector import VectorIndex

    db = Database(db_path)
    db.initialize()
    vindex = VectorIndex(db_path)
    vindex.initialize()
    embed = EmbeddingModel()
    event_bus = EventBus()
    store = Store(db, vindex, embed, event_bus=event_bus)
    searcher = Searcher(db, vindex, embed)
    return _Components(db=db, vindex=vindex, embed=embed, store=store, searcher=searcher)


@cli.command()
@click.option("--host", default="127.0.0.1", show_default=True)
@click.option("--port", default=8989, type=int, show_default=True)
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
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
@click.option("--user-id", "user_id", default="default", show_default=True)
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def add(content: str, type_: str, tags: str, user_id: str, db: str) -> None:
    """Store a new memory."""
    from mneme.engine.types import Memory, MemoryType

    _db, _vindex, _embed, store, _searcher = _init_components(db)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    memory = Memory(content=content, type=MemoryType(type_), tags=tag_list, user_id=user_id)
    store.store(memory)
    click.echo(memory.to_dict())


@cli.command()
@click.argument("query", required=False, default=None)
@click.option("--type", "type_", default=None, help="Filter by memory type")
@click.option("--tags", default=None, help="Comma-separated tags to filter")
@click.option("--limit", default=10, type=int, show_default=True)
@click.option("--user-id", "user_id", default=None)
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def search(
    query: str | None,
    type_: str | None,
    tags: str | None,
    limit: int,
    user_id: str | None,
    db: str,
) -> None:
    """Search memories."""
    _db, _vindex, _embed, _store, searcher = _init_components(db)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    results = searcher.search(
        query=query, type_filter=type_, tags=tag_list, limit=limit, user_id=user_id
    )
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
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
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
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
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
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
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
@click.option("--type", "type_", default=None, help="Filter by memory type")
@click.option("--tags", default=None, help="Comma-separated tags")
@click.option("--limit", default=20, type=int, show_default=True)
@click.option("--offset", default=0, type=int, show_default=True)
@click.option("--sort-by", default="created_at", show_default=True)
@click.option("--sort-order", default="desc", show_default=True)
@click.option("--include-deleted", is_flag=True, default=False)
@click.option("--user-id", "user_id", default=None)
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def list(
    type_: str | None,
    tags: str | None,
    limit: int,
    offset: int,
    sort_by: str,
    sort_order: str,
    include_deleted: bool,
    user_id: str | None,
    db: str,
) -> None:
    """List memories with pagination and filtering."""
    _db, _vindex, _embed, _store, _searcher = _init_components(db)
    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else None
    memories, total = _db.list_memories(
        offset=offset,
        limit=limit,
        type_filter=type_,
        tags=tag_list,
        sort_by=sort_by,
        sort_order=sort_order,
        include_deleted=include_deleted,
        user_id=user_id,
    )
    if not memories:
        console.print("[yellow]No memories found.[/yellow]")
        return
    table = Table(title=f"Memories ({offset + 1}-{offset + len(memories)} of {total})")
    table.add_column("ID", style="dim", no_wrap=True)
    table.add_column("Type")
    table.add_column("Content")
    table.add_column("Weight")
    table.add_column("Tags")
    table.add_column("User")
    table.add_column("Created")
    for m in memories:
        table.add_row(
            m.id[:8],
            m.type.value,
            m.content[:80] + ("..." if len(m.content) > 80 else ""),
            f"{m.weight:.2f}",
            ",".join(m.tags),
            m.user_id,
            m.created_at.strftime("%Y-%m-%d %H:%M"),
        )
    console.print(table)


@cli.command()
@click.argument("output", type=click.Path())
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def export(output: str, db: str) -> None:
    """Export all memories to a JSON file."""
    import json

    _db, _vindex, _embed, _store, _searcher = _init_components(db)
    data = _db.export_all()
    with open(output, "w") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    console.print(f"[green]Exported {len(data)} memories to {output}[/green]")


@cli.command("import")
@click.argument("input_path", type=click.Path(exists=True))
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def import_memories(input_path: str, db: str) -> None:
    """Import memories from a JSON file."""
    import json

    _db, _vindex, _embed, store, _searcher = _init_components(db)
    with open(input_path) as f:
        data = json.load(f)
    if not isinstance(data, list):
        console.print("[red]Error: JSON file must contain an array of memories.[/red]")
        sys.exit(1)
    count, imported = _db.import_memories(data)
    for mem in imported:
        content = mem.get("content", "")
        if content:
            embedding = store.embed.encode(content)
            if not isinstance(embedding, list):
                embedding = list(embedding)
            store.vindex.upsert(mem["id"], embedding)
    console.print(f"[green]Imported {count} new memories[/green]")


@cli.command()
@click.argument("memory_id")
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def restore(memory_id: str, db: str) -> None:
    """Restore a soft-deleted memory."""
    _db, _vindex, _embed, _store, _searcher = _init_components(db)
    if _db.restore(memory_id):
        console.print(f"Restored memory {memory_id}.")
    else:
        console.print(f"Memory {memory_id} not found or not deleted.", style="red")
        sys.exit(1)


@cli.command()
@click.option("--detail", is_flag=True, default=False)
@click.option("--user-id", "user_id", default=None)
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def stats(detail: bool, user_id: str | None, db: str) -> None:
    """Show memory statistics."""
    _db, _vindex, _embed, store, _searcher = _init_components(db)
    if detail:
        stats_data = _db.get_detailed_stats(user_id=user_id)
        stats_data["vector_count"] = _vindex.count()
        console.print("[bold]Memory Statistics[/bold]")
        console.print(f"  Total:          [bold]{stats_data['total']}[/bold]")
        console.print(f"  Total weight:   {stats_data['total_weight']:.2f}")
        console.print(f"  Deleted:        {stats_data['deleted_count']}")
        console.print(f"  Vector entries: {stats_data['vector_count']}")
        if stats_data["by_type"]:
            console.print("  [bold]By type:[/bold]")
            for t, c in sorted(stats_data["by_type"].items()):
                console.print(f"    {t}: {c}")
        if stats_data["by_tag"]:
            console.print("  [bold]By tag:[/bold]")
            for tag, c in stats_data["by_tag"].items():
                console.print(f"    {tag}: {c}")
    else:
        total = store.count(user_id=user_id)
        user_clause = (
            " AND COALESCE(json_extract(metadata, '$.user_id'), 'default') = ?" if user_id else ""
        )
        user_params = [user_id] if user_id else []
        rows = _db.cursor.execute(
            f"SELECT type, COUNT(*) AS cnt FROM memories"
            f" WHERE deleted_at IS NULL{user_clause} GROUP BY type",
            user_params,
        ).fetchall()
        by_type: dict[str, int] = {r["type"]: r["cnt"] for r in rows}
        console.print(f"Total memories: [bold]{total}[/bold]")
        for t, c in sorted(by_type.items()):
            console.print(f"  {t}: {c}")


@cli.command()
@click.option("--dry-run", is_flag=True, default=False)
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
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


# ── Plugin commands ──────────────────────────────────────────────


@cli.group()
def plugin() -> None:
    """Plugin management commands."""


@plugin.command("list")
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def plugin_list(db: str) -> None:
    """List loaded plugins."""
    _db, _vindex, _embed, _store, _searcher = _init_components(db)
    from mneme.plugin.bus import EventBus
    from mneme.plugin.registry import PluginRegistry

    bus = EventBus.get_instance()
    registry = PluginRegistry(bus=bus)

    # Discover and auto-load builtin plugins for listing
    builtin = registry.discover()
    for cls in builtin:
        with contextlib.suppress(Exception):
            registry.load(cls)

    plugins = registry.list()
    if not plugins:
        console.print("[yellow]No plugins loaded.[/yellow]")
        return
    table = Table(title="Loaded Plugins")
    table.add_column("Name", style="bold")
    table.add_column("Class")
    table.add_column("Loaded")
    for info in plugins.values():
        table.add_row(info["name"], info["class"], "yes" if info["loaded"] else "no")
    console.print(table)


@plugin.command("load")
@click.argument("path", type=click.Path(exists=True))
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def plugin_load(path: str, db: str) -> None:
    """Load a plugin from a directory or file path."""
    _db, _vindex, _embed, _store, _searcher = _init_components(db)
    from mneme.plugin.bus import EventBus
    from mneme.plugin.registry import PluginRegistry

    bus = EventBus.get_instance()
    registry = PluginRegistry(bus=bus)
    discovered = registry.discover(plugin_dir=path)
    if not discovered:
        console.print("[yellow]No plugin classes found in the specified path.[/yellow]")
        return
    for cls in discovered:
        registry.load(cls)
        console.print(f"[green]Loaded plugin: {cls.name}[/green]")


@plugin.command("unload")
@click.argument("name")
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def plugin_unload(name: str, db: str) -> None:
    """Unload a plugin by name."""
    _db, _vindex, _embed, _store, _searcher = _init_components(db)
    from mneme.plugin.bus import EventBus
    from mneme.plugin.registry import PluginRegistry

    bus = EventBus.get_instance()
    registry = PluginRegistry(bus=bus)

    # Auto-load builtin to ensure registry has them
    builtin = registry.discover()
    for cls in builtin:
        with contextlib.suppress(Exception):
            registry.load(cls)

    try:
        registry.unload(name)
        console.print(f"[green]Unloaded plugin: {name}[/green]")
    except KeyError:
        console.print(f"[red]Plugin '{name}' not found.[/red]")
        sys.exit(1)


# ── Users command ─────────────────────────────────────────────────


@cli.group()
def users() -> None:
    """User management commands."""


@users.command("list")
@click.option("--db", default=_DB_DEFAULT, show_default=True, envvar="MNEME_DB_PATH")
def users_list(db: str) -> None:
    """List users who have memories."""
    _db, _vindex, _embed, _store, _searcher = _init_components(db)
    distinct_users = _db.get_distinct_users()
    if not distinct_users:
        console.print("[yellow]No users found.[/yellow]")
        return
    table = Table(title="Users")
    table.add_column("User ID", style="bold")
    table.add_column("Memory Count")
    for uid in distinct_users:
        count = _db.count(user_id=uid)
        table.add_row(uid, str(count))
    console.print(table)
