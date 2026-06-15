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
        if hasattr(self, "conn") and self.conn is not None:
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
        meta = dict(d.get("metadata", {}))
        meta["user_id"] = d.get("user_id", "default")
        d["metadata"] = json.dumps(meta, ensure_ascii=False)
        return d

    @staticmethod
    def _row_to_memory(row: sqlite3.Row) -> Memory:
        d: dict[str, Any] = dict(row)
        if d.get("tags") is not None:
            d["tags"] = d["tags"].split(",") if d["tags"] else []
        if d.get("metadata") is not None:
            d["metadata"] = json.loads(d["metadata"])
        meta = d.get("metadata")
        if isinstance(meta, dict):
            d["user_id"] = meta.pop("user_id", "default")
        else:
            d["user_id"] = "default"
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

    def count(self, user_id: str | None = None) -> int:
        if user_id is not None:
            row = self.cursor.execute(
                "SELECT COUNT(*) AS cnt FROM memories"
                " WHERE deleted_at IS NULL"
                " AND COALESCE(json_extract(metadata, '$.user_id'), 'default') = ?",
                (user_id,),
            ).fetchone()
        else:
            row = self.cursor.execute(
                "SELECT COUNT(*) AS cnt FROM memories WHERE deleted_at IS NULL"
            ).fetchone()
        return row["cnt"] if row else 0

    def get_all(self, user_id: str | None = None) -> list[Memory]:
        if user_id is not None:
            rows = self.cursor.execute(
                "SELECT * FROM memories WHERE deleted_at IS NULL"
                " AND COALESCE(json_extract(metadata, '$.user_id'), 'default') = ?"
                " ORDER BY created_at DESC",
                (user_id,),
            ).fetchall()
        else:
            rows = self.cursor.execute(
                "SELECT * FROM memories WHERE deleted_at IS NULL ORDER BY created_at DESC"
            ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def get_distinct_users(self) -> list[str]:
        rows = self.cursor.execute(
            "SELECT DISTINCT COALESCE(json_extract(metadata, '$.user_id'), 'default') AS user_id"
            " FROM memories WHERE deleted_at IS NULL"
        ).fetchall()
        return sorted(r["user_id"] for r in rows if r["user_id"])

    def _build_filter_where(
        self,
        type_filter: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        weight_min: float | None = None,
        weight_max: float | None = None,
        include_deleted: bool = False,
        user_id: str | None = None,
    ) -> tuple[str, list[Any]]:
        conditions: list[str] = []
        params: list[Any] = []

        if not include_deleted:
            conditions.append("deleted_at IS NULL")

        if user_id is not None:
            conditions.append("COALESCE(json_extract(metadata, '$.user_id'), 'default') = ?")
            params.append(user_id)

        if type_filter is not None:
            conditions.append("type = ?")
            params.append(type_filter)

        if tags:
            for tag in tags:
                conditions.append("(',' || tags || ',') LIKE ?")
                params.append(f"%,{tag},%")

        if date_from is not None:
            conditions.append("created_at >= ?")
            params.append(date_from)

        if date_to is not None:
            conditions.append("created_at <= ?")
            params.append(date_to)

        if weight_min is not None:
            conditions.append("weight >= ?")
            params.append(weight_min)

        if weight_max is not None:
            conditions.append("weight <= ?")
            params.append(weight_max)

        where = " AND ".join(conditions) if conditions else "1=1"
        return where, params

    def list_memories(
        self,
        offset: int = 0,
        limit: int = 20,
        type_filter: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        weight_min: float | None = None,
        weight_max: float | None = None,
        sort_by: str = "created_at",
        sort_order: str = "desc",
        include_deleted: bool = False,
        user_id: str | None = None,
    ) -> tuple[list[Memory], int]:
        """Return (memories, total_count) with pagination and multi-filter support."""
        valid_sort_columns = {"created_at", "updated_at", "weight"}
        if sort_by not in valid_sort_columns:
            raise ValueError(f"Invalid sort_by: {sort_by}. Must be one of {valid_sort_columns}")
        if sort_order not in ("asc", "desc"):
            raise ValueError("sort_order must be 'asc' or 'desc'")

        where_sql, params = self._build_filter_where(
            type_filter=type_filter,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
            weight_min=weight_min,
            weight_max=weight_max,
            include_deleted=include_deleted,
            user_id=user_id,
        )

        count_sql = f"SELECT COUNT(*) AS cnt FROM memories WHERE {where_sql}"
        count_row = self.cursor.execute(count_sql, params).fetchone()
        total = count_row["cnt"] if count_row else 0

        data_sql = (
            f"SELECT * FROM memories WHERE {where_sql}"
            f" ORDER BY {sort_by} {sort_order}"
            f" LIMIT ? OFFSET ?"
        )
        rows = self.cursor.execute(data_sql, params + [limit, offset]).fetchall()
        memories = [self._row_to_memory(r) for r in rows]
        return memories, total

    def batch_delete(
        self,
        type_filter: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        weight_min: float | None = None,
        weight_max: float | None = None,
        user_id: str | None = None,
    ) -> tuple[int, list[str]]:
        """Soft-delete memories matching filters. Returns (deleted_count, deleted_ids)."""
        where_sql, params = self._build_filter_where(
            type_filter=type_filter,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
            weight_min=weight_min,
            weight_max=weight_max,
            include_deleted=False,
            user_id=user_id,
        )

        rows = self.cursor.execute(f"SELECT id FROM memories WHERE {where_sql}", params).fetchall()
        ids = [r["id"] for r in rows]

        if not ids:
            return 0, []

        now = datetime.now(UTC).isoformat()
        placeholders = ",".join(["?"] * len(ids))
        self.cursor.execute(
            f"UPDATE memories SET deleted_at = ? WHERE id IN ({placeholders})",
            [now] + ids,
        )
        self.conn.commit()
        return len(ids), ids

    def batch_update(
        self,
        updates: dict[str, Any],
        type_filter: str | None = None,
        tags: list[str] | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        weight_min: float | None = None,
        weight_max: float | None = None,
        user_id: str | None = None,
    ) -> int:
        """Update memories matching filters. Returns updated count."""
        where_sql, params = self._build_filter_where(
            type_filter=type_filter,
            tags=tags,
            date_from=date_from,
            date_to=date_to,
            weight_min=weight_min,
            weight_max=weight_max,
            include_deleted=False,
            user_id=user_id,
        )

        # Determine which matching IDs to update
        rows = self.cursor.execute(f"SELECT id FROM memories WHERE {where_sql}", params).fetchall()
        ids = [r["id"] for r in rows]

        if not ids:
            return 0

        set_parts: list[str] = []
        set_params: list[Any] = []
        now = datetime.now(UTC).isoformat()

        if "tags" in updates:
            set_parts.append("tags = ?")
            set_params.append(",".join(updates["tags"]))

        if "weight" in updates:
            set_parts.append("weight = ?")
            set_params.append(updates["weight"])

        if "type" in updates:
            set_parts.append("type = ?")
            set_params.append(updates["type"])

        if not set_parts:
            return 0

        set_parts.append("updated_at = ?")
        set_params.append(now)

        placeholders = ",".join(["?"] * len(ids))
        self.cursor.execute(
            f"UPDATE memories SET {', '.join(set_parts)} WHERE id IN ({placeholders})",
            set_params + ids,
        )
        self.conn.commit()
        return len(ids)

    def restore(self, memory_id: str) -> bool:
        """Restore a soft-deleted memory. Returns True if restored."""
        self.cursor.execute(
            "UPDATE memories SET deleted_at = NULL WHERE id = ? AND deleted_at IS NOT NULL",
            (memory_id,),
        )
        self.conn.commit()
        return self.cursor.rowcount > 0

    def get_deleted(self, limit: int = 50) -> list[Memory]:
        """Get soft-deleted memories."""
        rows = self.cursor.execute(
            "SELECT * FROM memories WHERE deleted_at IS NOT NULL ORDER BY deleted_at DESC LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def export_all(self) -> list[dict[str, Any]]:
        """Export all memories (including soft-deleted) as JSON-compatible dicts."""
        rows = self.cursor.execute("SELECT * FROM memories").fetchall()
        return [self._row_to_memory(r).to_dict() for r in rows]

    def import_memories(
        self, memories_data: list[dict[str, Any]]
    ) -> tuple[int, list[dict[str, Any]]]:
        """Import memories from JSON-compatible dicts. Returns (count, imported_data)."""
        count = 0
        imported: list[dict[str, Any]] = []
        for data in memories_data:
            row = dict(data)
            if isinstance(row.get("tags"), list):
                row["tags"] = ",".join(row["tags"])
            if isinstance(row.get("metadata"), dict):
                row["metadata"] = json.dumps(row["metadata"], ensure_ascii=False)

            try:
                self.cursor.execute(
                    """INSERT OR IGNORE INTO memories
                       (id, type, content, weight, metadata, tags,
                        created_at, updated_at, version, superseded_by, deleted_at)
                       VALUES (:id, :type, :content, :weight, :metadata, :tags,
                               :created_at, :updated_at, :version, :superseded_by, :deleted_at)""",
                    row,
                )
                if self.cursor.rowcount > 0:
                    count += 1
                    imported.append(data)
            except Exception:
                continue
        self.conn.commit()
        return count, imported

    def get_detailed_stats(self, user_id: str | None = None) -> dict[str, Any]:
        """Return detailed stats: total, by_type, by_tag, total_weight, deleted_count."""
        user_clause = (
            " AND COALESCE(json_extract(metadata, '$.user_id'), 'default') = ?" if user_id else ""
        )
        user_params = [user_id] if user_id else []

        total_active = self.count(user_id=user_id)

        by_type_rows = self.cursor.execute(
            f"SELECT type, COUNT(*) AS cnt FROM memories"
            f" WHERE deleted_at IS NULL{user_clause} GROUP BY type",
            user_params,
        ).fetchall()
        by_type: dict[str, int] = {r["type"]: r["cnt"] for r in by_type_rows}

        weight_row = self.cursor.execute(
            f"SELECT COALESCE(SUM(weight), 0.0) AS total_weight"
            f" FROM memories WHERE deleted_at IS NULL{user_clause}",
            user_params,
        ).fetchone()
        total_weight = weight_row["total_weight"] if weight_row else 0.0

        deleted_row = self.cursor.execute(
            "SELECT COUNT(*) AS cnt FROM memories WHERE deleted_at IS NOT NULL"
        ).fetchone()
        deleted_count = deleted_row["cnt"] if deleted_row else 0

        all_rows = self.cursor.execute(
            f"SELECT tags FROM memories WHERE deleted_at IS NULL{user_clause}",
            user_params,
        ).fetchall()
        tag_counts: dict[str, int] = {}
        for row in all_rows:
            if row["tags"]:
                for tag in row["tags"].split(","):
                    tag = tag.strip()
                    if tag:
                        tag_counts[tag] = tag_counts.get(tag, 0) + 1
        by_tag = dict(sorted(tag_counts.items(), key=lambda x: x[1], reverse=True))

        return {
            "total": total_active,
            "by_type": by_type,
            "by_tag": by_tag,
            "total_weight": total_weight,
            "deleted_count": deleted_count,
        }

    def get_stats(self, user_id: str | None = None) -> dict:
        """Return total count and per-type breakdown."""
        total = self.count(user_id=user_id)
        user_clause = (
            " AND COALESCE(json_extract(metadata, '$.user_id'), 'default') = ?" if user_id else ""
        )
        user_params = [user_id] if user_id else []
        rows = self.cursor.execute(
            f"SELECT type, COUNT(*) AS cnt FROM memories"
            f" WHERE deleted_at IS NULL{user_clause} GROUP BY type",
            user_params,
        ).fetchall()
        by_type: dict[str, int] = {r["type"]: r["cnt"] for r in rows}
        return {"total": total, "by_type": by_type}
