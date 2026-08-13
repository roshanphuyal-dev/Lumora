"""Provider-boundary tests for Gemini's batched embedding call."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from ai.gemini.client import EMBEDDING_DIMENSIONS, GeminiClient, GeminiError


def _client_with_response(response: object) -> tuple[GeminiClient, AsyncMock]:
    # Bypass `__init__` so this unit test never constructs the real provider SDK client.
    client = GeminiClient.__new__(GeminiClient)
    embed_content = AsyncMock(return_value=response)
    client._client = SimpleNamespace(  # type: ignore[assignment]  # provider SDK test seam
        aio=SimpleNamespace(models=SimpleNamespace(embed_content=embed_content))
    )
    return client, embed_content


@pytest.mark.parametrize(
    ("purpose", "provider_task_type"),
    [
        ("retrieval_document", "RETRIEVAL_DOCUMENT"),
        ("retrieval_query", "RETRIEVAL_QUERY"),
    ],
)
async def test_embed_texts_uses_fixed_model_dimension_and_task_type(
    purpose: str, provider_task_type: str
) -> None:
    vectors = [[0.1] * EMBEDDING_DIMENSIONS, [0.2] * EMBEDDING_DIMENSIONS]
    response = SimpleNamespace(embeddings=[SimpleNamespace(values=vector) for vector in vectors])
    client, embed_content = _client_with_response(response)

    result = await client.embed_texts(texts=["one", "two"], purpose=purpose)

    assert result == vectors
    call = embed_content.await_args
    assert call.kwargs["model"] == "gemini-embedding-001"
    assert call.kwargs["contents"] == ["one", "two"]
    assert call.kwargs["config"].task_type == provider_task_type
    assert call.kwargs["config"].output_dimensionality == EMBEDDING_DIMENSIONS


async def test_embed_texts_rejects_incomplete_provider_batch() -> None:
    response = SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1] * EMBEDDING_DIMENSIONS)])
    client, _ = _client_with_response(response)

    with pytest.raises(GeminiError, match="unexpected number of embeddings"):
        await client.embed_texts(
            texts=["one", "two"],
            purpose="retrieval_document",
        )


async def test_embed_texts_rejects_wrong_vector_dimensions() -> None:
    response = SimpleNamespace(embeddings=[SimpleNamespace(values=[0.1, 0.2])])
    client, _ = _client_with_response(response)

    with pytest.raises(GeminiError, match="dimensions other than 768"):
        await client.embed_texts(texts=["one"], purpose="retrieval_query")
