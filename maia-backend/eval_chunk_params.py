"""
Benchmark de parâmetros de chunking para o RAG MaIA.

Testa todas as combinações de MAX_WORDS e OVERLAP_RATIO contra as 15 queries
anotadas em tests/rag/queries.jsonl, usando um ChromaDB temporário por
configuração (sem tocar no índice de produção).

Métricas por configuração:
  - Hit@1, Hit@3, Hit@5, Hit@10  (fração de queries com ≥1 arquivo esperado)
  - MRR@10  (Mean Reciprocal Rank — qualidade de ranqueamento)
  - NDCG@5, NDCG@10  (Normalized Discounted Cumulative Gain)
  - Média de chunks por arquivo, tokens por chunk, custo estimado de ingestão

Saída:
  data/chunk_benchmark/results.json  — dados brutos
  data/chunk_benchmark/report.md     — tabela + análise textual
  data/chunk_benchmark/plots/        — gráficos PNG (heatmaps + curvas)

Uso:
  # Dentro do container (acessa knowledge/ e ChromaDB temporário em /tmp)
  docker compose run --rm -v "$(pwd):/app" api python eval_chunk_params.py

  # Opções
  python eval_chunk_params.py --source /data/knowledge --top-k 5 10
  python eval_chunk_params.py --dry-run      # só mostra plano, sem embeddings
  python eval_chunk_params.py --no-plots     # pula matplotlib (sem display)

Custo estimado (~$0.02/1M tokens, text-embedding-3-small):
  Corpus ~215k tokens × N configurações = calcule antes de rodar.
  Com 12 combinações: ~$0.05 USD total.

ATENÇÃO: não modifica o índice de produção (.chroma/).
Cada configuração usa um ChromaDB efêmero em /tmp/maia_benchmark_<hash>/.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import math
import shutil
import sys
import tempfile
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from itertools import product
from pathlib import Path

import structlog

# ---------------------------------------------------------------------------
# Parâmetros a testar
# ---------------------------------------------------------------------------

WORD_SIZES = [500, 750, 1000, 1250, 1500]    # MAX_WORDS_PER_CHUNK
OVERLAP_RATIOS = [0.0, 0.10, 0.20]           # OVERLAP_RATIO
TOP_K_VALUES = [1, 3, 5, 10]                 # para Hit@k e NDCG@k

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

structlog.configure(
    wrapper_class=structlog.make_filtering_bound_logger(logging.INFO),
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.dev.ConsoleRenderer(),
    ],
)
log = structlog.get_logger()


# ---------------------------------------------------------------------------
# Tipos de resultado
# ---------------------------------------------------------------------------

@dataclass
class QueryResult:
    query_id: str
    query_text: str
    expected_files: list[str]
    returned_files: list[str]      # em ordem de ranque (top-10)
    scores: list[float]
    bloco: str


@dataclass
class ConfigResult:
    max_words: int
    overlap_ratio: float
    n_chunks: int
    avg_tokens_per_chunk: float
    cost_usd: float
    # Hit@k: fração de queries com ≥1 arquivo esperado no top-k
    hit_at: dict[int, float]
    # MRR@10
    mrr: float
    # NDCG@k
    ndcg_at: dict[int, float]
    # Por bloco
    hit_at_5_by_bloco: dict[str, float]
    per_query: list[QueryResult]
    elapsed_seconds: float


# ---------------------------------------------------------------------------
# Métricas
# ---------------------------------------------------------------------------

def _reciprocal_rank(returned: list[str], expected: set[str]) -> float:
    """1/rank do primeiro arquivo esperado encontrado. 0 se não encontrado."""
    for rank, f in enumerate(returned, start=1):
        if f in expected:
            return 1.0 / rank
    return 0.0


def _dcg(returned: list[str], expected: set[str], k: int) -> float:
    """Discounted Cumulative Gain até posição k. Relevância binária."""
    dcg = 0.0
    for rank, f in enumerate(returned[:k], start=1):
        if f in expected:
            dcg += 1.0 / math.log2(rank + 1)
    return dcg


def _ndcg(returned: list[str], expected: set[str], k: int) -> float:
    """NDCG@k. IDCG assume todos os relevantes nas primeiras posições."""
    n_relevant = len(expected)
    if n_relevant == 0:
        return 0.0
    ideal_hits = min(n_relevant, k)
    idcg = sum(1.0 / math.log2(i + 2) for i in range(ideal_hits))
    if idcg == 0:
        return 0.0
    return _dcg(returned, expected, k) / idcg


def compute_metrics(
    query_results: list[QueryResult],
    top_k_values: list[int],
) -> tuple[dict[int, float], float, dict[int, float]]:
    """Retorna (hit_at, mrr, ndcg_at)."""
    n = len(query_results)
    if n == 0:
        zeros = {k: 0.0 for k in top_k_values}
        return zeros, 0.0, zeros

    hit_at: dict[int, float] = {}
    for k in top_k_values:
        hits = sum(
            1 for r in query_results
            if set(r.returned_files[:k]) & set(r.expected_files)
        )
        hit_at[k] = hits / n

    mrr = sum(
        _reciprocal_rank(r.returned_files, set(r.expected_files))
        for r in query_results
    ) / n

    ndcg_at: dict[int, float] = {}
    for k in top_k_values:
        ndcg_at[k] = sum(
            _ndcg(r.returned_files, set(r.expected_files), k)
            for r in query_results
        ) / n

    return hit_at, mrr, ndcg_at


# ---------------------------------------------------------------------------
# Ingestão numa coleção temporária
# ---------------------------------------------------------------------------

def _temp_collection_name(max_words: int, overlap_ratio: float) -> str:
    key = f"bench_{max_words}_{overlap_ratio:.2f}"
    return "maia_bench_" + hashlib.sha256(key.encode()).hexdigest()[:12]


def ingest_to_temp_store(
    source_dir: Path,
    max_words: int,
    overlap_ratio: float,
    chroma_tmp_path: str,
) -> tuple[object, int, float]:
    """
    Ingere todo o knowledge/ com os parâmetros dados em uma coleção Chroma
    temporária (path isolado). Retorna (vector_store, n_chunks, cost_usd).

    Usa os módulos de produção (loaders, manifest, embeddings) mas overrides
    os parâmetros de chunking via monkey-patch local — sem alterar o módulo
    de produção em disco.
    """
    import chromadb
    from chromadb.config import Settings as ChromaSettings

    # Import módulos de produção
    from app.rag import chunking as chunking_mod
    from app.rag.chunking import chunk_essay, chunk_index
    from app.rag.embeddings import embed_texts, estimate_cost, estimate_tokens
    from app.rag.loaders import list_documents, load_document
    from app.rag.manifest import parse_manifest, validate_manifest

    # Monkey-patch dos parâmetros para esta run
    original_max = chunking_mod.MAX_WORDS_PER_CHUNK
    original_overlap = chunking_mod.OVERLAP_RATIO
    chunking_mod.MAX_WORDS_PER_CHUNK = max_words
    chunking_mod.OVERLAP_RATIO = overlap_ratio

    try:
        index_path = source_dir / "00-indice.md"
        manifest = parse_manifest(index_path)
        validate_manifest(manifest, source_dir)

        all_docs = list_documents(source_dir)

        # Coleção isolada
        col_name = _temp_collection_name(max_words, overlap_ratio)
        client = chromadb.PersistentClient(
            path=chroma_tmp_path,
            settings=ChromaSettings(anonymized_telemetry=False),
        )
        collection = client.get_or_create_collection(
            name=col_name,
            metadata={"hnsw:space": "cosine"},
        )

        total_chunks = 0
        total_tokens = 0
        ingested_at = datetime.now(timezone.utc).isoformat()

        for doc in all_docs:
            text = load_document(doc)
            is_index = doc.name == "00-indice.md"

            if is_index:
                chunks = chunk_index(text, source_file=doc.name)
            else:
                chunks = chunk_essay(text, source_file=doc.name)

            if not chunks:
                continue

            contents = [c.content for c in chunks]
            tokens_est = estimate_tokens(contents)
            total_tokens += tokens_est
            total_chunks += len(chunks)

            vectors = embed_texts(contents)

            # Metadata mínima para o benchmark (source_file obrigatório)
            manifest_entry = manifest.get(doc.name) if not is_index else None
            ids, embeddings, documents, metadatas = [], [], [], []
            for i, (chunk, vec) in enumerate(zip(chunks, vectors)):
                chunk_key = f"{doc.name}::{i}::{chunk.content[:100]}"
                chunk_id = hashlib.sha256(chunk_key.encode()).hexdigest()[:32]
                meta = {
                    "source_file": chunk.source_file,
                    "section_type": chunk.section_type,
                    "chunk_index": chunk.chunk_index,
                    "max_words_param": max_words,
                    "overlap_ratio_param": overlap_ratio,
                }
                if manifest_entry:
                    meta["bloco_tematico"] = manifest_entry.get("bloco_tematico", "")
                ids.append(chunk_id)
                embeddings.append(vec)
                documents.append(chunk.content)
                metadatas.append(meta)

            collection.upsert(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas,
            )

        cost_usd = estimate_cost(total_tokens)
        return collection, total_chunks, cost_usd

    finally:
        # Sempre restaura os parâmetros originais
        chunking_mod.MAX_WORDS_PER_CHUNK = original_max
        chunking_mod.OVERLAP_RATIO = original_overlap


# ---------------------------------------------------------------------------
# Avaliação de uma configuração
# ---------------------------------------------------------------------------

def eval_config(
    collection,
    queries: list[dict],
    top_k_values: list[int],
    n_chunks: int,
    cost_usd: float,
    max_words: int,
    overlap_ratio: float,
    elapsed: float,
) -> ConfigResult:
    from app.rag.embeddings import embed_single

    max_k = max(top_k_values)
    query_results: list[QueryResult] = []

    for q in queries:
        qid = q["id"]
        query_text = q["query"]
        expected = q.get("expected_files", [])
        bloco = q.get("bloco", "?")

        vector = embed_single(query_text)

        raw = collection.query(
            query_embeddings=[vector],
            n_results=max_k,
            include=["documents", "metadatas", "distances"],
        )
        returned_files_ordered = []
        scores = []
        seen = set()
        for meta, dist in zip(raw["metadatas"][0], raw["distances"][0]):
            src = meta.get("source_file", "?")
            score = 1.0 - (dist / 2.0)
            if src not in seen:
                returned_files_ordered.append(src)
                seen.add(src)
            scores.append(score)

        query_results.append(QueryResult(
            query_id=qid,
            query_text=query_text,
            expected_files=expected,
            returned_files=returned_files_ordered,
            scores=scores,
            bloco=bloco,
        ))

    hit_at, mrr, ndcg_at = compute_metrics(query_results, top_k_values)

    # Hit@5 por bloco
    blocos = sorted(set(r.bloco for r in query_results))
    hit_at_5_by_bloco: dict[str, float] = {}
    for bloco in blocos:
        bloco_queries = [r for r in query_results if r.bloco == bloco]
        if bloco_queries:
            hits = sum(
                1 for r in bloco_queries
                if set(r.returned_files[:5]) & set(r.expected_files)
            )
            hit_at_5_by_bloco[bloco] = hits / len(bloco_queries)

    return ConfigResult(
        max_words=max_words,
        overlap_ratio=overlap_ratio,
        n_chunks=n_chunks,
        avg_tokens_per_chunk=0.0,  # preenchido abaixo
        cost_usd=cost_usd,
        hit_at=hit_at,
        mrr=mrr,
        ndcg_at=ndcg_at,
        hit_at_5_by_bloco=hit_at_5_by_bloco,
        per_query=query_results,
        elapsed_seconds=elapsed,
    )


# ---------------------------------------------------------------------------
# Geração de relatório Markdown
# ---------------------------------------------------------------------------

def _fmt_pct(v: float) -> str:
    return f"{v*100:.1f}%"


def generate_report(results: list[ConfigResult], top_k_values: list[int]) -> str:
    lines = [
        "# Benchmark de Parâmetros de Chunking — MaIA RAG",
        f"\nGerado em: {datetime.now(timezone.utc).isoformat()}",
        f"Configurações testadas: {len(results)}",
        f"Queries: 15 (cobrindo blocos I–VI)",
        "",
    ]

    # --- Tabela principal ---
    ks = sorted(top_k_values)
    headers = ["max_words", "overlap", "n_chunks", "custo_USD"] + [f"Hit@{k}" for k in ks] + ["MRR@10"] + [f"NDCG@{k}" for k in ks]
    lines.append("## Resultados por Configuração")
    lines.append("")
    lines.append("| " + " | ".join(headers) + " |")
    lines.append("| " + " | ".join(["---"] * len(headers)) + " |")

    for r in sorted(results, key=lambda x: (-x.hit_at.get(5, 0), -x.mrr)):
        row = [
            str(r.max_words),
            f"{r.overlap_ratio:.0%}",
            str(r.n_chunks),
            f"${r.cost_usd:.4f}",
        ]
        for k in ks:
            row.append(_fmt_pct(r.hit_at.get(k, 0)))
        row.append(f"{r.mrr:.3f}")
        for k in ks:
            row.append(f"{r.ndcg_at.get(k, 0):.3f}")
        lines.append("| " + " | ".join(row) + " |")

    lines.append("")

    # --- Melhor configuração ---
    best = max(results, key=lambda x: (x.hit_at.get(5, 0), x.mrr, x.ndcg_at.get(5, 0)))
    lines += [
        "## Melhor Configuração (Hit@5 + MRR)",
        "",
        f"- **max_words:** {best.max_words}",
        f"- **overlap_ratio:** {best.overlap_ratio:.0%}",
        f"- **n_chunks:** {best.n_chunks}",
        f"- **Hit@5:** {_fmt_pct(best.hit_at.get(5, 0))}",
        f"- **MRR@10:** {best.mrr:.3f}",
        f"- **NDCG@5:** {best.ndcg_at.get(5, 0):.3f}",
        f"- **NDCG@10:** {best.ndcg_at.get(10, 0):.3f}",
        f"- **Custo estimado:** ${best.cost_usd:.4f} USD",
        "",
    ]

    # --- Hit@5 por bloco (melhor config) ---
    lines += [
        "## Hit@5 por Bloco Temático (Melhor Configuração)",
        "",
        "| Bloco | Hit@5 |",
        "|-------|-------|",
    ]
    for bloco, score in sorted(best.hit_at_5_by_bloco.items()):
        lines.append(f"| {bloco} | {_fmt_pct(score)} |")
    lines.append("")

    # --- Análise do efeito do overlap ---
    lines += [
        "## Efeito do Overlap (fixado max_words=1000)",
        "",
        "| overlap | Hit@5 | MRR@10 | NDCG@5 |",
        "|---------|-------|--------|--------|",
    ]
    for r in sorted(results, key=lambda x: x.overlap_ratio):
        if r.max_words == 1000:
            lines.append(
                f"| {r.overlap_ratio:.0%} | {_fmt_pct(r.hit_at.get(5,0))} | {r.mrr:.3f} | {r.ndcg_at.get(5,0):.3f} |"
            )
    lines.append("")

    # --- Análise do efeito do chunk size ---
    lines += [
        "## Efeito do Chunk Size (fixado overlap=10%)",
        "",
        "| max_words | n_chunks | Hit@5 | MRR@10 | NDCG@5 |",
        "|-----------|----------|-------|--------|--------|",
    ]
    for r in sorted(results, key=lambda x: x.max_words):
        if abs(r.overlap_ratio - 0.10) < 0.001:
            lines.append(
                f"| {r.max_words} | {r.n_chunks} | {_fmt_pct(r.hit_at.get(5,0))} | {r.mrr:.3f} | {r.ndcg_at.get(5,0):.3f} |"
            )
    lines.append("")

    # --- Detalhes por query (melhor config) ---
    lines += [
        "## Detalhes por Query (Melhor Configuração)",
        "",
        "| ID | Bloco | Hit@5 | MRR | Esperado | Top-1 Retornado |",
        "|----|-------|-------|-----|----------|-----------------|",
    ]
    for qr in best.per_query:
        hit5 = "✅" if set(qr.returned_files[:5]) & set(qr.expected_files) else "❌"
        rr = _reciprocal_rank(qr.returned_files, set(qr.expected_files))
        expected_str = ", ".join(qr.expected_files)
        top1 = qr.returned_files[0] if qr.returned_files else "—"
        lines.append(f"| {qr.query_id} | {qr.bloco} | {hit5} | {rr:.2f} | {expected_str} | {top1} |")
    lines.append("")

    # --- Recomendação ---
    lines += [
        "## Recomendação",
        "",
        f"Configuração recomendada com base nos dados: **max_words={best.max_words}, overlap={best.overlap_ratio:.0%}**.",
        "",
        "Para alterar a configuração de produção:",
        "1. Editar `MAX_WORDS_PER_CHUNK` e `OVERLAP_RATIO` em `app/rag/chunking.py`",
        "2. Deletar `.chroma/` e `data/ingest-state.json`",
        "3. Re-ingerir: `docker compose run --rm api python -m app.rag.ingest --source /data/knowledge --force`",
        "",
    ]

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Geração de gráficos
# ---------------------------------------------------------------------------

def generate_plots(results: list[ConfigResult], output_dir: Path) -> None:
    """
    Gera PNGs em output_dir/:
      heatmap_hit5.png  — Hit@5 por (max_words × overlap)
      heatmap_mrr.png   — MRR@10 por (max_words × overlap)
      heatmap_ndcg5.png — NDCG@5 por (max_words × overlap)
      curve_hit_at_k.png — Hit@k (k=1,3,5,10) para melhor configuração
      curve_chunk_size.png — Hit@5 × max_words (overlap=10%)
    """
    try:
        import matplotlib
        matplotlib.use("Agg")  # sem display
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        log.warning("matplotlib não instalado — gráficos pulados. pip install matplotlib")
        return

    output_dir.mkdir(parents=True, exist_ok=True)

    word_sizes = sorted(set(r.max_words for r in results))
    overlap_ratios = sorted(set(r.overlap_ratio for r in results))

    def build_matrix(metric_fn) -> np.ndarray:
        mat = np.zeros((len(overlap_ratios), len(word_sizes)))
        for r in results:
            i = overlap_ratios.index(r.overlap_ratio)
            j = word_sizes.index(r.max_words)
            mat[i, j] = metric_fn(r)
        return mat

    def save_heatmap(matrix, title, filename, fmt=".2f", vmin=0, vmax=1):
        fig, ax = plt.subplots(figsize=(8, 4))
        im = ax.imshow(matrix, aspect="auto", cmap="YlGn", vmin=vmin, vmax=vmax)
        ax.set_xticks(range(len(word_sizes)))
        ax.set_xticklabels([str(w) for w in word_sizes])
        ax.set_yticks(range(len(overlap_ratios)))
        ax.set_yticklabels([f"{o:.0%}" for o in overlap_ratios])
        ax.set_xlabel("max_words")
        ax.set_ylabel("overlap_ratio")
        ax.set_title(title)
        for i in range(len(overlap_ratios)):
            for j in range(len(word_sizes)):
                ax.text(j, i, f"{matrix[i,j]:{fmt}}", ha="center", va="center",
                        color="black", fontsize=10)
        plt.colorbar(im, ax=ax)
        plt.tight_layout()
        fig.savefig(output_dir / filename, dpi=150)
        plt.close(fig)
        log.info("plot.saved", file=filename)

    save_heatmap(build_matrix(lambda r: r.hit_at.get(5, 0)), "Hit@5", "heatmap_hit5.png")
    save_heatmap(build_matrix(lambda r: r.mrr), "MRR@10", "heatmap_mrr.png")
    save_heatmap(build_matrix(lambda r: r.ndcg_at.get(5, 0)), "NDCG@5", "heatmap_ndcg5.png")

    # Curva Hit@k para melhor config
    best = max(results, key=lambda x: (x.hit_at.get(5, 0), x.mrr))
    ks = sorted(best.hit_at.keys())
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(ks, [best.hit_at[k] for k in ks], marker="o", linewidth=2)
    ax.set_xlabel("k")
    ax.set_ylabel("Hit@k")
    ax.set_title(f"Hit@k — Melhor config (max_words={best.max_words}, overlap={best.overlap_ratio:.0%})")
    ax.set_ylim(0, 1.05)
    ax.set_xticks(ks)
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig(output_dir / "curve_hit_at_k.png", dpi=150)
    plt.close(fig)

    # Curva Hit@5 × chunk size (overlap=10%)
    overlap_10 = [r for r in results if abs(r.overlap_ratio - 0.10) < 0.001]
    overlap_10 = sorted(overlap_10, key=lambda r: r.max_words)
    if overlap_10:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot([r.max_words for r in overlap_10], [r.hit_at.get(5, 0) for r in overlap_10],
                marker="o", linewidth=2, label="Hit@5")
        ax.plot([r.max_words for r in overlap_10], [r.mrr for r in overlap_10],
                marker="s", linewidth=2, linestyle="--", label="MRR@10")
        ax.plot([r.max_words for r in overlap_10], [r.ndcg_at.get(5, 0) for r in overlap_10],
                marker="^", linewidth=2, linestyle=":", label="NDCG@5")
        ax.set_xlabel("max_words_per_chunk")
        ax.set_ylabel("Score")
        ax.set_title("Qualidade × Chunk Size (overlap=10%)")
        ax.set_ylim(0, 1.05)
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / "curve_chunk_size.png", dpi=150)
        plt.close(fig)

    # Curva Hit@5 × overlap (fixado max_words=1000)
    size_1000 = [r for r in results if r.max_words == 1000]
    size_1000 = sorted(size_1000, key=lambda r: r.overlap_ratio)
    if size_1000:
        fig, ax = plt.subplots(figsize=(7, 4))
        ax.plot([r.overlap_ratio for r in size_1000], [r.hit_at.get(5, 0) for r in size_1000],
                marker="o", linewidth=2, label="Hit@5")
        ax.plot([r.overlap_ratio for r in size_1000], [r.mrr for r in size_1000],
                marker="s", linewidth=2, linestyle="--", label="MRR@10")
        ax.set_xlabel("overlap_ratio")
        ax.set_ylabel("Score")
        ax.set_title("Qualidade × Overlap (max_words=1000)")
        ax.set_ylim(0, 1.05)
        ax.set_xticks([r.overlap_ratio for r in size_1000])
        ax.set_xticklabels([f"{r.overlap_ratio:.0%}" for r in size_1000])
        ax.legend()
        ax.grid(True, alpha=0.3)
        plt.tight_layout()
        fig.savefig(output_dir / "curve_overlap.png", dpi=150)
        plt.close(fig)

    log.info("plots.done", output_dir=str(output_dir))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Benchmark de parâmetros de chunking — MaIA RAG")
    parser.add_argument("--source", type=Path, default=Path("/data/knowledge"),
                        help="Pasta knowledge/ (default: /data/knowledge)")
    parser.add_argument("--top-k", type=int, nargs="+", default=TOP_K_VALUES,
                        help="Valores de k para Hit@k e NDCG@k (default: 1 3 5 10)")
    parser.add_argument("--word-sizes", type=int, nargs="+", default=WORD_SIZES,
                        help="Valores de MAX_WORDS_PER_CHUNK a testar")
    parser.add_argument("--overlaps", type=float, nargs="+", default=OVERLAP_RATIOS,
                        help="Valores de OVERLAP_RATIO a testar (ex: 0.0 0.10 0.20)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Mostra plano (configurações + custo estimado) sem rodar embeddings")
    parser.add_argument("--no-plots", action="store_true",
                        help="Pula geração de gráficos (útil sem display ou matplotlib)")
    parser.add_argument("--keep-tmp", action="store_true",
                        help="Não deletar ChromaDBs temporários após o benchmark")
    args = parser.parse_args()

    source_dir: Path = args.source
    if not source_dir.exists():
        log.error("source_dir.not_found", path=str(source_dir))
        sys.exit(1)

    queries_path = Path("tests/rag/queries.jsonl")
    if not queries_path.exists():
        log.error("queries.not_found", path=str(queries_path))
        sys.exit(1)

    queries: list[dict] = []
    with open(queries_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                queries.append(json.loads(line))

    configs = list(product(sorted(args.word_sizes), sorted(args.overlaps)))
    n_configs = len(configs)

    # Estimativa de custo
    from app.rag.embeddings import estimate_cost, estimate_tokens
    from app.rag.loaders import list_documents, load_document
    all_docs = list_documents(source_dir)
    total_words_corpus = sum(
        len(load_document(d).split()) for d in all_docs
    )
    tokens_per_ingest = int(total_words_corpus * 1.3)
    cost_per_config = estimate_cost(tokens_per_ingest)
    total_cost = cost_per_config * n_configs

    log.info(
        "benchmark.plan",
        configs=n_configs,
        corpus_words=total_words_corpus,
        tokens_per_config=tokens_per_ingest,
        cost_per_config_usd=round(cost_per_config, 4),
        total_cost_usd=round(total_cost, 4),
    )

    print(f"\n📋 Plano do benchmark:")
    print(f"   Configurações: {n_configs}  ({len(args.word_sizes)} chunk sizes × {len(args.overlaps)} overlaps)")
    print(f"   Queries:       {len(queries)}")
    print(f"   Corpus:        ~{total_words_corpus:,} palavras")
    print(f"   Custo por config: ~${cost_per_config:.4f} USD")
    print(f"   Custo TOTAL:   ~${total_cost:.4f} USD")

    if args.dry_run:
        print("\n✅ Dry-run concluído. Sem embeddings gerados.")
        return

    confirm = input(f"\nProsseguir? Custo estimado: ~${total_cost:.4f} USD  [s/N] ").strip().lower()
    if confirm not in ("s", "sim", "y", "yes"):
        print("Cancelado.")
        sys.exit(0)

    # Pasta de saída
    output_dir = Path("data/chunk_benchmark")
    output_dir.mkdir(parents=True, exist_ok=True)
    plots_dir = output_dir / "plots"

    results: list[ConfigResult] = []
    tmp_dirs: list[str] = []

    total_start = time.time()

    for idx, (max_words, overlap_ratio) in enumerate(configs, start=1):
        log.info(
            "config.start",
            idx=idx,
            total=n_configs,
            max_words=max_words,
            overlap_ratio=overlap_ratio,
        )
        print(f"\n[{idx}/{n_configs}] max_words={max_words}, overlap={overlap_ratio:.0%}")

        tmp_dir = tempfile.mkdtemp(prefix=f"maia_bench_{max_words}_{int(overlap_ratio*100)}_")
        tmp_dirs.append(tmp_dir)

        t0 = time.time()
        collection, n_chunks, cost_usd = ingest_to_temp_store(
            source_dir=source_dir,
            max_words=max_words,
            overlap_ratio=overlap_ratio,
            chroma_tmp_path=tmp_dir,
        )
        elapsed_ingest = time.time() - t0
        log.info("config.ingest_done", n_chunks=n_chunks, cost_usd=round(cost_usd, 4),
                 elapsed=round(elapsed_ingest, 1))

        result = eval_config(
            collection=collection,
            queries=queries,
            top_k_values=sorted(args.top_k),
            n_chunks=n_chunks,
            cost_usd=cost_usd,
            max_words=max_words,
            overlap_ratio=overlap_ratio,
            elapsed=time.time() - t0,
        )
        results.append(result)

        print(f"   n_chunks={n_chunks}  Hit@5={result.hit_at.get(5,0):.1%}  "
              f"MRR={result.mrr:.3f}  NDCG@5={result.ndcg_at.get(5,0):.3f}")

    total_elapsed = time.time() - total_start

    # Salva JSON raw
    raw_path = output_dir / "results.json"
    serializable = []
    for r in results:
        d = asdict(r)
        # hit_at/ndcg_at têm chaves int — converter para str para JSON
        d["hit_at"] = {str(k): v for k, v in d["hit_at"].items()}
        d["ndcg_at"] = {str(k): v for k, v in d["ndcg_at"].items()}
        serializable.append(d)
    raw_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")
    log.info("results.json.written", path=str(raw_path))

    # Relatório Markdown
    report = generate_report(results, sorted(args.top_k))
    report_path = output_dir / "report.md"
    report_path.write_text(report, encoding="utf-8")
    log.info("report.written", path=str(report_path))

    # Gráficos
    if not args.no_plots:
        generate_plots(results, plots_dir)

    # Limpa temporários
    if not args.keep_tmp:
        for d in tmp_dirs:
            shutil.rmtree(d, ignore_errors=True)
        log.info("tmp_dirs.cleaned", count=len(tmp_dirs))

    best = max(results, key=lambda x: (x.hit_at.get(5, 0), x.mrr))
    print(f"\n✅ Benchmark concluído em {total_elapsed:.0f}s")
    print(f"   Melhor config: max_words={best.max_words}, overlap={best.overlap_ratio:.0%}")
    print(f"   Hit@5={best.hit_at.get(5,0):.1%}  MRR={best.mrr:.3f}  NDCG@5={best.ndcg_at.get(5,0):.3f}")
    print(f"   Relatório: {report_path}")
    if not args.no_plots:
        print(f"   Gráficos:  {plots_dir}/")


if __name__ == "__main__":
    main()
