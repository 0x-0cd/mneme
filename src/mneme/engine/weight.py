"""
Weight calibration module — adaptive initial weight assignment.
Phase 1: Type-based default ranges. Phase 2: feedback signals + calibration.
"""

from __future__ import annotations

import contextlib
import sqlite3
from datetime import UTC, datetime

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
        for col in ["last_signal TEXT", "pos_consecutive INTEGER NOT NULL DEFAULT 0"]:
            with contextlib.suppress(sqlite3.OperationalError):
                self.cursor.execute(
                    f"ALTER TABLE weight_calibrations ADD COLUMN {col}"
                )
        self.cursor.execute("""
            CREATE TABLE IF NOT EXISTS feedback_log (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                memory_id   TEXT NOT NULL,
                user_id     TEXT NOT NULL,
                mem_type    TEXT NOT NULL,
                signal      TEXT NOT NULL CHECK(signal IN ('positive', 'negative')),
                weight_before REAL,
                weight_after  REAL,
                bias_before   REAL,
                bias_after    REAL,
                created_at  TEXT NOT NULL DEFAULT (datetime('now'))
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

    def _load_calibration(self, user_id: str, mem_type: str) -> dict | None:
        row = self.cursor.execute(
            "SELECT * FROM weight_calibrations WHERE user_id=? AND mem_type=?",
            (user_id, mem_type),
        ).fetchone()
        return dict(row) if row else None

    def _build_cal_row(
        self, user_id: str, mem_type: str, bias: float, signal: str,
        consecutive: int = 0,
    ) -> dict:
        now = datetime.now(UTC).isoformat()
        row = {
            "user_id": user_id, "mem_type": mem_type, "bias": bias,
            "pos_count": 0, "neg_count": 0,
            "last_pos_at": None, "last_neg_at": None,
            "last_signal": signal, "pos_consecutive": consecutive,
        }
        if signal == "positive":
            row["pos_count"] = 1
            row["last_pos_at"] = now
        else:
            row["neg_count"] = 1
            row["last_neg_at"] = now
        return row

    def _save_calibration(
        self, user_id: str, mem_type: str, bias: float, signal: str,
        consecutive: int = 0,
    ) -> None:
        row = self._build_cal_row(user_id, mem_type, bias, signal, consecutive)
        self.cursor.execute("""
            INSERT INTO weight_calibrations
                (user_id, mem_type, bias, pos_count, neg_count,
                 last_pos_at, last_neg_at, last_signal, pos_consecutive, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            ON CONFLICT(user_id, mem_type) DO UPDATE SET
                bias = excluded.bias,
                pos_count = weight_calibrations.pos_count + excluded.pos_count,
                neg_count = weight_calibrations.neg_count + excluded.neg_count,
                last_pos_at = excluded.last_pos_at,
                last_neg_at = excluded.last_neg_at,
                last_signal = excluded.last_signal,
                pos_consecutive = excluded.pos_consecutive,
                updated_at = excluded.updated_at
        """, (
            row["user_id"], row["mem_type"], row["bias"],
            row["pos_count"], row["neg_count"],
            row["last_pos_at"], row["last_neg_at"],
            row["last_signal"], row["pos_consecutive"],
        ))
        self.conn.commit()

    def _log_feedback(
        self, user_id: str, mem_type: str, memory_id: str | None,
        signal: str, bias_before: float, bias_after: float,
    ) -> None:
        self.cursor.execute(
            """INSERT INTO feedback_log
               (memory_id, user_id, mem_type, signal, bias_before, bias_after, created_at)
               VALUES (?, ?, ?, ?, ?, ?, datetime('now'))""",
            (memory_id or "", user_id, mem_type, signal, bias_before, bias_after),
        )
        self.conn.commit()

    def apply_feedback(
        self, user_id: str, mem_type: str, signal: str,
        memory_id: str | None = None,
    ) -> dict:
        """Process user feedback and adjust calibration bias.

        Args:
            signal: "positive" or "negative"
        Returns:
            dict with bias_before, bias_after, delta
        """
        if user_id == "default":
            return {"bias_before": 0.0, "bias_after": 0.0, "delta": 0.0}
        if signal not in ("positive", "negative"):
            raise ValueError(f"Unknown signal: {signal}")

        cal = self._load_calibration(user_id, mem_type)
        current_bias = cal["bias"] if cal else 0.0
        consecutive = 0

        if signal == "negative":
            new_bias = current_bias - 0.05

        elif signal == "positive":
            if current_bias < 0:
                prev_consecutive = cal["pos_consecutive"] if cal else 0
                last_signal = cal["last_signal"] if cal else None

                consecutive = prev_consecutive + 1 if last_signal == "positive" else 1

                pull_ratio = max(0.1, 0.6 * (0.5 ** (consecutive - 1)))
                new_bias = current_bias * (1 - pull_ratio)
            else:
                new_bias = current_bias + 0.01

        new_bias = max(-0.2, min(0.2, new_bias))

        self._save_calibration(user_id, mem_type, new_bias, signal, consecutive)
        self._log_feedback(
            user_id, mem_type, memory_id, signal, current_bias, new_bias,
        )

        return {
            "bias_before": round(current_bias, 4),
            "bias_after": round(new_bias, 4),
            "delta": round(new_bias - current_bias, 4),
        }

    def decay_calibrations(self) -> None:
        """Phase 3 stub — decay calibration bias toward zero over time."""
        pass

    def close(self) -> None:
        self.conn.close()
