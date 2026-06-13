"""Tests for embedding model management."""

from __future__ import annotations

from mneme.embed.model import EmbeddingModel


class TestInit:
    def test_init_with_model_name(self):
        model = EmbeddingModel("all-MiniLM-L6-v2")
        assert model.model_name == "all-MiniLM-L6-v2"
        assert model._model is None

    def test_default_model_name(self):
        model = EmbeddingModel()
        assert model.model_name == "all-MiniLM-L6-v2"


class TestLazyLoad:
    def test_lazy_load(self):
        model = EmbeddingModel()
        assert model._model is None


class TestEncode:
    def test_encode_returns_list_of_floats(self):
        model = EmbeddingModel()
        result = model.encode("hello world")
        assert isinstance(result, list)
        assert all(isinstance(v, float) for v in result)

    def test_encode_multiple_texts(self):
        model = EmbeddingModel()
        result = model.encode(["hello", "world"])
        assert isinstance(result, list)
        assert len(result) == 2
        assert all(isinstance(v, list) for v in result)
        assert all(all(isinstance(x, float) for x in v) for v in result)


class TestDims:
    def test_dims_before_encode_is_none(self):
        model = EmbeddingModel()
        assert model.dims is None

    def test_dims_after_encode(self):
        model = EmbeddingModel()
        model.encode("test")
        assert isinstance(model.dims, int)
        assert model.dims > 0
