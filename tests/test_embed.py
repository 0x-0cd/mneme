"""Tests for embedding model management."""

from __future__ import annotations

from mneme.embed.model import EmbeddingModel


class TestInit:
    def test_init_with_model_name(self):
        model = EmbeddingModel("all-MiniLM-L6-v2")
        assert model.model_name == "all-MiniLM-L6-v2"
        assert model._session is None

    def test_default_model_name(self):
        model = EmbeddingModel()
        assert model.model_name == "all-MiniLM-L6-v2"


class TestLazyLoad:
    def test_lazy_load(self):
        model = EmbeddingModel()
        assert model._session is None
        assert model._tokenizer is None


class TestEncode:
    def test_encode_returns_list_of_floats(self):
        model = EmbeddingModel()
        result = model.encode("hello world")
        assert isinstance(result, list)
        assert len(result) == 384
        assert all(isinstance(v, float) for v in result)

    def test_encode_multiple_texts(self):
        model = EmbeddingModel()
        result = model.encode(["hello", "world"])
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(v, list) for v in result)
        assert all(len(v) == 384 for v in result)
        assert all(all(isinstance(x, float) for x in v) for v in result)


class TestDims:
    def test_dims_known_at_init(self):
        model = EmbeddingModel()
        assert model.dims == 384

    def test_dims_stable_after_encode(self):
        model = EmbeddingModel()
        model.encode("test")
        assert model.dims == 384
