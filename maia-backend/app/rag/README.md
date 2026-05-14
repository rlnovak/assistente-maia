# MaIA RAG — Módulo de Ingestão

Pipeline de ingestão que lê `knowledge/`, faz chunking semântico por H2, gera embeddings e popula o ChromaDB local.

## Corpus

19 ensaios consolidados (~165k palavras, ~697 referências bibliográficas) organizados em 6 blocos temáticos:

| Bloco | Tema | Arquivos |
|---|---|---|
| I | Bem-estar e saúde mental dos cuidadores | 01, 02 |
| II | Regulação emocional e disciplina | 03, 04, 19, 05 |
| III | Comportamentos desafiadores | 06, 07, 08, 09 |
| IV | Rotinas e infraestrutura familiar | 10, 11, 12, 13, 15 |
| V | Brincar e ambiente preparado | 14, 16, 18 |
| VI | Síntese cultural integradora | 17 |

O arquivo `00-indice.md` é o manifesto mestre — parser extrai metadata de cada ensaio (palavras-chave, autoridades, referências cruzadas) para enriquecer os chunks.

---

## Estrutura do módulo

```
app/rag/
  loaders.py       — leitores por tipo (MD/TXT/PDF/DOCX)
  manifest.py      — parser do 00-indice.md + validação cruzada
  chunking.py      — chunking semântico por H2
  embeddings.py    — wrapper OpenAI text-embedding-3-small
  vector_store.py  — interface ABC + LocalVectorStore + PineconeVectorStore stub
  ingest.py        — CLI principal
```

---

## Rodando a ingestão

```bash
# Ingestão completa (primeira vez ou com --force)
docker compose run --rm api python -m app.rag.ingest --source /data/knowledge

# Re-rodar — pula arquivos inalterados (hash tracking)
docker compose run --rm api python -m app.rag.ingest --source /data/knowledge

# Forçar reingestão de tudo
docker compose run --rm api python -m app.rag.ingest --source /data/knowledge --force

# Dry-run (mostra plano sem gravar embeddings ou custo)
docker compose run --rm api python -m app.rag.ingest --source /data/knowledge --dry-run
```

**Hash tracking:** o estado dos hashes é salvo em `data/ingest-state.json`. Re-rodar sem mudanças processa 0 arquivos e gasta $0. Modificar um arquivo → só esse arquivo é reingerido.

---

## Adicionando novos documentos

1. Adicione o arquivo `.md` em `knowledge/`.
2. Atualize `00-indice.md`: adicione entrada na tabela "Visão de conjunto" e seção H3 com Palavras-chave / Autoridades / Ver também.
3. Rode `python -m app.rag.ingest --source /data/knowledge` — só o novo arquivo será ingerido.

---

## Reingerindo um arquivo específico

O pipeline detecta mudança por hash. Para forçar reingestão de um único arquivo: modifique-o (mesmo que só um espaço) ou use `--force`.

Alternativa programática:

```python
from app.rag.vector_store import get_vector_store
vs = get_vector_store()
vs.delete_by_filter({"source_file": "06-desobediencia.md"})
# depois rode o ingest normalmente
```

---

## Limpando o índice local

```bash
# Remove todos os vetores e o state de hashes
rm -rf .chroma/ data/ingest-state.json

# Reingerir tudo do zero
docker compose run --rm api python -m app.rag.ingest --source /data/knowledge --force
```

---

## Rodando a avaliação qualitativa

```bash
# Todas as 15 queries (top-5)
docker compose run --rm -v $(pwd):/app api python eval_retrieval.py

# Filtrar por bloco
docker compose run --rm -v $(pwd):/app api python eval_retrieval.py --bloco III

# Query específica
docker compose run --rm -v $(pwd):/app api python eval_retrieval.py --query-id q07

# Top-10
docker compose run --rm -v $(pwd):/app api python eval_retrieval.py --top-k 10
```

No Windows, substituir `$(pwd)` pelo caminho absoluto:

```powershell
docker compose run --rm -v "C:\Users\rlnov\Projetos\assistente-maia\maia-backend:/app" api python eval_retrieval.py
```

---

## Como funciona o parser do índice

`manifest.py` lê `00-indice.md` em 3 etapas:

1. **Tabela "Visão de conjunto"** → extrai file_number, palavras_count, refs_count, tema_central.
2. **H2 "## Bloco I/II/..."** → mapeia cada arquivo para bloco_tematico e bloco_nome.
3. **H3 "### 01 — Título"** + bullets → extrai file_title, descricao_curta, palavras_chave_csv, autoridades_csv, ver_tambem_csv.

Validação cruzada obrigatória: 19 ensaios no índice + 19 no disco + 1 índice = 20 arquivos. Pipeline para e lança `RuntimeError` se houver discrepância.

---

## Queries filtradas por bloco e section_type

```python
from app.rag.embeddings import embed_single
from app.rag.vector_store import get_vector_store

vs = get_vector_store()
vector = embed_single("Como lidar com birra?")

# Só bloco III
results = vs.query(vector, top_k=5, filter={"bloco_tematico": "III"})

# Só seções de conteúdo (ignora glossário e referências)
results = vs.query(vector, top_k=5, filter={"section_type": "conteudo"})

# Combinado (Chroma aceita $and)
results = vs.query(vector, top_k=5, filter={
    "$and": [
        {"bloco_tematico": "III"},
        {"section_type": "conteudo"},
    ]
})
```

---

## Promoção a produção (Pinecone)

A abstração `VectorStore` isola completamente o backend. Para promover:

1. Instalar `pinecone-client`.
2. Criar índice Pinecone com dimensão 1536 (text-embedding-3-small) e métrica cosseno.
3. Setar no `.env`:
   ```
   VECTOR_STORE_BACKEND=pinecone
   PINECONE_API_KEY=...
   PINECONE_INDEX=maia-rag
   PINECONE_ENVIRONMENT=...
   ```
4. Implementar `PineconeVectorStore` em `vector_store.py` (hoje é stub).
5. Rodar `python -m app.rag.ingest --source /data/knowledge --force`.

**Nenhum código fora de `vector_store.py` muda.** `chat_service.py`, endpoints, tudo continua igual.

---

## Custos

- Modelo: `text-embedding-3-small` — $0.02 / 1M tokens
- Corpus completo (~165k palavras × 1.3 tokens/palavra ≈ 215k tokens): **~$0.004 USD**
- Re-ingestão parcial (1 arquivo modificado): proporcional ao arquivo
- Re-ingestão com hash tracking inalterado: **$0.00**
