"""Tests for embedding client service."""

from unittest.mock import MagicMock
from unittest.mock import patch
import pytest

from talentwright.candidate_rag.services.embeddings import EmbeddingClient


class FakeEmbeddingItem:
    def __init__(self, index: int, embedding: list[float]):
        self.index = index
        self.embedding = embedding


class FakeEmbeddingResponse:
    def __init__(self, items: list[FakeEmbeddingItem]):
        self.data = items


def test_embedding_client_empty_inputs():
    client = EmbeddingClient(api_key="test-key", base_url="https://example.com/v1")
    assert client.get_embedding("") == []
    assert client.get_embedding("   ") == []
    assert client.get_embeddings_batch([]) == []


@patch("talentwright.candidate_rag.services.embeddings.OpenAI")
def test_embedding_client_batch_success(mock_openai_class):
    mock_openai = MagicMock()
    mock_openai_class.return_value = mock_openai

    fake_response = FakeEmbeddingResponse(
        [
            FakeEmbeddingItem(index=0, embedding=[3.0, 4.0]),
            FakeEmbeddingItem(index=1, embedding=[1.0, 0.0]),
        ]
    )
    mock_openai.embeddings.create.return_value = fake_response

    client = EmbeddingClient(api_key="fake-key", base_url="https://fake.url/v1")
    vectors = client.get_embeddings_batch(["Text one", "Text two"])

    assert len(vectors) == 2
    # Vectors must be unit normalized: [3.0, 4.0] -> [0.6, 0.8]
    assert pytest.approx(vectors[0][0], rel=1e-4) == 0.6
    assert pytest.approx(vectors[0][1], rel=1e-4) == 0.8
    assert vectors[1] == [1.0, 0.0]

    mock_openai.embeddings.create.assert_called_once()
