"""
Parser do 00-indice.md — extrai metadata estruturada para enriquecer chunks RAG.

Estrutura do índice:
- Tabela "Visão de conjunto": file_number, source_file, palavras, refs, tema_central
- Blocos temáticos: H2 "## Bloco I — ...", "## Bloco II — ...", etc.
- Entradas por ensaio: H3 "### 01 — Título", bullets Palavras-chave/Autoridades/Ver também
"""
from __future__ import annotations

import re
from pathlib import Path


# ---------------------------------------------------------------------------
# Tipos
# ---------------------------------------------------------------------------

ManifestEntry = dict  # ver schema em CLAUDE_CODE_LOCAL_DEV.md §3.6


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def parse_csv_metadata(value: str) -> list[str]:
    """Converte string CSV de metadata de volta para lista de strings."""
    if not value:
        return []
    return [item.strip() for item in value.split(",") if item.strip()]


# ---------------------------------------------------------------------------
# Parser principal
# ---------------------------------------------------------------------------

def parse_manifest(index_path: Path) -> dict[str, ManifestEntry]:
    """
    Lê 00-indice.md e retorna dict keyed por source_file.

    Exemplo de chave: "06-desobediencia.md"

    Levanta RuntimeError se:
    - Tabela de visão geral não for encontrada
    - Número de ensaios != 19
    """
    text = index_path.read_text(encoding="utf-8")
    lines = text.splitlines()

    table_data = _parse_overview_table(lines)
    bloco_map = _parse_blocos(lines)
    entry_details = _parse_entries(lines)

    # Mescla tudo em manifest_data
    manifest: dict[str, ManifestEntry] = {}
    for source_file, row in table_data.items():
        file_num = row["file_number"]
        entry = entry_details.get(file_num, {})
        bloco_tematico, bloco_nome = bloco_map.get(file_num, ("?", "Desconhecido"))

        manifest[source_file] = {
            "file_number": file_num,
            "source_file": source_file,
            "file_title": entry.get("file_title", ""),
            "bloco_tematico": bloco_tematico,
            "bloco_nome": bloco_nome,
            "tema_central": row.get("tema_central", ""),
            "descricao_curta": entry.get("descricao_curta", ""),
            "palavras_chave_csv": entry.get("palavras_chave_csv", ""),
            "autoridades_csv": entry.get("autoridades_csv", ""),
            "ver_tambem_csv": entry.get("ver_tambem_csv", ""),
            "palavras_count": row.get("palavras_count", 0),
            "refs_count": row.get("refs_count", 0),
        }

    return manifest


def validate_manifest(
    manifest: dict[str, ManifestEntry],
    source_dir: Path,
) -> None:
    """
    Validação cruzada: arquivos no disco vs entradas no índice.

    Levanta RuntimeError descritivo em qualquer discrepância.
    Esperado: 19 ensaios (01-19) + 1 índice = 20 arquivos totais.
    """
    disk_files = {
        f.name for f in source_dir.iterdir()
        if f.is_file() and f.suffix.lower() == ".md"
    }
    index_files = set(manifest.keys())

    missing_from_disk = index_files - disk_files
    missing_from_index = disk_files - index_files - {"00-indice.md"}

    errors = []
    if missing_from_disk:
        errors.append(
            f"Arquivos no índice mas ausentes no disco: {sorted(missing_from_disk)}"
        )
    if missing_from_index:
        errors.append(
            f"Arquivos no disco mas ausentes no índice: {sorted(missing_from_index)}"
        )
    if len(manifest) != 19:
        errors.append(
            f"Índice deve ter 19 ensaios, encontrado: {len(manifest)}"
        )

    if errors:
        raise RuntimeError(
            "Validação cruzada do índice falhou. Pare e investigue:\n"
            + "\n".join(f"  - {e}" for e in errors)
        )


# ---------------------------------------------------------------------------
# Parsers internos
# ---------------------------------------------------------------------------

def _parse_overview_table(lines: list[str]) -> dict[str, dict]:
    """
    Extrai a tabela Markdown "Visão de conjunto".

    Colunas: | # | Arquivo | Palavras | Refs | Tema central |
    Retorna dict keyed por source_file.
    """
    in_table = False
    result: dict[str, dict] = {}

    for line in lines:
        stripped = line.strip()

        # Detecta início da tabela (linha de cabeçalho)
        if re.match(r"\|\s*#\s*\|", stripped):
            in_table = True
            continue

        if in_table:
            # Linha separadora (|---|---...)
            if re.match(r"\|[-:\s|]+\|", stripped):
                continue
            # Linha de dado da tabela
            if stripped.startswith("|") and stripped.endswith("|"):
                # Ignora linha de total (Σ)
                if "Σ" in stripped or "**Σ**" in stripped:
                    break
                parts = [p.strip() for p in stripped.strip("|").split("|")]
                if len(parts) < 5:
                    continue
                try:
                    file_num_raw = parts[0].strip("*").strip()
                    # Aceita "01", "1", "**01**" etc.
                    file_num = int(re.sub(r"\D", "", file_num_raw))
                    # Extrai nome do arquivo da célula (pode ter backticks)
                    source_file = re.sub(r"`", "", parts[1]).strip()
                    palavras_raw = re.sub(r"[^\d]", "", parts[2]) or "0"
                    refs_raw = re.sub(r"[^\d]", "", parts[3]) or "0"
                    tema_central = parts[4].strip()

                    result[source_file] = {
                        "file_number": file_num,
                        "palavras_count": int(palavras_raw),
                        "refs_count": int(refs_raw),
                        "tema_central": tema_central,
                    }
                except (ValueError, IndexError):
                    continue
            else:
                # Linha não-tabela depois do início = fim da tabela
                if in_table and result:
                    break

    if not result:
        raise RuntimeError(
            "Tabela 'Visão de conjunto' não encontrada em 00-indice.md. "
            "Verifique se o formato da tabela está correto."
        )

    return result


# Mapa de número romano para numeral
_ROMAN = {"I": "I", "II": "II", "III": "III", "IV": "IV", "V": "V", "VI": "VI"}

def _parse_blocos(lines: list[str]) -> dict[int, tuple[str, str]]:
    """
    Mapeia file_number → (bloco_tematico, bloco_nome).

    Detecta H2 "## Bloco I — ..." e H3 "### 01 — ..." dentro de cada bloco.
    """
    bloco_map: dict[int, tuple[str, str]] = {}
    current_bloco_num = ""
    current_bloco_nome = ""

    bloco_h2_re = re.compile(r"^##\s+Bloco\s+([IVX]+)\s+[—–-]+\s*(.+)$")
    entry_h3_re = re.compile(r"^###\s+(\d+)\s+[—–-]")

    for line in lines:
        stripped = line.strip()
        m_bloco = bloco_h2_re.match(stripped)
        if m_bloco:
            current_bloco_num = m_bloco.group(1).strip()
            current_bloco_nome = m_bloco.group(2).strip()
            continue

        m_entry = entry_h3_re.match(stripped)
        if m_entry and current_bloco_num:
            file_num = int(m_entry.group(1))
            bloco_map[file_num] = (current_bloco_num, current_bloco_nome)

    return bloco_map


def _parse_entries(lines: list[str]) -> dict[int, dict]:
    """
    Extrai por ensaio: file_title, descricao_curta, palavras_chave_csv,
    autoridades_csv, ver_tambem_csv.
    """
    entries: dict[int, dict] = {}
    current_num: int | None = None
    desc_lines: list[str] = []
    in_desc = False

    entry_h3_re = re.compile(r"^###\s+(\d+)\s+[—–-]+\s*(.+)$")
    kw_re = re.compile(r"\*\*Palavras-chave\*\*[:\s]*(.+)$", re.IGNORECASE)
    auth_re = re.compile(r"\*\*Autoridades\*\*[:\s]*(.+)$", re.IGNORECASE)
    see_re = re.compile(r"\*\*Ver\s+também\*\*[:\s]*(.+)$", re.IGNORECASE)

    def _save_current():
        if current_num is not None:
            desc = " ".join(desc_lines).strip()
            entries[current_num]["descricao_curta"] = desc

    for line in lines:
        stripped = line.strip()

        m_entry = entry_h3_re.match(stripped)
        if m_entry:
            _save_current()
            current_num = int(m_entry.group(1))
            title = m_entry.group(2).strip()
            entries[current_num] = {
                "file_title": title,
                "descricao_curta": "",
                "palavras_chave_csv": "",
                "autoridades_csv": "",
                "ver_tambem_csv": "",
            }
            desc_lines = []
            in_desc = True
            continue

        if current_num is None:
            continue

        # Bullet de palavras-chave
        m_kw = kw_re.search(stripped)
        if m_kw:
            in_desc = False
            entries[current_num]["palavras_chave_csv"] = _clean_csv(m_kw.group(1))
            continue

        # Bullet de autoridades
        m_auth = auth_re.search(stripped)
        if m_auth:
            in_desc = False
            entries[current_num]["autoridades_csv"] = _clean_csv(m_auth.group(1))
            continue

        # Bullet "Ver também"
        m_see = see_re.search(stripped)
        if m_see:
            in_desc = False
            ver_raw = m_see.group(1)
            # Extrai apenas os números das referências (ex: "02 (solidão...)" → "2")
            nums = re.findall(r"\b(\d{1,2})\b", ver_raw)
            entries[current_num]["ver_tambem_csv"] = ",".join(nums)
            continue

        # Linha de descrição (parágrafo entre o H3 e os bullets)
        if in_desc and stripped and not stripped.startswith("#") and not stripped.startswith("-"):
            desc_lines.append(stripped)

    _save_current()
    return entries


def _clean_csv(raw: str) -> str:
    """Remove asteriscos de bold, pontuação extra. Retorna CSV limpo."""
    # Remove bold markdown
    cleaned = re.sub(r"\*+", "", raw)
    # Remove parênteses e conteúdo entre parênteses nos itens
    # Ex: "Sanders (Triple P)" → mantém como está (faz parte do nome da autoridade)
    # Apenas remove trailing punctuation
    cleaned = cleaned.strip().rstrip(".")
    return cleaned
