"""Sentence embeddings — memory-architecture-quack.md §1.1, §5.4.

Used only by seed_misconceptions in phase 1 (compute library embeddings).
Lazy load: the model is downloaded on first call, not at import.

Model: intfloat/multilingual-e5-small (384 dim), prefix "query: " for e5,
L2-normalized vectors.
"""

from __future__ import annotations


class Embedder:
    """Wrapper around sentence-transformers with lazy load and dimension check."""

    def __init__(self, model_name: str, dim: int) -> None:
        self.model_name = model_name
        self.dim = dim
        self._model = None

    def _load(self) -> None:
        if self._model is not None:
            return
        # Import inside _load to avoid pulling torch at module import time.
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name)

    def embed(self, texts: list[str]) -> list[list[float]]:
        """Return L2-normalized embeddings, one per input text.

        Prefixes each text with 'query: ' per e5 convention.
        Raises ValueError if the model returns a vector of the wrong size.
        """
        if not texts:
            return []
        self._load()
        assert self._model is not None  # for mypy/ruff
        prefixed = [f"query: {t}" for t in texts]
        vectors = self._model.encode(
            prefixed,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        out: list[list[float]] = [list(map(float, v)) for v in vectors]
        for v in out:
            if len(v) != self.dim:
                raise ValueError(
                    f"embedding dim mismatch: got {len(v)}, expected {self.dim}"
                )
        return out
