"""Vector index layer using sqlite-vec for semantic search."""

from __future__ import annotations

import sqlite3
import struct

import sqlite_vec


class VectorIndex:
    def __init__(self, db_path: str = "memories.db", dimensions: int = 384) -> None:
        self.db_path = db_path
        self.dimensions = dimensions
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()

    def __del__(self) -> None:
        self.close()

    def initialize(self) -> None:
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)
        self.cursor.execute(
            "CREATE VIRTUAL TABLE IF NOT EXISTS memories_vec USING vec0("
            "    id TEXT,"
            f"    embedding float[{self.dimensions}]"
            ")"
        )
        self.conn.commit()

    def close(self) -> None:
        if hasattr(self, "conn") and self.conn:
            self.conn.close()
            self.conn = None  # type: ignore[assignment]

    @staticmethod
    def _pack(vector: list[float]) -> bytes:
        return struct.pack(f"{len(vector)}f", *vector)

    def insert(self, memory_id: str, embedding: list[float]) -> None:
        self.delete(memory_id)
        blob = self._pack(embedding)
        self.cursor.execute(
            "INSERT INTO memories_vec(id, embedding) VALUES (?, ?)",
            (memory_id, blob),
        )
        self.conn.commit()

    def search(self, query_vector: list[float], limit: int = 20) -> list[tuple[str, float]]:
        blob = self._pack(query_vector)
        rows = self.cursor.execute(
            "SELECT id, distance FROM memories_vec"
            " WHERE embedding MATCH ? ORDER BY distance LIMIT ?",
            (blob, limit),
        ).fetchall()
        return [(row[0], row[1]) for row in rows]

    def delete(self, memory_id: str) -> None:
        self.cursor.execute("DELETE FROM memories_vec WHERE id = ?", (memory_id,))
        self.conn.commit()

    def clear(self) -> None:
        self.cursor.execute("DELETE FROM memories_vec")
        self.conn.commit()

    def count(self) -> int:
        row = self.cursor.execute("SELECT COUNT(*) AS cnt FROM memories_vec").fetchone()
        return row[0] if row else 0
