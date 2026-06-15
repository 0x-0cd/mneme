"""Tests for weight calibration module."""

from __future__ import annotations

from pathlib import Path

import pytest

from mneme.engine.weight import WeightCalibrator


@pytest.fixture
def cal(tmp_path: Path) -> WeightCalibrator:
    db_path = str(tmp_path / "test.db")
    return WeightCalibrator(db_path)


class TestGetEffectiveWeight:
    def test_default_user_returns_one(self, cal: WeightCalibrator) -> None:
        assert cal.get_effective_weight("default", "preference") == 1.0

    def test_unknown_type_returns_one(self, cal: WeightCalibrator) -> None:
        assert cal.get_effective_weight("user_a", "bogus_type") == 1.0

    def test_preference_within_range(self, cal: WeightCalibrator) -> None:
        w = cal.get_effective_weight("user_a", "preference")
        assert 0.7 <= w <= 1.0

    def test_returns_midpoint_when_no_bias(self, cal: WeightCalibrator) -> None:
        w = cal.get_effective_weight("user_x", "preference")
        assert w == pytest.approx(0.85)

    def test_reflects_bias_after_feedback(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_x", "preference", "negative")
        w = cal.get_effective_weight("user_x", "preference")
        assert w == pytest.approx(0.80)


class TestApplyFeedbackNegative:
    def test_negative_reduces_bias(self, cal: WeightCalibrator) -> None:
        result = cal.apply_feedback("user_a", "preference", "negative")
        assert result["bias_before"] == 0.0
        assert result["bias_after"] == pytest.approx(-0.05)
        assert result["delta"] == pytest.approx(-0.05)

    def test_negative_accumulates(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_a", "preference", "negative")
        result = cal.apply_feedback("user_a", "preference", "negative")
        assert result["bias_before"] == pytest.approx(-0.05)
        assert result["bias_after"] == pytest.approx(-0.10)
        assert result["delta"] == pytest.approx(-0.05)


class TestApplyFeedbackPositiveWhenBiasNegative:
    def test_positive_pulls_back_60_percent(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_a", "preference", "negative")
        cal.apply_feedback("user_a", "preference", "negative")
        result = cal.apply_feedback("user_a", "preference", "positive")
        assert result["bias_before"] == pytest.approx(-0.10)
        assert result["bias_after"] == pytest.approx(-0.04)
        assert result["delta"] == pytest.approx(0.06)

    def test_consecutive_positives_decay_pull_strength(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_a", "preference", "negative")
        cal.apply_feedback("user_a", "preference", "negative")
        r1 = cal.apply_feedback("user_a", "preference", "positive")
        assert r1["bias_after"] == pytest.approx(-0.04)

        r2 = cal.apply_feedback("user_a", "preference", "positive")
        assert r2["bias_before"] == pytest.approx(-0.04)
        assert r2["bias_after"] == pytest.approx(-0.028)

        r3 = cal.apply_feedback("user_a", "preference", "positive")
        assert r3["bias_before"] == pytest.approx(-0.028)
        assert r3["bias_after"] == pytest.approx(-0.0238)

    def test_pull_ratio_floor_at_0_1(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_a", "preference", "negative")
        cal.apply_feedback("user_a", "preference", "negative")
        for _ in range(10):
            cal.apply_feedback("user_a", "preference", "positive")
        result = cal.apply_feedback("user_a", "preference", "positive")
        # bias is near zero from repeated pulls; last pull is weak
        assert result["delta"] < 0.02


class TestApplyFeedbackPositiveWhenBiasNonNegative:
    def test_positive_on_zero_adds_micro_adjustment(self, cal: WeightCalibrator) -> None:
        result = cal.apply_feedback("user_a", "preference", "positive")
        assert result["bias_before"] == 0.0
        assert result["bias_after"] == pytest.approx(0.01)
        assert result["delta"] == pytest.approx(0.01)

    def test_positive_on_positive_adds_micro(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_a", "preference", "positive")
        result = cal.apply_feedback("user_a", "preference", "positive")
        assert result["bias_before"] == pytest.approx(0.01)
        assert result["bias_after"] == pytest.approx(0.02)
        assert result["delta"] == pytest.approx(0.01)


class TestApplyFeedbackClamping:
    def test_lower_bound_clamped_at_minus_0_2(self, cal: WeightCalibrator) -> None:
        for _ in range(5):
            cal.apply_feedback("user_a", "preference", "negative")
        result = cal.apply_feedback("user_a", "preference", "negative")
        assert result["bias_after"] == pytest.approx(-0.2)

    def test_upper_bound_clamped_at_0_2(self, cal: WeightCalibrator) -> None:
        user = "user_upper"
        for _ in range(25):
            cal.apply_feedback(user, "preference", "positive")
        result = cal.apply_feedback(user, "preference", "positive")
        assert result["bias_after"] == pytest.approx(0.2)


class TestApplyFeedbackEdgeCases:
    def test_default_user_is_noop(self, cal: WeightCalibrator) -> None:
        result = cal.apply_feedback("default", "preference", "negative")
        assert result == {"bias_before": 0.0, "bias_after": 0.0, "delta": 0.0}

    def test_invalid_signal_raises(self, cal: WeightCalibrator) -> None:
        with pytest.raises(ValueError, match="Unknown signal"):
            cal.apply_feedback("user_a", "preference", "neutral")

    def test_memory_id_logged(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_a", "preference", "negative", memory_id="mem-1")
        row = cal.cursor.execute(
            "SELECT * FROM feedback_log WHERE memory_id=?", ("mem-1",)
        ).fetchone()
        assert row is not None
        assert row["signal"] == "negative"
        assert row["mem_type"] == "preference"


class TestFeedbackLog:
    def test_log_written_on_feedback(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_a", "preference", "positive")
        row = cal.cursor.execute(
            "SELECT * FROM feedback_log WHERE user_id=? AND mem_type=?",
            ("user_a", "preference"),
        ).fetchone()
        assert row is not None
        assert row["signal"] == "positive"
        assert row["bias_before"] == 0.0
        assert row["bias_after"] == pytest.approx(0.01)

    def test_log_bias_values_after_negative(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_b", "fact", "negative")
        row = cal.cursor.execute(
            "SELECT * FROM feedback_log WHERE user_id=? AND mem_type=?",
            ("user_b", "fact"),
        ).fetchone()
        assert row is not None
        assert row["bias_before"] == 0.0
        assert row["bias_after"] == pytest.approx(-0.05)

    def test_log_without_memory_id(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_c", "event", "positive")
        row = cal.cursor.execute(
            "SELECT * FROM feedback_log WHERE user_id=?", ("user_c",)
        ).fetchone()
        assert row is not None
        assert row["memory_id"] == ""


class TestCalibrationPersistence:
    def test_calibration_saved_and_reloaded(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_a", "preference", "negative")
        cal_row = cal._load_calibration("user_a", "preference")
        assert cal_row is not None
        assert cal_row["bias"] == pytest.approx(-0.05)
        assert cal_row["neg_count"] == 1


class TestTableInitialization:
    def test_feedback_log_table_exists(self, cal: WeightCalibrator) -> None:
        row = cal.cursor.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='feedback_log'"
        ).fetchone()
        assert row is not None

    def test_weight_calibrations_has_new_columns(self, cal: WeightCalibrator) -> None:
        info = cal.cursor.execute("PRAGMA table_info(weight_calibrations)").fetchall()
        cols = {r["name"] for r in info}
        assert "last_signal" in cols
        assert "pos_consecutive" in cols

    def test_new_columns_have_defaults(self, cal: WeightCalibrator) -> None:
        cal.apply_feedback("user_a", "preference", "positive")
        row = cal._load_calibration("user_a", "preference")
        assert row is not None
        assert row["pos_consecutive"] == 0
        assert row["last_signal"] == "positive"
