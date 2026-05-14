# MaIA Backend

FastAPI + ChromaDB + Supabase — ambiente local de desenvolvimento.

## Pré-requisitos

- Docker Desktop com acesso ao drive `C:` (Settings → Resources → File Sharing)
- Supabase: projeto de dev criado, schema aplicado (`migrations/001_initial_schema.sql`)
- `.env` na raiz do repo pai (`../assistente-maia/.env`) com todas as variáveis

## Subir local

```bash
cd maia-backend
docker compose build
docker compose up
```

API disponível em `http://localhost:8000`.  
Swagger UI: `http://localhost:8000/docs`

## Derrubar

```bash
docker compose down
```

## Ver logs

```bash
docker compose logs -f
```

## Hot reload

O código em `./app/` é montado como volume dentro do container. Editar qualquer `.py` recarrega automaticamente sem rebuild.

## Rodar testes

```bash
docker compose run --rm api pytest tests/ -v
```

Ou localmente (com venv):

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Ingestão RAG

```bash
docker compose run --rm api python -m app.rag.ingest --source /data/knowledge
```

## Trocar de provider LLM

Editar `../.env` (ou `maia-backend/.env` se existir):

```env
# Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5

# OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.4
```

Reiniciar o container:

```bash
docker compose restart
```

**Nenhum código muda.** A factory `get_llm_client()` e `get_system_prompt()` resolvem automaticamente.

### Modelos suportados

| Provider | Modelo | Custo estimado (input/output por 1M tokens) |
|---|---|---|
| `anthropic` | `claude-sonnet-4-5` | $3 / $15 |
| `anthropic` | `claude-haiku-4-5-20251001` | $0.80 / $4 |
| `openai` | `gpt-5.4` | verificar docs.openai.com |
| `openai` | `gpt-5.4-mini` | verificar docs.openai.com |

Custo por conversa (10 turnos, ~500 tokens/resposta): estimativa de $0.01–$0.05 dependendo do modelo.

## Trocar Vector Store

```env
# Local (dev)
VECTOR_STORE_BACKEND=local

# Pinecone (não implementado — sprint de promoção)
VECTOR_STORE_BACKEND=pinecone
PINECONE_API_KEY=...
PINECONE_INDEX=...
PINECONE_ENVIRONMENT=...
```

## Schema Supabase

Aplicar uma única vez no SQL Editor do Supabase (projeto de dev):

```
migrations/001_initial_schema.sql
```

## Promoção a produção

O que vai mudar na sprint de promoção (não agora):

| Item | Dev | Produção |
|---|---|---|
| Acesso | Direto ao Uvicorn `:8000` | Nginx reverse proxy + Certbot TLS |
| Docker | `docker-compose.yml` | `docker-compose.prod.yml` |
| Workers | 1 + `--reload` | múltiplos workers sem reload |
| Vector store | ChromaDB local | Pinecone (`VECTOR_STORE_BACKEND=pinecone`) |
| Rate limiting | 1000/min generoso | 60/min global, 20/min chat |
| LLM provider | Qualquer (dev) | Decisão definitiva + monitoramento de custo |
| Logs | Console colorido | JSON estruturado + agregador externo |
| Webapp | `localhost:4321` | Cloudflare Pages |

A troca de provider/vector store é configuração, não código — a abstração já está plugada.
