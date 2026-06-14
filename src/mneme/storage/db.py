"""SQLite storage for Mneme memories."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from mneme.engine.types import Memory


class Database:
    def __init__(self, db_path: str = "memories.db") -> None:
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def __del__(self) -> None:
        self.close()

    def initialize(self) -> None:
        if self.db_path != ":memory:":
            self.cursor.execute("PRAGMA journal_mode=WAL")
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id          TEXT PRIMARY KEY,
                type        TEXT NOT NULL DEFAULT "fact",
                content     TEXT NOT NULL,
                weight      REAL NOT NULL DEFAULT 1.0,
                metadata    TEXT NOT NULL DEFAULT "{}",
                tags        TEXT NOT NULL DEFAULT "",
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                version     INTEGER NOT NULL DEFAULT 1,
                superseded_by TEXT,
                deleted_at  TEXT
            )
        """)
        self.cursor.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)")
        self.cursor.execute(
            "CREATE INDEX IF NOT EXISTS idx_memories_deleted ON memories(deleted_at)"
        )
        self.conn.commit()

    def close(self) -> None:
        if hasattr(self, "conn") and self.conn:
            self.conn.close()
            self.conn = None  # type: ignore[assignment]

    @staticmethod
    def _memory_to_row(memory: Memory) -> dict[str, Any]:
        d = memory.to_dict()
        d["tags"] = ",".join(d["tags"])
        d["metadata"] = json.dumps(d["metadata"], ensure_ascii=False)
        return d

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> Memory:
        d: dict[str, Any] = dict(row)
        if d.get("tags") is not None:
            d["tags"] = d["tags"].split(",") if d["tags"] else []
        if d.get("metadata") is not None:
            d["metadata"] = json.loads(d["metadata"])
        return Memory.from_dict(d)

    def insert(self, memory: Memory) -> None:
        row = self._memory_to_row(memory)
        self.cursor.execute(
            """INSERT INTO memories
               (id, type, content, weight, metadata, tags,
                created_at, updated_at, version, superseded_by, deleted_at)
               VALUES (:id, :type, :content, :weight, :metadata, :tags,
                       :created_at, :updated_at, :version, :superseded_by, :deleted_at)""",
            row,
        )
        self.conn.commit()

    def get(self, memory_id: str) -> Memory | None:
        row = self.cursor.execute(
            "SELECT * FROM memories WHERE id = ? AND deleted_at IS NULL",
            (memory_id,),
        ).fetchone()
        return self._row_to_memory(row) if row else None

    def search(
        self,
        query: str | None = None,
        type_filter: str | None = None,
        tags: list[str] | None = None,
        limit: int = 10,
    ) -> list[Memory]:
        sql = "SELECT * FROM memories WHERE deleted_at IS NULL"
        params: list[Any] = []

        if query is not None:
            sql += " AND content LIKE ?"
            params.append(f"%{query}%")

        if type_filter is not None:
            sql += " AND type = ?"
            params.append(type_filter)

        if tags:
            for tag in tags:
                sql += " AND (',' || tags || ',') LIKE ?"
                params.append(f"%,{tag},%")

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self.cursor.execute(sql, params).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def update(self, memory: Memory) -> None:
        row = self._memory_to_row(memory)
        now = datetime.now(UTC).isoformat()
        self.cursor.execute(
            """UPDATE memories
               SET content = ?, type = ?, weight = ?,
                   metadata = ?, tags = ?,
                   updated_at = ?, version = version + 1,
                   superseded_by = ?
               WHERE id = ? AND deleted_at IS NULL""",
            (
                row["content"],
                row["type"],
                row["weight"],
                row["metadata"],
                row["tags"],
                now,
                row["superseded_by"],
                memory.id,
            ),
        )
        self.conn.commit()

    def soft_delete(self, memory_id: str) -> None:
        now = datetime.now(UTC).isoformat()
        self.cursor.execute(
            "UPDATE memories SET deleted_at = ? WHERE id = ? AND deleted_at IS NULL",
            (now, memory_id),
        )
        self.conn.commit()

    def clear(self) -> None:
        self.cursor.execute("DELETE FROM memories")
        self.conn.commit()

    def count(self) -> int:
        row = self.cursor.execute(
            "SELECT COUNT(*) AS cnt FROM memories WHERE deleted_at IS NULL"
        ).fetchone()
        return row["cnt"] if row else 0

    def get_all(self) -> list[Memory]:
        rows = self.cursor.execute(
            "SELECT * FROM memories WHERE deleted_at IS NULL ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]
