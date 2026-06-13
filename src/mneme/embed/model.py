"""Embedding model management for Mneme."""

from __future__ import annotations

from sentence_transformers import SentenceTransformer


class EmbeddingModel:
    def __init__(self, model_name: str = "all-MiniLM-L6-v2") -> None:
        self.model_name = model_name
        self._model: SentenceTransformer | None = None

    def _load_model(self) -> None:
        if self._model is None:
            self._model = SentenceTransformer(self.model_name)

    @property
    def dims(self) -> int | None:
        if self._model is None:
            return None
        return self._model.get_sentence_embedding_dimension()

    def encode(self, text: str | list[str]) -> list[float] | list[list[float]]:
        self._load_model()
        result = self._model.encode(text, normalize_embeddings=True)
        if isinstance(text, str):
            return result.tolist()
        return [v.tolist() for v in result]
