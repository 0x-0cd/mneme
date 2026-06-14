"""Unit tests for embedding model management (no network)."""

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


class TestDims:
    def test_dims_known_at_init(self):
        model = EmbeddingModel()
        assert model.dims == 384
