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
# PineconeVectorStore — implementação real
# ---------------------------------------------------------------------------

class PineconeVectorStore(VectorStore):
    """
    Pinecone serverless. Índice deve ser criado manualmente no dashboard
    com dimensão 1536 (text-embedding-3-small) e métrica cosine.
    """

    # Pinecone aceita no máximo 100 vetores por upsert
    _UPSERT_BATCH = 100

    def __init__(self) -> None:
        try:
            from pinecone import Pinecone
        except ImportError:
            raise ImportError(
                "pinecone não instalado. Execute: pip install pinecone-client"
            )

        missing = [
            k for k, v in {
                "PINECONE_API_KEY": settings.PINECONE_API_KEY,
                "PINECONE_INDEX": settings.PINECONE_INDEX,
            }.items() if not v
        ]
        if missing:
            raise ValueError(
                f"PineconeVectorStore exige variáveis de ambiente: {', '.join(missing)}"
            )

        pc = Pinecone(api_key=settings.PINECONE_API_KEY)
        self._index = pc.Index(settings.PINECONE_INDEX)

    def upsert(self, items: list[VectorItem]) -> None:
        if not items:
            return
        vectors = [
            {
                "id": item.id,
                "values": item.vector,
                "metadata": {**item.metadata, "_content": item.content},
            }
            for item in items
        ]
        # Envia em batches de 100
        for i in range(0, len(vectors), self._UPSERT_BATCH):
            self._index.upsert(vectors=vectors[i : i + self._UPSERT_BATCH])

    def query(
        self,
        vector: list[float],
        top_k: int = 5,
        filter: dict | None = None,
    ) -> list[QueryResult]:
        kwargs: dict[str, Any] = {
            "vector": vector,
            "top_k": top_k,
            "include_metadata": True,
        }
        if filter:
            kwargs["filter"] = filter

        response = self._index.query(**kwargs)

        results: list[QueryResult] = []
        for match in response.matches:
            meta = dict(match.metadata or {})
            content = meta.pop("_content", "")
            results.append(QueryResult(
                id=match.id,
                content=content,
                metadata=meta,
                score=float(match.score),
            ))
        return results

    def delete_by_filter(self, filter: dict) -> int:
        # Pinecone serverless free tier não suporta delete by filter diretamente —
        # busca IDs primeiro via query com vetor zero, depois deleta por ID.
        # Limitado a 10k resultados por chamada.
        zero_vector = [0.0] * 1536
        response = self._index.query(
            vector=zero_vector,
            top_k=10000,
            filter=filter,
            include_metadata=False,
        )
        ids = [m.id for m in response.matches]
        if ids:
            self._index.delete(ids=ids)
        return len(ids)

    def count(self) -> int:
        stats = self._index.describe_index_stats()
        return stats.total_vector_count


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
