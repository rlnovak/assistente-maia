"""
Wrapper sobre OpenAI text-embedding-3-small.
Provider travado — não alterar sem reingerir todo o knowledge/.
"""
from __future__ import annotations

import time

from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings

# Batch máximo recomendado pela OpenAI para embeddings
EMBED_BATCH_SIZE = 100


def _get_client():
    from openai import OpenAI  # import local — não vazar para fora deste módulo
    return OpenAI(api_key=settings.OPENAI_API_KEY)


@retry(
    retry=retry_if_exception_type(Exception),
    wait=wait_exponential(multiplier=1, min=2, max=60),
    stop=stop_after_attempt(5),
    reraise=True,
)
def _embed_batch(texts: list[str], client) -> list[list[float]]:
    response = client.embeddings.create(
        model=settings.EMBEDDING_MODEL,
        input=texts,
    )
    # Mantém ordem original
    items = sorted(response.data, key=lambda x: x.index)
    return [item.embedding for item in items]


def embed_texts(texts: list[str]) -> list[list[float]]:
    """
    Gera embeddings para lista de textos.
    Processa em batches de EMBED_BATCH_SIZE.
    Retry automático em rate limit (429) e erros 5xx via tenacity.
    """
    if not texts:
        return []

    client = _get_client()
    all_embeddings: list[list[float]] = []

    for i in range(0, len(texts), EMBED_BATCH_SIZE):
        batch = texts[i : i + EMBED_BATCH_SIZE]
        batch_embeddings = _embed_batch(batch, client)
        all_embeddings.extend(batch_embeddings)

    return all_embeddings


def embed_single(text: str) -> list[float]:
    """Convenência para um único texto."""
    return embed_texts([text])[0]


def estimate_cost(total_tokens: int) -> float:
    """
    Estimativa de custo em USD para text-embedding-3-small.
    Preço: $0.02 / 1M tokens (maio 2025).
    """
    return (total_tokens / 1_000_000) * 0.02


def estimate_tokens(texts: list[str]) -> int:
    """Estimativa rápida: ~1.3 tokens por palavra."""
    total_words = sum(len(t.split()) for t in texts)
    return int(total_words * 1.3)
