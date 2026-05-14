"""Leitores de documentos por tipo. Corpus atual: 100% Markdown."""
from pathlib import Path


SUPPORTED_EXTENSIONS = {".md", ".txt", ".pdf", ".docx"}


def load_document(path: Path) -> str:
    """Retorna o conteúdo textual do arquivo. Pausa via exceção se PDF escaneado."""
    ext = path.suffix.lower()
    if ext in (".md", ".txt"):
        return path.read_text(encoding="utf-8")
    if ext == ".pdf":
        return _load_pdf(path)
    if ext == ".docx":
        return _load_docx(path)
    raise ValueError(f"Extensão não suportada: {ext} ({path.name})")


def _load_pdf(path: Path) -> str:
    try:
        import pypdf
    except ImportError as e:
        raise ImportError("pypdf não instalado. Execute: pip install pypdf") from e

    reader = pypdf.PdfReader(str(path))
    pages = [page.extract_text() or "" for page in reader.pages]
    text = "\n".join(pages).strip()

    if not text:
        raise RuntimeError(
            f"PDF escaneado detectado (sem texto extraível): {path.name}\n"
            "Pare e processe com OCR antes de ingerir."
        )

    # Heurística: texto muito curto para número de páginas sugere escaneado parcial
    words_per_page = len(text.split()) / max(len(reader.pages), 1)
    if words_per_page < 20:
        raise RuntimeError(
            f"PDF possivelmente escaneado (média {words_per_page:.0f} palavras/página): "
            f"{path.name}\nVerifique e processe com OCR se necessário."
        )

    return text


def _load_docx(path: Path) -> str:
    try:
        import docx
    except ImportError as e:
        raise ImportError("python-docx não instalado. Execute: pip install python-docx") from e

    doc = docx.Document(str(path))
    return "\n".join(p.text for p in doc.paragraphs if p.text.strip())


def list_documents(source_dir: Path) -> list[Path]:
    """Lista todos os arquivos suportados em source_dir (não recursivo)."""
    files = [
        f for f in sorted(source_dir.iterdir())
        if f.is_file() and f.suffix.lower() in SUPPORTED_EXTENSIONS
    ]
    return files
