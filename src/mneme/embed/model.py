"""Embedding model using ONNX Runtime (no PyTorch needed)."""

from __future__ import annotations

import os

import numpy as np
import onnxruntime as ort
from transformers import AutoTokenizer


class EmbeddingModel:
    """ONNX-based embedding model with lazy loading.

    Uses ONNX Runtime instead of PyTorch, making it suitable for
    resource-constrained environments like Raspberry Pi.
    """

    _MODEL_INFO = {
        "all-MiniLM-L6-v2": {
            "repo": "sentence-transformers/all-MiniLM-L6-v2",
            "onnx_file": "onnx/model.onnx",
            "dims": 384,
        },
    }

    def __init__(self, model_name: str = "all-MiniLM-L6-v2", cache_dir: str | None = None):
        self.model_name = model_name
        self._model_info = self._MODEL_INFO.get(model_name)
        if self._model_info is None:
            raise ValueError(
                f"Unknown model: {model_name}. Available: {list(self._MODEL_INFO.keys())}"
            )

        self._cache_dir = cache_dir or os.path.join(
            os.path.expanduser("~"), ".cache", "mneme", "onnx"
        )
        self._session: ort.InferenceSession | None = None
        self._tokenizer: AutoTokenizer | None = None
        self._dims: int = self._model_info["dims"]

    @property
    def dims(self) -> int:
        """Get embedding dimensions."""
        return self._dims

    def _load(self):
        """Download ONNX model and tokenizer, create inference session."""
        repo = self._model_info["repo"]
        onnx_file = self._model_info["onnx_file"]

        # Load tokenizer from HuggingFace (uses transformers, no PyTorch needed)
        # First try local-only (no network), then fall back to online
        try:
            self._tokenizer = AutoTokenizer.from_pretrained(repo, local_files_only=True)
        except OSError:
            self._tokenizer = AutoTokenizer.from_pretrained(repo)

        # Try to load local ONNX model first, then download
        onnx_path = self._resolve_onnx_path(onnx_file, repo)
        self._session = ort.InferenceSession(
            onnx_path,
            providers=["CPUExecutionProvider"],
        )

    def _resolve_onnx_path(self, onnx_file: str, repo: str) -> str:
        """Find or download the ONNX model file."""
        # Check common local locations
        local_candidates = [
            os.path.join(self._cache_dir, repo.replace("/", "_"), onnx_file),
            os.path.join(self._cache_dir, onnx_file),
        ]
        for path in local_candidates:
            if os.path.exists(path):
                return path

        # Download from HuggingFace using huggingface_hub
        from huggingface_hub import hf_hub_download

        # Try ONNX path first
        try:
            return hf_hub_download(
                repo_id=repo,
                filename=onnx_file,
                cache_dir=self._cache_dir,
            )
        except (OSError, EnvironmentError):
            # Fallback: download the model and convert using optimum
            # For now, try raw model export
            onnx_path = self._convert_to_onnx(repo)
            return onnx_path

    def _convert_to_onnx(self, repo: str) -> str:
        """Convert a HuggingFace transformer model to ONNX using optimum.

        This is a fallback when no pre-converted ONNX model is available.
        """
        onnx_path = os.path.join(self._cache_dir, repo.replace("/", "_"), "model.onnx")
        os.makedirs(os.path.dirname(onnx_path), exist_ok=True)

        # Use optimum to export the model to ONNX
        from optimum.onnxruntime import ORTModelForFeatureExtraction

        model = ORTModelForFeatureExtraction.from_pretrained(repo, export=True)
        model.save_pretrained(os.path.dirname(onnx_path))
        return onnx_path

    def encode(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Encode text(s) into embedding vector(s).

        Uses mean pooling + normalization for sentence embeddings.
        """
        if self._session is None:
            self._load()

        single = isinstance(text, str)
        texts = [text] if single else text

        # Tokenize
        inputs = self._tokenizer(  # type: ignore
            texts,
            padding=True,
            truncation=True,
            return_tensors="np",
            max_length=256,
        )

        # Run ONNX inference
        onnx_inputs = {
            "input_ids": inputs["input_ids"].astype(np.int64),
            "attention_mask": inputs["attention_mask"].astype(np.int64),
            "token_type_ids": inputs.get(
                "token_type_ids", np.zeros_like(inputs["input_ids"])
            ).astype(np.int64),
        }
        # Remove token_type_ids if model doesn't use it
        model_inputs = [inp.name for inp in self._session.get_inputs()]  # type: ignore
        if "token_type_ids" not in model_inputs:
            del onnx_inputs["token_type_ids"]

        outputs = self._session.run(None, onnx_inputs)  # type: ignore
        last_hidden = outputs[0]  # (batch, seq_len, hidden)

        # Mean pooling
        attention_mask = inputs["attention_mask"]
        mask_expanded = np.expand_dims(attention_mask, axis=-1).astype(last_hidden.dtype)
        sum_embeddings = np.sum(last_hidden * mask_expanded, axis=1)
        sum_mask = np.clip(np.sum(mask_expanded, axis=1), 1e-9, None)
        embeddings = sum_embeddings / sum_mask

        # Normalize (L2)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        normalized = embeddings / np.clip(norms, 1e-12, None)

        if single:
            return normalized[0].tolist()
        return [v.tolist() for v in normalized]
