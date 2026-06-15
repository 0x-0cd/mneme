"""
Weight calibration module — adaptive initial weight assignment.
Phase 1: Type-based default ranges.
"""

from __future__ import annotations

import sqlite3

TYPE_WEIGHT_RANGES: dict[str, list[float]] = {
    "preference":   [0.7, 1.0],
    "event":        [0.5, 0.9],
    "fact":         [0.3, 0.8],
    "conversation": [0.2, 0.6],
    "skill":        [0.6, 1.0],
}


class WeightCalibrator:
    def __init__(self, db_path: str = "memories.db"):
        self.conn = sqlite3.connect(db_path)
        self.conn.row_factory = sqlite3.Row
        self.cursor = self.conn.cursor()
        self._initialize_table()

    def _initialize_table(self) -> None:
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS weight_calibrations (
                user_id     TEXT NOT NULL,
                mem_type    TEXT NOT NULL,
                bias        REAL NOT NULL DEFAULT 0.0,
                pos_count   INTEGER NOT NULL DEFAULT 0,
                neg_count   INTEGER NOT NULL DEFAULT 0,
                last_pos_at TEXT,
                last_neg_at TEXT,
                updated_at  TEXT NOT NULL DEFAULT (datetime('now')),
                PRIMARY KEY (user_id, mem_type)
            )
        """)
        self.conn.commit()

    def get_effective_weight(self, user_id: str, mem_type: str) -> float:
        """Return the effective initial weight for a (user_id, mem_type) pair."""
        if user_id == "default":
            return 1.0

        mem_type = mem_type.lower()
        if mem_type not in TYPE_WEIGHT_RANGES:
            return 1.0

        base_min, base_max = TYPE_WEIGHT_RANGES[mem_type]
        midpoint = (base_min + base_max) / 2.0
        bias = self._load_bias(user_id, mem_type)
        effective = midpoint + bias
        return max(base_min, min(base_max, effective))

    def _load_bias(self, user_id: str, mem_type: str) -> float:
        row = self.cursor.execute(
            "SELECT bias FROM weight_calibrations WHERE user_id=? AND mem_type=?",
            (user_id, mem_type),
        ).fetchone()
        return row["bias"] if row else 0.0

    def apply_feedback(self, user_id: str, mem_type: str, signal: str) -> None:
        """Phase 2 stub — apply user feedback to adjust calibration bias."""
        pass

    def decay_calibrations(self) -> None:
        """Phase 3 stub — decay calibration bias toward zero over time."""
        pass

    def close(self) -> None:
        self.conn.close()
