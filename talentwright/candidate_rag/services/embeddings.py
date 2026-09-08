"""Embedding generation client for candidate resume RAG."""

from __future__ import annotations

import logging
import os
from typing import Sequence

from openai import OpenAI

from talentwright.candidate_rag.services.vector_math import normalize_vector
from talentwright.resume_analysis.exceptions import LLMConfigurationError

logger = logging.getLogger(__name__)


def _get_setting(name: str, default: str = "") -> str:
    """Fetch setting from Django settings or environment variables."""
    try:
        from django.conf import settings as django_settings

        value = getattr(django_settings, name, None)
        if value:
            return str(value)
    except Exception:  # noqa: BLE001
        pass
    return os.environ.get(name, default)


class EmbeddingClient:
    """Client for generating normalized dense embeddings using OpenAI / OpenRouter."""

    def __init__(
        self,
        api_key: str | None = None,
        base_url: str | None = None,
        model: str | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.api_key = (
            api_key
            or _get_setting("SCREENING_LLM_API_KEY")
            or _get_setting("OPENROUTER_API_KEY")
            or _get_setting("OPENAI_API_KEY")
        )
        if not self.api_key:
            msg = "Neither OPENROUTER_API_KEY nor SCREENING_LLM_API_KEY nor OPENAI_API_KEY is configured."
            raise LLMConfigurationError(msg)

        default_base_url = (
            "https://api.openai.com/v1"
            if _get_setting("OPENAI_API_KEY")
            and not (_get_setting("SCREENING_LLM_BASE_URL") or _get_setting("OPENROUTER_API_KEY") or _get_setting("SCREENING_LLM_API_KEY"))
            else "https://openrouter.ai/api/v1"
        )
        self.base_url = (
            base_url
            or _get_setting("SCREENING_LLM_BASE_URL")
            or default_base_url
        )
        self.model = (
            model
            or _get_setting("CANDIDATE_EMBEDDING_MODEL")
            or "text-embedding-3-small"
        )
        self.timeout = timeout
        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url,
            timeout=self.timeout,
        )

    def get_embedding(self, text: str) -> list[float]:
        """Generate a normalized embedding vector for a single text string."""
        cleaned = text.strip()
        if not cleaned:
            return []
        batch = self.get_embeddings_batch([cleaned])
        return batch[0] if batch else []

    def get_embeddings_batch(self, texts: Sequence[str]) -> list[list[float]]:
        """Generate normalized embedding vectors for a batch of text strings in a single API call.

        Args:
            texts: A list or sequence of text strings to embed.

        Returns:
            A list of unit-normalized embedding vectors (each a list of floats).
        """
        cleaned_texts = [t.strip() for t in texts if t.strip()]
        if not cleaned_texts:
            return []

        try:
            logger.debug(
                "Requesting embeddings for %d texts with model '%s'",
                len(cleaned_texts),
                self.model,
            )
            response = self.client.embeddings.create(
                model=self.model,
                input=cleaned_texts,
            )
            # OpenAI embeddings response items are ordered by index
            sorted_data = sorted(response.data, key=lambda item: item.index)
            embeddings = [normalize_vector(item.embedding) for item in sorted_data]
            return embeddings
        except Exception as exc:
            logger.exception("Failed to generate embeddings: %s", exc)
            raise
