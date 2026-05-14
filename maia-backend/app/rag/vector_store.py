"""
Abstração VectorStore — interface ABC + LocalVectorStore (Chroma) + PineconeVectorStore (stub).

Regra: nenhum código fora deste arquivo deve importar chromadb ou pinecone diretamente.
Sempre consumir via get_vector_store().
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.core.config import settings


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

@dataclass
class VectorItem:
    id: str
    vector: list[float]
    metadata: dict[str, Any]
    content: str


@dataclass
class QueryResult:
    id: str
    content: str
    metadata: dict[str, Any]
    score: float


# ---------------------------------------------------------------------------
# Interface
# ---------------------------------------------------------------------------

class VectorStore(ABC):

    @abstractmethod
    def upsert(self, items: list[VectorItem]) -> None:
        """Insere ou atualiza chunks em batch."""

    @abstractmethod
    def query(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict | None = None,
    ) -> list[QueryResult]:
        """Retorna chunks mais similares ao vetor query."""

    @abstractmethod
    def delete_by_filter(self, filter: dict) -> int:
        """Deleta chunks por metadata. Retorna quantidade deletada."""

    @abstractmethod
    def count(self) -> int:
        """Total de vetores no índice."""


# ---------------------------------------------------------------------------
# LocalVectorStore — ChromaDB embedded
# ---------------------------------------------------------------------------

class LocalVectorStore(VectorStore):
    """ChromaDB PersistentClient. Distância cosseno. Coleção maia-rag."""

    def __init__(self, path: str, collection_name: str) -> None:
        import chromadb  # confinado aqui
        from chromadb.config import Settings as ChromaSettings

        self._client = chromadb.PersistentClient(
            path=path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        self._collection = self._client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def upsert(self, items: list[VectorItem]) -> None:
        if not items:
            return
        self._collection.upsert(
            ids=[item.id for item in items],
            embeddings=[item.vector for item in items],
            documents=[item.content for item in items],
            metadatas=[item.metadata for item in items],
        )

    def query(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict | None = None,
    ) -> list[QueryResult]:
        kwargs: dict[str, Any] = {
            "query_embeddings": [vector],
            "n_results": top_k,
            "include": ["documents", "metadatas", "distances"],
        }
        if filter:
            kwargs["where"] = filter

        results = self._collection.query(**kwargs)

        output: list[QueryResult] = []
        ids = results["ids"][0]
        docs = results["documents"][0]
        metas = results["metadatas"][0]
        distances = results["distances"][0]

        for qid, doc, meta, dist in zip(ids, docs, metas, distances):
            # Chroma cosine distance: 0 = idêntico, 2 = oposto
            # Converte para score 0-1 (1 = mais similar)
            score = 1.0 - (dist / 2.0)
            output.append(QueryResult(id=qid, content=doc, metadata=meta, score=score))

        return output

    def delete_by_filter(self, filter: dict) -> int:
        # Chroma não retorna contagem direta — busca IDs primeiro
        results = self._collection.get(where=filter, include=[])
        ids = results["ids"]
        if ids:
            self._collection.delete(ids=ids)
        return len(ids)

    def count(self) -> int:
        return self._collection.count()


# ---------------------------------------------------------------------------
# PineconeVectorStore — stub (sprint de promoção a produção)
# ---------------------------------------------------------------------------

class PineconeVectorStore(VectorStore):
    """
    Stub para Pinecone. Todos os métodos levantam NotImplementedError.
    __init__ valida envs para falhar cedo se mal configurado.
    """

    def __init__(self) -> None:
        try:
            import pinecone  # noqa: F401
        except ImportError:
            raise ImportError(
                "pinecone não instalado. Execute: pip install pinecone-client\n"
                "Nota: PineconeVectorStore será implementado na sprint de promoção a produção."
            )

        missing = [
            k for k, v in {
                "PINECONE_API_KEY": settings.PINECONE_API_KEY,
                "PINECONE_INDEX": settings.PINECONE_INDEX,
                "PINECONE_ENVIRONMENT": settings.PINECONE_ENVIRONMENT,
            }.items() if not v
        ]
        if missing:
            raise ValueError(
                f"PineconeVectorStore exige variáveis de ambiente: {', '.join(missing)}"
            )

    def upsert(self, items: list[VectorItem]) -> None:
        raise NotImplementedError(
            "PineconeVectorStore será implementado na sprint de promoção a produção. "
            "Por enquanto, use VECTOR_STORE_BACKEND=local."
        )

    def query(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict | None = None,
    ) -> list[QueryResult]:
        raise NotImplementedError(
            "PineconeVectorStore será implementado na sprint de promoção a produção. "
            "Por enquanto, use VECTOR_STORE_BACKEND=local."
        )

    def delete_by_filter(self, filter: dict) -> int:
        raise NotImplementedError(
            "PineconeVectorStore será implementado na sprint de promoção a produção. "
            "Por enquanto, use VECTOR_STORE_BACKEND=local."
        )

    def count(self) -> int:
        raise NotImplementedError(
            "PineconeVectorStore será implementado na sprint de promoção a produção. "
            "Por enquanto, use VECTOR_STORE_BACKEND=local."
        )


# ---------------------------------------------------------------------------
# Factory
# ---------------------------------------------------------------------------

def get_vector_store() -> VectorStore:
    """Retorna a implementação configurada via VECTOR_STORE_BACKEND."""
    backend = settings.VECTOR_STORE_BACKEND
    if backend == "local":
        return LocalVectorStore(
            path=settings.CHROMA_PATH,
            collection_name=settings.CHROMA_COLLECTION,
        )
    if backend == "pinecone":
        return PineconeVectorStore()
    raise ValueError(f"VECTOR_STORE_BACKEND inválido: '{backend}'. Use 'local' ou 'pinecone'.")
