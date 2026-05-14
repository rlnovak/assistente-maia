"""
Chunking semântico por H2.

Estratégia (conforme CLAUDE_CODE_LOCAL_DEV.md §3.4 e §3.5):
- Unidade base: cada ## H2 dentro do arquivo
- Tamanho típico: 400–1200 palavras (autocontido)
- Subdivisão: se seção > MAX_WORDS_PER_CHUNK, divide por parágrafo com overlap
- section_type: visao_geral | conteudo | glossario | referencias
- Para 00-indice.md: chunking por bloco temático (## Bloco I, II, ...)
  com section_type: indice_visao_geral | indice_referencias_cruzadas | conteudo
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

# ~1500 tokens ≈ 1000–1100 palavras (proporção ~1.3 tokens/palavra)
MAX_WORDS_PER_CHUNK = 1000
OVERLAP_RATIO = 0.10  # 10% overlap entre sub-chunks


@dataclass
class RawChunk:
    content: str
    section_h2: str
    section_type: str
    chunk_index: int
    source_file: str


# ---------------------------------------------------------------------------
# Detecção de section_type
# ---------------------------------------------------------------------------

def _detect_section_type(h2_title: str, chunk_index: int) -> str:
    title_lower = h2_title.lower().strip()
    if "glossário" in title_lower or "glossario" in title_lower:
        return "glossario"
    if "referência" in title_lower or "referencia" in title_lower or title_lower.startswith("ref"):
        return "referencias"
    if chunk_index == 0:
        return "visao_geral"
    return "conteudo"


# ---------------------------------------------------------------------------
# Chunking de ensaios normais (01-19)
# ---------------------------------------------------------------------------

def chunk_essay(text: str, source_file: str) -> list[RawChunk]:
    """
    Divide o texto de um ensaio em chunks por H2.
    Preserva o título H2 como primeira linha de cada chunk.
    Subdivide seções muito longas respeitando fronteiras de parágrafo.
    """
    sections = _split_by_h2(text)
    chunks: list[RawChunk] = []
    chunk_index = 0

    for section_idx, (h2_title, section_body) in enumerate(sections):
        section_type = _detect_section_type(h2_title, section_idx)
        full_content = f"## {h2_title}\n\n{section_body}".strip()
        words = len(full_content.split())

        if words <= MAX_WORDS_PER_CHUNK:
            chunks.append(RawChunk(
                content=full_content,
                section_h2=h2_title,
                section_type=section_type,
                chunk_index=chunk_index,
                source_file=source_file,
            ))
            chunk_index += 1
        else:
            # Subdivide por parágrafo com overlap
            sub_chunks = _subdivide_by_paragraph(
                h2_title=h2_title,
                body=section_body,
                section_type=section_type,
                source_file=source_file,
                start_chunk_index=chunk_index,
            )
            chunks.extend(sub_chunks)
            chunk_index += len(sub_chunks)

    return chunks


def _split_by_h2(text: str) -> list[tuple[str, str]]:
    """
    Divide texto por H2 (## Título).
    Retorna lista de (h2_title, body_text).
    Conteúdo antes do primeiro H2 é descartado (metadados HTML do corpus).
    """
    h2_re = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    matches = list(h2_re.finditer(text))

    if not matches:
        # Arquivo sem H2 — trata como chunk único com título genérico
        return [("Conteúdo", text.strip())]

    sections: list[tuple[str, str]] = []
    for i, match in enumerate(matches):
        h2_title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:  # ignora seções vazias
            sections.append((h2_title, body))

    return sections


def _subdivide_by_paragraph(
    h2_title: str,
    body: str,
    section_type: str,
    source_file: str,
    start_chunk_index: int,
) -> list[RawChunk]:
    """
    Divide body em sub-chunks respeitando fronteiras de parágrafo.
    Mantém o título H2 como cabeçalho de cada sub-chunk.
    Aplica overlap de ~10% (últimos N parágrafos do chunk anterior).
    """
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]
    sub_chunks: list[RawChunk] = []
    current_paras: list[str] = []
    current_words = 0
    chunk_index = start_chunk_index

    overlap_paras: list[str] = []

    for para in paragraphs:
        para_words = len(para.split())

        if current_words + para_words > MAX_WORDS_PER_CHUNK and current_paras:
            content = f"## {h2_title}\n\n" + "\n\n".join(current_paras)
            sub_chunks.append(RawChunk(
                content=content.strip(),
                section_h2=h2_title,
                section_type=section_type,
                chunk_index=chunk_index,
                source_file=source_file,
            ))
            chunk_index += 1

            # Overlap: pega últimos parágrafos que somam ~10% do limite
            overlap_target = int(MAX_WORDS_PER_CHUNK * OVERLAP_RATIO)
            overlap_paras = []
            overlap_words = 0
            for p in reversed(current_paras):
                pw = len(p.split())
                if overlap_words + pw <= overlap_target:
                    overlap_paras.insert(0, p)
                    overlap_words += pw
                else:
                    break

            current_paras = overlap_paras + [para]
            current_words = sum(len(p.split()) for p in current_paras)
        else:
            current_paras.append(para)
            current_words += para_words

    # Último sub-chunk
    if current_paras:
        content = f"## {h2_title}\n\n" + "\n\n".join(current_paras)
        sub_chunks.append(RawChunk(
            content=content.strip(),
            section_h2=h2_title,
            section_type=section_type,
            chunk_index=chunk_index,
            source_file=source_file,
        ))

    return sub_chunks


# ---------------------------------------------------------------------------
# Chunking do 00-indice.md (tratamento diferenciado)
# ---------------------------------------------------------------------------

def chunk_index(text: str, source_file: str = "00-indice.md") -> list[RawChunk]:
    """
    Chunking conservador do índice mestre.
    - Tabela "Visão de conjunto" → chunk separado (section_type: indice_visao_geral)
    - "Mapa de referências cruzadas" → chunk separado (indice_referencias_cruzadas)
    - Cada "## Bloco I/II/III/..." → chunk único (conteudo)
    - Seção "Notas para uso..." → chunk conteudo
    """
    chunks: list[RawChunk] = []
    chunk_index_counter = 0

    # Divide por H2
    h2_re = re.compile(r"^##\s+(.+)$", re.MULTILINE)
    matches = list(h2_re.finditer(text))

    for i, match in enumerate(matches):
        h2_title = match.group(1).strip()
        start = match.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        if not body:
            continue

        title_lower = h2_title.lower()
        if "visão de conjunto" in title_lower or "visao de conjunto" in title_lower:
            section_type = "indice_visao_geral"
        elif "mapa de referência" in title_lower or "mapa de referencia" in title_lower:
            section_type = "indice_referencias_cruzadas"
        else:
            section_type = "conteudo"

        content = f"## {h2_title}\n\n{body}".strip()
        chunks.append(RawChunk(
            content=content,
            section_h2=h2_title,
            section_type=section_type,
            chunk_index=chunk_index_counter,
            source_file=source_file,
        ))
        chunk_index_counter += 1

    return chunks
