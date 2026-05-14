# MaIA — Assistente Parental com IA

Assistente conversacional para mães de crianças de **1 a 5 anos**, baseado em um corpus de 19 ensaios clínicos (~165 mil palavras, ~697 referências bibliográficas) organizados em seis blocos temáticos:

| Bloco | Tema |
|---|---|
| I | Bem-estar e saúde mental dos cuidadores |
| II | Regulação emocional e disciplina |
| III | Comportamentos desafiadores |
| IV | Rotinas e infraestrutura familiar |
| V | Brincar e ambiente preparado |
| VI | Síntese cultural integradora |

Tom: **amiga especialista** — acolhedor, baseado em evidências, linguagem cotidiana. Idioma: pt-BR.

---

## Arquitetura

```
assistente-maia/
├── knowledge/          # Corpus: 19 ensaios .md + 00-indice.md
├── maia-backend/       # API FastAPI (Python 3.11, Docker)
└── maia-frontend/      # Webapp Astro + React + Tailwind
```

### Stack

| Camada | Tecnologia |
|---|---|
| Backend | FastAPI + Uvicorn |
| Vector DB (dev) | ChromaDB embedded |
| Vector DB (prod) | Pinecone (sprint futura) |
| Embeddings | OpenAI `text-embedding-3-small` |
| LLM | Anthropic Claude ou OpenAI GPT (configurável via env) |
| Auth | Supabase (Postgres + JWT) |
| Frontend | Astro 5 + React 18 + Tailwind 4 |

---

## Pré-requisitos

- [Docker Desktop](https://www.docker.com/products/docker-desktop/) com acesso ao drive `C:` habilitado  
  *(Settings → Resources → File Sharing → marcar `C:`)*
- Node.js 20+
- Projeto Supabase de dev criado com schema aplicado (ver [Schema Supabase](#schema-supabase))
- Chaves de API: OpenAI (obrigatório) + Anthropic ou OpenAI para o LLM de chat

---

## Configuração inicial

### 1. Variáveis de ambiente

Crie o arquivo `.env` na **raiz do repositório** (`assistente-maia/.env`):

```env
# === LLM ===
LLM_PROVIDER=anthropic          # anthropic | openai
LLM_MODEL=claude-sonnet-4-5     # ver tabela de modelos abaixo

# === API Keys ===
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...

# === Embeddings (não alterar sem reingerir knowledge/) ===
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# === Vector Store ===
VECTOR_STORE_BACKEND=local      # local | pinecone

# === Supabase ===
SUPABASE_URL=https://<projeto>.supabase.co
SUPABASE_ANON_KEY=<anon-key>
SUPABASE_SERVICE_ROLE_KEY=<service-role-key>
SUPABASE_JWT_SECRET=<jwt-secret>

# === App ===
ENV=development
```

> O backend lê `../.env` (relativo a `maia-backend/`). O frontend usa variáveis separadas com prefixo `PUBLIC_` em `maia-frontend/.env`.

### 2. Variáveis de ambiente do frontend

Crie `maia-frontend/.env`:

```env
PUBLIC_SUPABASE_URL=https://<projeto>.supabase.co
PUBLIC_SUPABASE_ANON_KEY=<anon-key>
PUBLIC_API_URL=http://localhost:8000
```

### 3. Schema Supabase

No SQL Editor do seu projeto Supabase, execute:

```
maia-backend/migrations/001_initial_schema.sql
```

---

## Containers Docker

O backend roda em um único container gerenciado pelo `docker-compose.yml` em `maia-backend/`.

### Serviço `api`

| Propriedade | Valor |
|---|---|
| Imagem base | `python:3.11-slim` |
| Porta exposta | `8000` (host) → `8000` (container) |
| Comando | `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload` |
| Restart | `unless-stopped` |

### Volumes montados

| Host | Container | Modo | Finalidade |
|---|---|---|---|
| `./app/` | `/app/app` | read-write | Hot reload — editar `.py` recarrega sem rebuild |
| `./.chroma/` | `/app/.chroma` | read-write | ChromaDB persistente entre restarts |
| `./data/` | `/app/data` | read-write | Summaries de ingestão e estado |
| `./docs/` | `/app/docs` | read-write | Inventário RAG gerado |
| `knowledge/` (raiz) | `/data/knowledge` | **read-only** | Corpus de conteúdo |

> **Importante:** o caminho do `knowledge/` no `docker-compose.yml` está hardcoded para `C:\Users\rlnov\Projetos\assistente-maia\knowledge`. Se clonar em outro caminho, edite a linha correspondente em `maia-backend/docker-compose.yml`.

### Dockerfile resumido

```
python:3.11-slim
  → instala build-essential
  → copia pyproject.toml + app/
  → pip install ".[dev]"
  → EXPOSE 8000
```

O `node_modules` do frontend e o `.chroma/` do backend **não entram no git** (`.gitignore`).

---

## Rodar localmente (dev)

### Backend

```bash
cd maia-backend

# Primeira vez: build da imagem
docker compose build

# Subir a API
docker compose up
```

API disponível em `http://localhost:8000`  
Swagger UI: `http://localhost:8000/docs`

**Derrubar:**
```bash
docker compose down
```

**Ver logs em tempo real:**
```bash
docker compose logs -f
```

### Ingestão RAG (primeira vez ou ao atualizar `knowledge/`)

```bash
docker compose run --rm api python -m app.rag.ingest --source /data/knowledge
```

O pipeline é idempotente — re-rodar em corpus inalterado não gera novos embeddings.

### Frontend

```bash
cd maia-frontend
npm install       # apenas na primeira vez
npm run dev
```

Webapp disponível em `http://localhost:4321`

### Fluxo completo

1. `docker compose up` em `maia-backend/` → aguardar `Application startup complete`
2. `npm run dev` em `maia-frontend/`
3. Abrir `http://localhost:4321/login`
4. Digitar email → clicar no magic link recebido por email
5. Redireciona para `/chat` → enviar mensagem → resposta do MaIA

---

## Trocar de provider LLM

Editar `.env` na raiz e reiniciar o container — **sem mexer em código**:

```env
# Anthropic Claude
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5

# OpenAI GPT
LLM_PROVIDER=openai
LLM_MODEL=gpt-5.4
```

```bash
docker compose restart
```

### Modelos suportados

| Provider | Modelo | Perfil |
|---|---|---|
| `anthropic` | `claude-sonnet-4-5` | Qualidade |
| `anthropic` | `claude-haiku-4-5-20251001` | Mais rápido/barato |
| `openai` | `gpt-5.4` | Qualidade |
| `openai` | `gpt-5.4-mini` | Mais rápido/barato |

Cada provider usa um system prompt otimizado para seu estilo de instrução (`maia-backend/app/llm/prompts/`).

---

## Rodar testes

```bash
docker compose run --rm api pytest tests/ -v
```

---

## O que NÃO está em escopo nesta versão dev

- Deploy em VPS / Cloudflare Pages
- Nginx reverse proxy e TLS
- CI/CD (GitHub Actions)
- Webhooks WhatsApp / Hub.la
- Streaming SSE
- Dark mode / PWA
- Pinecone (Vector DB de produção) — stub implementado, ativo na sprint de promoção

---

## Estrutura de código

```
maia-backend/app/
├── api/v1/          # endpoints: /chat, /conversations, /health, webhooks
├── core/            # config (pydantic-settings), logging, security
├── db/              # cliente Supabase + modelos Pydantic
├── llm/             # LLMClient ABC + AnthropicClient + OpenAIClient + prompts
├── rag/             # ingestão, chunking H2, embeddings, VectorStore ABC
├── services/        # chat_service, conversation_service, email_service
└── middleware/      # request_id, rate_limit

maia-frontend/src/
├── pages/           # index (redirect), login, auth/callback, chat
├── components/      # ChatApp, ConversationSidebar, LoginForm, MessageBubble
├── lib/             # supabase.ts, api.ts (fetch com JWT auto-inject)
├── layouts/         # BaseLayout.astro
└── styles/          # global.css com tokens de design do brandbook
```
