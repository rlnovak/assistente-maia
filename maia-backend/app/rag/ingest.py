"""
CLI de ingestão RAG.

Uso:
    python -m app.rag.ingest --source /data/knowledge

Flags:
    --source    Caminho da pasta knowledge (default: /data/knowledge)
    --force     Re-ingere todos os arquivos mesmo sem mudanças
    --dry-run   Mostra plano sem gravar embeddings
"""
from __future__ import annotations

import argparse
import hashlib
import json
import logging
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import structlog

from app.rag.chunking import RawChunk, chunk_essay, chunk_index
from app.rag.embeddings import embed_texts, estimate_cost, estimate_tokens
from app.rag.loaders import list_documents, load_document
from app.rag.manifest import parse_manifest, validate_manifest
from app.rag.vector_store import VectorItem, get_vector_store

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

# Caminho persistente do estado de hashes (dentro do container, no volume .chroma)
STATE_PATH = Path("data/ingest-state.json")


# ---------------------------------------------------------------------------
# Hash tracking
# ---------------------------------------------------------------------------

def _file_hash(path: Path) -> str:
    """SHA-256 do conteúdo do arquivo."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load_state() -> dict[str, str]:
    """Carrega {filename: hash} do state file. Retorna dict vazio se não existe."""
    if STATE_PATH.exists():
        try:
            return json.loads(STATE_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            return {}
    return {}


def _save_state(state: dict[str, str]) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False), encoding="utf-8")


# ---------------------------------------------------------------------------
# ID determinístico de chunk
# ---------------------------------------------------------------------------

def _chunk_id(source_file: str, chunk_index: int, content: str) -> str:
    key = f"{source_file}::{chunk_index}::{content[:200]}"
    return hashlib.sha256(key.encode()).hexdigest()[:32]


# ---------------------------------------------------------------------------
# Construção de metadata
# ---------------------------------------------------------------------------

def _build_metadata(
    chunk: RawChunk,
    manifest_entry: dict | None,
    ingested_at: str,
    is_manifest: bool = False,
) -> dict:
    meta: dict = {
        "source_file": chunk.source_file,
        "chunk_index": chunk.chunk_index,
        "section_h2": chunk.section_h2,
        "section_type": chunk.section_type,
        "ingested_at": ingested_at,
        "is_manifest": is_manifest,
        "content_preview": chunk.content[:200],
    }

    if is_manifest:
        meta["file_number"] = 0
        meta["bloco_tematico"] = "0"
        meta["bloco_nome"] = "Índice mestre"
    elif manifest_entry:
        meta["file_number"] = manifest_entry.get("file_number", 0)
        meta["file_title"] = manifest_entry.get("file_title", "")
        meta["bloco_tematico"] = manifest_entry.get("bloco_tematico", "")
        meta["bloco_nome"] = manifest_entry.get("bloco_nome", "")
        meta["tema_central"] = manifest_entry.get("tema_central", "")
        meta["descricao_curta"] = manifest_entry.get("descricao_curta", "")
        meta["palavras_chave_csv"] = manifest_entry.get("palavras_chave_csv", "")
        meta["autoridades_csv"] = manifest_entry.get("autoridades_csv", "")
        meta["ver_tambem_csv"] = manifest_entry.get("ver_tambem_csv", "")
        meta["palavras_count"] = manifest_entry.get("palavras_count", 0)
        meta["refs_count"] = manifest_entry.get("refs_count", 0)

    # Chroma não aceita None — omite campos vazios
    return {k: v for k, v in meta.items() if v is not None and v != ""}


# ---------------------------------------------------------------------------
# Ingestão de um arquivo
# ---------------------------------------------------------------------------

def ingest_file(
    path: Path,
    manifest_entry: dict | None,
    vector_store,
    ingested_at: str,
    dry_run: bool = False,
    is_index: bool = False,
) -> dict:
    """Ingere um arquivo. Retorna summary dict."""
    log.info("ingest_file.start", file=path.name)

    text = load_document(path)
    is_manifest_doc = is_index or path.name == "00-indice.md"

    if is_manifest_doc:
        chunks = chunk_index(text, source_file=path.name)
    else:
        chunks = chunk_essay(text, source_file=path.name)

    if not chunks:
        log.warning("ingest_file.no_chunks", file=path.name)
        return {"file": path.name, "chunks": 0, "tokens_estimated": 0, "skipped": False}

    contents = [c.content for c in chunks]
    tokens_est = estimate_tokens(contents)

    if dry_run:
        log.info("ingest_file.dry_run", file=path.name, chunks=len(chunks), tokens=tokens_est)
        return {"file": path.name, "chunks": len(chunks), "tokens_estimated": tokens_est, "skipped": False}

    # Deleta chunks antigos deste arquivo antes de reingerir
    deleted = vector_store.delete_by_filter({"source_file": path.name})
    if deleted:
        log.info("ingest_file.deleted_old_chunks", file=path.name, deleted=deleted)

    vectors = embed_texts(contents)

    items: list[VectorItem] = []
    for chunk, vector in zip(chunks, vectors):
        meta = _build_metadata(
            chunk=chunk,
            manifest_entry=manifest_entry,
            ingested_at=ingested_at,
            is_manifest=is_manifest_doc,
        )
        items.append(VectorItem(
            id=_chunk_id(chunk.source_file, chunk.chunk_index, chunk.content),
            vector=vector,
            metadata=meta,
            content=chunk.content,
        ))

    vector_store.upsert(items)
    log.info("ingest_file.done", file=path.name, chunks=len(chunks), tokens=tokens_est)

    return {"file": path.name, "chunks": len(chunks), "tokens_estimated": tokens_est, "skipped": False}


# ---------------------------------------------------------------------------
# Inventário
# ---------------------------------------------------------------------------

def write_inventory(source_dir: Path, docs: list[Path], output_path: Path) -> None:
    lines = [
        "# RAG Inventory",
        f"\nGerado em: {datetime.now(timezone.utc).isoformat()}",
        f"Fonte: `{source_dir}`",
        f"Total de arquivos: {len(docs)}",
        "\n| Arquivo | Tamanho (KB) |",
        "|---------|-------------|",
    ]
    for doc in docs:
        size_kb = round(doc.stat().st_size / 1024, 1)
        lines.append(f"| `{doc.name}` | {size_kb} |")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines), encoding="utf-8")
    log.info("inventory.written", path=str(output_path))


# ---------------------------------------------------------------------------
# CLI principal
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="MaIA RAG Ingestor")
    parser.add_argument(
        "--source",
        type=Path,
        default=Path("/data/knowledge"),
        help="Caminho da pasta knowledge (default: /data/knowledge)",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Re-ingere todos os arquivos mesmo sem mudanças",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Mostra plano sem gravar embeddings",
    )
    args = parser.parse_args()

    source_dir: Path = args.source
    if not source_dir.exists():
        log.error("source_dir.not_found", path=str(source_dir))
        sys.exit(1)

    start_time = time.time()
    ingested_at = datetime.now(timezone.utc).isoformat()

    log.info("ingest.start", source=str(source_dir), dry_run=args.dry_run, force=args.force)

    # --- Parse e validação do manifesto ---
    index_path = source_dir / "00-indice.md"
    if not index_path.exists():
        log.error("manifest.not_found", path=str(index_path))
        sys.exit(1)

    log.info("manifest.parsing")
    manifest = parse_manifest(index_path)

    log.info("manifest.validating")
    try:
        validate_manifest(manifest, source_dir)
    except RuntimeError as e:
        log.error("manifest.validation_failed", error=str(e))
        print(f"\n❌ {e}\n", file=sys.stderr)
        sys.exit(1)

    log.info("manifest.ok", essays=len(manifest))

    # --- Inventário ---
    all_docs = list_documents(source_dir)
    essay_docs = [d for d in all_docs if d.name != "00-indice.md"]

    inventory_path = Path("docs/rag-inventory.md")
    write_inventory(source_dir, all_docs, inventory_path)

    # --- Hash state (skip inalterados) ---
    saved_state = _load_state() if not args.force else {}
    new_state: dict[str, str] = {}

    # --- Vector store ---
    if not args.dry_run:
        vector_store = get_vector_store()
        log.info("vector_store.ready", count_before=vector_store.count())
    else:
        vector_store = None

    # --- Ingestão dos 19 ensaios ---
    results = []
    total_tokens = 0
    skipped = 0

    all_to_process = essay_docs + [index_path]

    for doc in all_to_process:
        current_hash = _file_hash(doc)
        new_state[doc.name] = current_hash

        is_index = doc.name == "00-indice.md"

        if not args.force and saved_state.get(doc.name) == current_hash:
            log.info("ingest_file.skipped", file=doc.name, reason="unchanged")
            results.append({"file": doc.name, "chunks": 0, "tokens_estimated": 0, "skipped": True})
            skipped += 1
            continue

        manifest_entry = manifest.get(doc.name) if not is_index else None

        result = ingest_file(
            path=doc,
            manifest_entry=manifest_entry,
            vector_store=vector_store,
            ingested_at=ingested_at,
            dry_run=args.dry_run,
            is_index=is_index,
        )
        results.append(result)
        total_tokens += result.get("tokens_estimated", 0)

    # Persiste state atualizado
    if not args.dry_run:
        _save_state(new_state)
        log.info("state.saved", path=str(STATE_PATH), files=len(new_state))

    # --- Summary ---
    elapsed = time.time() - start_time
    cost_usd = estimate_cost(total_tokens)
    total_chunks = sum(r.get("chunks", 0) for r in results)
    processed = len(results) - skipped

    if not args.dry_run:
        count_after = vector_store.count()
    else:
        count_after = total_chunks

    summary = {
        "ingested_at": ingested_at,
        "source": str(source_dir),
        "dry_run": args.dry_run,
        "force": args.force,
        "files_processed": processed,
        "files_skipped": skipped,
        "total_chunks": total_chunks,
        "total_tokens_estimated": total_tokens,
        "cost_usd_estimated": round(cost_usd, 6),
        "vector_store_count_after": count_after,
        "elapsed_seconds": round(elapsed, 2),
        "files": results,
    }

    if not args.dry_run:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S")
        summary_path = Path(f"data/rag-ingestion-{ts}.json")
        summary_path.parent.mkdir(parents=True, exist_ok=True)
        summary_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        log.info("summary.written", path=str(summary_path))

    log.info(
        "ingest.complete",
        files_processed=processed,
        files_skipped=skipped,
        chunks=total_chunks,
        tokens=total_tokens,
        cost_usd=round(cost_usd, 6),
        vector_store_count=count_after,
        elapsed_s=round(elapsed, 2),
    )

    print(f"\n✅ Ingestão {'(dry-run) ' if args.dry_run else ''}concluída:")
    print(f"   Processados: {processed}  |  Pulados (sem mudança): {skipped}")
    print(f"   Chunks:      {total_chunks}")
    print(f"   Tokens:      ~{total_tokens:,}")
    print(f"   Custo:       ~${cost_usd:.4f} USD")
    print(f"   Tempo:       {round(elapsed, 2)}s")
    if not args.dry_run:
        print(f"   Total no vector store: {count_after}")


if __name__ == "__main__":
    main()
