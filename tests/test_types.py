"""Tests for MemoryType enum and Memory data model."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from mneme.engine.types import Memory, MemoryType


class TestMemoryType:
    def test_enum_values(self):
        assert MemoryType.FACT.value == "fact"
        assert MemoryType.PREFERENCE.value == "preference"
        assert MemoryType.EVENT.value == "event"
        assert MemoryType.CONVERSATION.value == "conversation"
        assert MemoryType.SKILL.value == "skill"

    def test_enum_members_count(self):
        assert len(MemoryType) == 5

    def test_enum_from_string(self):
        assert MemoryType("fact") == MemoryType.FACT
        assert MemoryType("preference") == MemoryType.PREFERENCE
        assert MemoryType("event") == MemoryType.EVENT
        assert MemoryType("conversation") == MemoryType.CONVERSATION
        assert MemoryType("skill") == MemoryType.SKILL

    def test_enum_invalid_string(self):
        with pytest.raises(ValueError):
            MemoryType("invalid_type")


class TestMemoryCreate:
    def test_minimal(self):
        m = Memory(content="hello world")
        assert m.content == "hello world"
        assert m.type == MemoryType.FACT
        assert isinstance(m.id, str) and len(m.id) > 0
        assert m.weight == 1.0
        assert m.tags == []
        assert m.metadata == {}
        assert isinstance(m.created_at, datetime)
        assert isinstance(m.updated_at, datetime)
        assert m.version == 1
        assert m.superseded_by is None
        assert m.deleted_at is None

    def test_with_all_fields(self):
        now = datetime.now(UTC)
        m = Memory(
            content="preference data",
            type=MemoryType.PREFERENCE,
            weight=2.5,
            tags=["important", "user"],
            metadata={"key": "value"},
            id="custom-id-123",
            created_at=now,
            updated_at=now,
            version=3,
            superseded_by="prev-id",
            deleted_at=now,
        )
        assert m.content == "preference data"
        assert m.type == MemoryType.PREFERENCE
        assert m.weight == 2.5
        assert m.tags == ["important", "user"]
        assert m.metadata == {"key": "value"}
        assert m.id == "custom-id-123"
        assert m.created_at == now
        assert m.updated_at == now
        assert m.version == 3
        assert m.superseded_by == "prev-id"
        assert m.deleted_at == now

    def test_auto_generate_uuid(self):
        m1 = Memory(content="a")
        m2 = Memory(content="b")
        assert m1.id != m2.id

    def test_default_type_is_fact(self):
        m = Memory(content="default test")
        assert m.type == MemoryType.FACT

    def test_string_type_auto_converted(self):
        m = Memory(content="string type", type="event")
        assert m.type == MemoryType.EVENT
        assert isinstance(m.type, MemoryType)

    def test_content_empty_raises(self):
        with pytest.raises(ValueError, match="content must not be empty"):
            Memory(content="")

    def test_content_whitespace_only_raises(self):
        with pytest.raises(ValueError, match="content must not be empty"):
            Memory(content="   ")

    def test_weight_zero_raises(self):
        with pytest.raises(ValueError, match="weight must be > 0"):
            Memory(content="test", weight=0)

    def test_weight_negative_raises(self):
        with pytest.raises(ValueError, match="weight must be > 0"):
            Memory(content="test", weight=-1)

    def test_weight_positive_small(self):
        m = Memory(content="test", weight=0.001)
        assert m.weight == 0.001


class TestMemoryToDict:
    def test_basic_serialization(self):
        m = Memory(content="serialize me", tags=["a", "b"])
        d = m.to_dict()
        assert d["content"] == "serialize me"
        assert d["type"] == "fact"
        assert d["tags"] == ["a", "b"]
        assert d["metadata"] == {}
        assert d["weight"] == 1.0
        assert d["version"] == 1
        assert d["superseded_by"] is None
        assert d["deleted_at"] is None

    def test_datetime_iso_format(self):
        m = Memory(content="datetime test")
        d = m.to_dict()
        assert isinstance(d["created_at"], str)
        assert isinstance(d["updated_at"], str)
        datetime.fromisoformat(d["created_at"])
        datetime.fromisoformat(d["updated_at"])

    def test_roundtrip(self):
        original = Memory(
            content="roundtrip",
            type="skill",
            weight=3.0,
            tags=["x"],
            metadata={"n": 42},
        )
        d = original.to_dict()
        restored = Memory.from_dict(d)
        assert restored.content == original.content
        assert restored.type == original.type
        assert restored.weight == original.weight
        assert restored.tags == original.tags
        assert restored.metadata == original.metadata
        assert restored.version == original.version
        assert restored.created_at == original.created_at
        assert restored.updated_at == original.updated_at

    def test_roundtrip_soft_deleted(self):
        now = datetime.now(UTC)
        original = Memory(
            content="deleted item",
            deleted_at=now,
            superseded_by="new-version-id",
        )
        d = original.to_dict()
        restored = Memory.from_dict(d)
        assert restored.deleted_at == original.deleted_at
        assert restored.superseded_by == original.superseded_by


class TestMemoryFromDict:
    def test_minimal_dict(self):
        d = {"content": "from dict"}
        m = Memory.from_dict(d)
        assert m.content == "from dict"
        assert m.type == MemoryType.FACT

    def test_full_dict(self):
        d = {
            "content": "full",
            "type": "conversation",
            "weight": 0.5,
            "tags": ["tag1"],
            "metadata": {"key": "val"},
            "id": "explicit-id",
            "created_at": "2024-01-01T00:00:00+00:00",
            "updated_at": "2024-01-02T00:00:00+00:00",
            "version": 5,
            "superseded_by": "old-id",
            "deleted_at": None,
        }
        m = Memory.from_dict(d)
        assert m.content == "full"
        assert m.type == MemoryType.CONVERSATION
        assert m.weight == 0.5
        assert m.tags == ["tag1"]
        assert m.metadata == {"key": "val"}
        assert m.id == "explicit-id"
        assert m.created_at == datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert m.updated_at == datetime(2024, 1, 2, 0, 0, 0, tzinfo=UTC)
        assert m.version == 5
        assert m.superseded_by == "old-id"
        assert m.deleted_at is None

    def test_string_type_in_from_dict(self):
        d = {"content": "test", "type": "preference"}
        m = Memory.from_dict(d)
        assert m.type == MemoryType.PREFERENCE

    def test_missing_content_raises(self):
        with pytest.raises(ValueError, match="content must not be empty"):
            Memory.from_dict({"type": "fact"})

    def test_empty_content_raises(self):
        with pytest.raises(ValueError, match="content must not be empty"):
            Memory.from_dict({"content": ""})
