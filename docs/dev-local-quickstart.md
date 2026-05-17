# MaIA — Rodar em Dev Local

**Pré-requisitos:** Docker Desktop, Node.js 20+, Git.

---

## 1. Clonar e posicionar

```powershell
git clone https://github.com/rlnovak/assistente-maia.git
cd assistente-maia
```

---

## 2. Criar o `.env` na raiz do projeto

O arquivo fica em `assistente-maia/.env` (usado pelo backend via `env_file: ../.env`).

Copie o template:

```powershell
Copy-Item maia-backend\.env.example .env
```

Edite `.env` com os valores reais:

```env
# LLM
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sua-chave-aqui
OPENAI_API_KEY=sua-chave-aqui

# Embeddings — NÃO MUDAR sem reingerir o knowledge/
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# Vector store local (dev)
VECTOR_STORE_BACKEND=local
CHROMA_PATH=./.chroma
CHROMA_COLLECTION=maia-rag

# Supabase
SUPABASE_URL=https://thtbpkucczusylaqdmch.supabase.co
SUPABASE_ANON_KEY=sua-anon-key
SUPABASE_SERVICE_ROLE_KEY=sua-service-role-key
SUPABASE_JWT_SECRET=seu-jwt-secret

# Stories
STORIES_LLM_PROVIDER=anthropic
STORIES_LLM_MODEL=claude-sonnet-4-6
ELEVENLABS_API_KEY=   # deixar vazio até ter a key

# Storage
SUPABASE_STORAGE_BUCKET_AUDIOS=story-audios
AUDIO_EXPIRY_DAYS=7

# App
ENV=development
```

---

## 3. Liberar o drive C: no Docker Desktop

Settings → Resources → File Sharing → garantir que `C:\` está na lista.

---

## 4. Subir o backend

```powershell
cd maia-backend
docker compose build
docker compose up
```

API disponível em `http://localhost:8000`.
Swagger UI: `http://localhost:8000/docs`

> **Hot reload ativo:** editar qualquer `.py` em `maia-backend/app/` recarrega automaticamente.

---

## 5. Ingerir o knowledge/ (primeira vez, ou após adicionar arquivos)

```powershell
# Com o container rodando (ou em outro terminal):
docker compose run --rm api python -m app.rag.ingest --source /data/knowledge
```

Para forçar reingestão completa (útil após mudar modelo de embedding):

```powershell
docker compose run --rm api python -m app.rag.ingest --source /data/knowledge --force
```

Saída esperada:
```
✅ Ingestão concluída:
   Processados: 20  |  Pulados: 0
   Chunks:      ~800
   Total no vector store: 800
```

---

## 6. Criar o `.env` do frontend

```powershell
cd ..\maia-frontend
Copy-Item .env.example .env
```

Conteúdo de `maia-frontend/.env`:

```env
PUBLIC_SUPABASE_URL=https://thtbpkucczusylaqdmch.supabase.co
PUBLIC_SUPABASE_ANON_KEY=sua-anon-key
PUBLIC_API_URL=http://localhost:8000
```

---

## 7. Subir o frontend

```powershell
cd maia-frontend
npm install
npm run dev
```

App disponível em `http://localhost:4321`.

---

## 8. Testar o fluxo completo

1. Acesse `http://localhost:4321/login`
2. Faça login com magic link (email cadastrado no Supabase)
3. Envie uma mensagem → MaIA responde usando o RAG local (Chroma)
4. Acesse `http://localhost:4321/stories` → tela de histórias infantis

---

## Comandos do dia a dia

```powershell
# Ver logs do backend em tempo real
docker compose -f maia-backend\docker-compose.yml logs -f

# Parar o backend
docker compose -f maia-backend\docker-compose.yml down

# Reiniciar após mudar .env
docker compose -f maia-backend\docker-compose.yml restart

# Rodar testes
docker compose -f maia-backend\docker-compose.yml run --rm api pytest tests/ -v
```

---

## Trocar de LLM provider

Editar `assistente-maia/.env`:

```env
# Usar Anthropic
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6

# Usar OpenAI
LLM_PROVIDER=openai
LLM_MODEL=gpt-4o
```

Reiniciar: `docker compose restart` na pasta `maia-backend`. Nenhum código muda.

---

## Resetar o vector store local

```powershell
# Para o container
docker compose -f maia-backend\docker-compose.yml down

# Remove o banco Chroma local
Remove-Item -Recurse -Force maia-backend\.chroma

# Sobe e reingestão
docker compose -f maia-backend\docker-compose.yml up -d
docker compose -f maia-backend\docker-compose.yml run --rm api python -m app.rag.ingest --source /data/knowledge --force
```

---

## Estrutura de portas

| Serviço | URL |
|---|---|
| Backend (FastAPI) | `http://localhost:8000` |
| Swagger UI | `http://localhost:8000/docs` |
| Frontend (Astro) | `http://localhost:4321` |
| Chat | `http://localhost:4321/chat` |
| Histórias | `http://localhost:4321/stories` |
