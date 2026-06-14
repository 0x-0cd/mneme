"""Tests for quality/contradiction detection module."""

from __future__ import annotations

from mneme.engine.quality import ContradictionDetector, ContradictionType
from mneme.engine.search import Searcher
from mneme.engine.store import Store
from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database

from tests.fakes import FakeEmbeddingModel, FakeVectorIndex


def make_detector() -> tuple[
    ContradictionDetector, Store, Database, FakeVectorIndex, FakeEmbeddingModel
]:
    db = Database(":memory:")
    db.initialize()
    vindex = FakeVectorIndex()
    embed = FakeEmbeddingModel()
    store = Store(db, vindex, embed)
    searcher = Searcher(db, vindex, embed)
    detector = ContradictionDetector(db, vindex, embed, searcher)
    return detector, store, db, vindex, embed


class TestDetectNoContradictions:
    def test_empty_db(self) -> None:
        detector, _, _, _, _ = make_detector()
        result = detector.detect()
        assert result == []

    def test_single_memory(self) -> None:
        detector, store, _, _, _ = make_detector()
        store.store(Memory(content="我喜欢咖啡"))
        result = detector.detect()
        assert result == []


class TestDetectDirectContradiction:
    def test_antonym_pair(self) -> None:
        detector, store, _, _, _ = make_detector()
        m1 = store.store(Memory(content="我喜欢咖啡"))
        m2 = store.store(Memory(content="我讨厌咖啡"))
        result = detector.detect()
        assert len(result) == 1
        c = result[0]
        assert c.type == ContradictionType.DIRECT
        assert {c.memory_a_id, c.memory_b_id} == {m1.id, m2.id}
        assert c.score > 0
        assert "喜欢" in c.reason and "讨厌" in c.reason

    def test_english_antonym(self) -> None:
        detector, store, _, _, _ = make_detector()
        m1 = store.store(Memory(content="I like coffee"))
        m2 = store.store(Memory(content="I hate coffee"))
        result = detector.detect()
        assert len(result) == 1
        assert result[0].type == ContradictionType.DIRECT

    def test_multiple_memories_only_contradictory_detected(self) -> None:
        detector, store, _, _, _ = make_detector()
        store.store(Memory(content="我喜欢咖啡"))
        store.store(Memory(content="我讨厌咖啡"))
        store.store(Memory(content="今天天气很好"))
        result = detector.detect()
        assert len(result) == 1


class TestDetectTemporalContradiction:
    def test_same_entity_different_value(self) -> None:
        detector, store, _, _, _ = make_detector()
        m1 = store.store(Memory(content="我在杭州"))
        m2 = store.store(Memory(content="我在上海"))
        result = detector.detect()
        assert len(result) == 1
        c = result[0]
        assert c.type == ContradictionType.TEMPORAL
        assert {c.memory_a_id, c.memory_b_id} == {m1.id, m2.id}

    def test_same_tags_shared_context(self) -> None:
        detector, store, _, _, _ = make_detector()
        m1 = store.store(
            Memory(content="我在杭州工作", tags=["location", "work"])
        )
        m2 = store.store(
            Memory(content="我在上海出差", tags=["location", "work"])
        )
        result = detector.detect()
        assert len(result) >= 1
        types = {c.type for c in result}
        assert ContradictionType.TEMPORAL in types


class TestDetectSpecificMemory:
    def test_only_target_memory_checked(self) -> None:
        detector, store, _, _, _ = make_detector()
        m1 = store.store(Memory(content="我喜欢咖啡"))
        m2 = store.store(Memory(content="我讨厌咖啡"))
        m3 = store.store(Memory(content="今天天气很好"))
        result = detector.detect(memory_id=m1.id)
        assert len(result) == 1
        c = result[0]
        assert c.memory_a_id == m1.id
        assert c.memory_b_id == m2.id

    def test_nonexistent_id(self) -> None:
        detector, store, _, _, _ = make_detector()
        store.store(Memory(content="我喜欢咖啡"))
        result = detector.detect(memory_id="nonexistent-id")
        assert result == []


class TestDetectSkipSameMemory:
    def test_no_self_comparison(self) -> None:
        detector, store, _, _, _ = make_detector()
        store.store(Memory(content="我喜欢咖啡"))
        result = detector.detect()
        assert result == []


class TestDetectSimilarNotContradictory:
    def test_similar_topic_no_antonyms(self) -> None:
        detector, store, _, _, _ = make_detector()
        store.store(Memory(content="我每天早上喝咖啡"))
        store.store(Memory(content="咖啡有助于提神"))
        result = detector.detect()
        assert result == []

    def test_identical_content_no_false_positive(self) -> None:
        detector, store, _, _, _ = make_detector()
        store.store(Memory(content="我喜欢咖啡"))
        store.store(Memory(content="我喜欢咖啡"))
        result = detector.detect()
        assert result == []


class TestDetectionOrdering:
    def test_results_sorted_by_score_desc(self) -> None:
        detector, store, _, _, _ = make_detector()
        store.store(Memory(content="我喜欢咖啡", tags=["drink"]))
        store.store(Memory(content="我讨厌咖啡", tags=["drink"]))
        store.store(Memory(content="我爱喝茶", tags=["drink"]))
        result = detector.detect()
        scores = [c.score for c in result]
        assert scores == sorted(scores, reverse=True)
