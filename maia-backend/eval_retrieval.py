"""
Avaliação qualitativa do pipeline RAG.

Uso:
    python eval_retrieval.py
    python eval_retrieval.py --top-k 5
    python eval_retrieval.py --query-id q07
    python eval_retrieval.py --bloco III

Saída: resultados por query com score, arquivo, section_type e preview do chunk.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def load_queries(path: Path) -> list[dict]:
    queries = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))
    return queries


def run_eval(top_k: int, query_id: str | None, bloco: str | None) -> None:
    from app.rag.embeddings import embed_single
    from app.rag.vector_store import get_vector_store

    queries_path = Path("tests/rag/queries.jsonl")
    if not queries_path.exists():
        print(f"❌ Arquivo não encontrado: {queries_path}", file=sys.stderr)
        sys.exit(1)

    queries = load_queries(queries_path)

    # Filtros opcionais
    if query_id:
        queries = [q for q in queries if q["id"] == query_id]
    if bloco:
        queries = [q for q in queries if q.get("bloco") == bloco]

    if not queries:
        print("Nenhuma query encontrada com os filtros fornecidos.", file=sys.stderr)
        sys.exit(1)

    vs = get_vector_store()
    total = vs.count()
    print(f"\n📚 Vector store: {total} chunks\n")
    print("=" * 80)

    hits = 0
    total_queries = len(queries)

    for q in queries:
        qid = q["id"]
        query_text = q["query"]
        expected = set(q.get("expected_files", []))
        bloco_label = q.get("bloco", "?")

        print(f"\n[{qid}] Bloco {bloco_label}")
        print(f"Query: {query_text}")
        print(f"Esperado: {sorted(expected)}")
        print("-" * 60)

        vector = embed_single(query_text)
        results = vs.query(vector=vector, top_k=top_k)

        returned_files = set()
        for i, r in enumerate(results, 1):
            src = r.metadata.get("source_file", "?")
            section = r.metadata.get("section_type", "?")
            bloco_meta = r.metadata.get("bloco_tematico", "?")
            score = r.score
            preview = r.content[:120].replace("\n", " ")

            returned_files.add(src)
            match_marker = "✅" if src in expected else "  "
            print(f"  {match_marker} {i}. [{score:.3f}] {src} | {section} | bloco {bloco_meta}")
            print(f"      {preview}…")

        # Hit = pelo menos 1 arquivo esperado no top-k
        hit = bool(returned_files & expected)
        if hit:
            hits += 1
        print(f"\n  → Hit: {'✅ SIM' if hit else '❌ NÃO'}")
        print("=" * 80)

    print(f"\n📊 Resultado: {hits}/{total_queries} queries com pelo menos 1 arquivo esperado no top-{top_k}")
    pct = (hits / total_queries * 100) if total_queries else 0
    print(f"   Hit rate: {pct:.0f}%\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Avaliação qualitativa do RAG MaIA")
    parser.add_argument("--top-k", type=int, default=5, help="Número de resultados por query (default: 5)")
    parser.add_argument("--query-id", type=str, default=None, help="Rodar só uma query (ex: q07)")
    parser.add_argument("--bloco", type=str, default=None, help="Filtrar por bloco temático (ex: III)")
    args = parser.parse_args()

    run_eval(top_k=args.top_k, query_id=args.query_id, bloco=args.bloco)


if __name__ == "__main__":
    main()
