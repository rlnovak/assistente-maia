# Deploy MaIA na AWS (t3.micro) + Pinecone

**Para quem:** dev nível básico, sem custo (free tier AWS + Pinecone).
**Pré-requisitos:** conta AWS ativa, conta Pinecone ativa, repositório clonado localmente.

---

## Por que Pinecone em vez de Chroma na EC2?

t3.micro tem 1GB de RAM. FastAPI usa ~400MB. Chroma carregado usa ~400MB.
Juntos, estouram a memória e o servidor trava. Pinecone fica nos servidores
deles — sua EC2 só envia perguntas via internet. Problema resolvido.

---

## Parte 1 — Pinecone (fazer no seu computador local)

### 1.1 Criar índice no Pinecone

1. Acesse [pinecone.io](https://pinecone.io) → faça login
2. Clique em **"Create Index"**
3. Preencha:
   - **Index name:** `maia-rag`
   - **Dimensions:** `1536` (obrigatório — tamanho do modelo de embedding)
   - **Metric:** `Cosine`
   - **Capacity mode:** `Serverless` (free tier)
   - **Cloud / Region:** `AWS us-east-1`
4. Clique em **"Create Index"**
5. Aguarde o índice ficar `Ready` (30-60 segundos)

### 1.2 Copiar credenciais do Pinecone

No dashboard do Pinecone:
- **API Key:** menu lateral → **API Keys** → copie a default key
- **Index name:** `maia-rag` (o que você criou acima)
- **Environment:** não é mais necessário no SDK novo (deixar vazio no .env)

### 1.3 Atualizar o .env local

No arquivo `.env` na raiz do projeto (`assistente-maia/.env`), mude:

```env
# Antes:
VECTOR_STORE_BACKEND=local

# Depois:
VECTOR_STORE_BACKEND=pinecone
PINECONE_API_KEY=sua-api-key-aqui
PINECONE_INDEX=maia-rag
PINECONE_ENVIRONMENT=   # deixar vazio — não usado no SDK v3
```

### 1.4 Instalar dependência do Pinecone localmente

```powershell
cd C:\Users\rlnov\Projetos\assistente-maia\maia-backend
pip install pinecone-client
```

### 1.5 Reingerir o knowledge/ apontando para o Pinecone

Este passo lê todos os arquivos da pasta `knowledge/`, gera os embeddings
(via OpenAI) e envia para o Pinecone. Roda uma vez só.

```powershell
# Na pasta maia-backend, com o .env já atualizado:
cd C:\Users\rlnov\Projetos\assistente-maia\maia-backend
docker compose run --rm api python -m app.rag.ingest --source /data/knowledge --force
```

Ao terminar, você verá algo como:
```
✅ Ingestão concluída:
   Processados: 20  |  Pulados: 0
   Chunks:      ~800
   Total no vector store: 800
```

Confirme no dashboard do Pinecone que o índice tem vetores.

### 1.6 Testar localmente antes de subir para a EC2

```powershell
docker compose up
```

Acesse `http://localhost:4321/chat` e envie uma mensagem. Se responder
normalmente, o Pinecone está funcionando.

---

## Parte 2 — EC2 (fazer no terminal SSH da sua instância)

### 2.1 Conectar na EC2

```bash
ssh -i sua-chave.pem ec2-user@IP-DA-SUA-EC2
```

### 2.2 Instalar Docker na EC2 (se ainda não tiver)

```bash
sudo yum update -y
sudo yum install -y docker git
sudo service docker start
sudo usermod -aG docker ec2-user

# Instalar Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Desconecte e reconecte para o grupo docker fazer efeito
exit
# Reconecte via SSH
```

### 2.3 Clonar o repositório na EC2

```bash
git clone https://github.com/rlnovak/assistente-maia.git
cd assistente-maia
```

### 2.4 Criar o arquivo .env na EC2

```bash
nano .env
```

Cole o conteúdo abaixo (substitua os valores reais):

```env
# LLM
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-6
ANTHROPIC_API_KEY=sua-chave-anthropic
OPENAI_API_KEY=sua-chave-openai

# Embeddings
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small

# Vector store — Pinecone (não Chroma)
VECTOR_STORE_BACKEND=pinecone
PINECONE_API_KEY=sua-chave-pinecone
PINECONE_INDEX=maia-rag
PINECONE_ENVIRONMENT=

# Supabase
SUPABASE_URL=https://thtbpkucczusylaqdmch.supabase.co
SUPABASE_ANON_KEY=sua-anon-key
SUPABASE_SERVICE_ROLE_KEY=sua-service-role-key
SUPABASE_JWT_SECRET=seu-jwt-secret

# Stories
STORIES_LLM_PROVIDER=anthropic
STORIES_LLM_MODEL=claude-sonnet-4-6
ELEVENLABS_API_KEY=

# Storage
SUPABASE_STORAGE_BUCKET_AUDIOS=story-audios
AUDIO_EXPIRY_DAYS=7

# App
ENV=production
```

Salvar: `Ctrl+O` → Enter → `Ctrl+X`

### 2.5 Criar docker-compose para produção na EC2

```bash
nano maia-backend/docker-compose.prod.yml
```

Cole:

```yaml
services:
  api:
    build: .
    ports:
      - "8000:8000"
    volumes:
      - ./data:/app/data
      - ./docs:/app/docs
      - ./knowledge:/data/knowledge:ro
    env_file:
      - ../.env
    environment:
      - VECTOR_STORE_BACKEND=pinecone
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
    restart: unless-stopped
```

Salvar: `Ctrl+O` → Enter → `Ctrl+X`

> **Nota:** sem volume `.chroma` — não precisa mais do Chroma na EC2.

### 2.6 Build e subir o backend

```bash
cd assistente-maia/maia-backend
docker-compose -f docker-compose.prod.yml up -d --build
```

Aguarde o build (3-5 minutos na primeira vez). Para ver os logs:

```bash
docker-compose -f docker-compose.prod.yml logs -f
```

Deve aparecer: `Application startup complete`.

### 2.7 Verificar que está funcionando

```bash
curl http://localhost:8000/v1/health
```

Deve retornar: `{"status":"ok","version":"0.1.0"}`

### 2.8 Abrir a porta 8000 no Security Group da EC2

No console AWS:
1. EC2 → sua instância → aba **Security**
2. Clique no Security Group
3. **Edit inbound rules** → Add rule:
   - Type: `Custom TCP`
   - Port: `8000`
   - Source: `0.0.0.0/0` (ou só seu IP por segurança)
4. Save rules

---

## Parte 3 — Frontend (duas opções)

### Opção A — Rodar na mesma EC2 (mais simples)

```bash
# Instalar Node.js na EC2
curl -fsSL https://rpm.nodesource.com/setup_20.x | sudo bash -
sudo yum install -y nodejs

cd ~/assistente-maia/maia-frontend

# Criar .env do frontend
echo "PUBLIC_API_URL=http://IP-DA-SUA-EC2:8000" > .env
echo "PUBLIC_SUPABASE_URL=https://thtbpkucczusylaqdmch.supabase.co" >> .env
echo "PUBLIC_SUPABASE_ANON_KEY=sua-anon-key" >> .env

npm install
npm run build
npm run preview -- --host 0.0.0.0 --port 4321
```

Abrir porta 4321 no Security Group (igual ao passo 2.8, mas porta 4321).
Acessar: `http://IP-DA-SUA-EC2:4321`

### Opção B — Frontend estático no S3 + CloudFront (gratuito no free tier)

```powershell
# No seu computador local, na pasta maia-frontend:
# Editar .env para apontar para o IP da EC2
PUBLIC_API_URL=http://IP-DA-SUA-EC2:8000

npm run build
# Gera a pasta dist/

# Upload da pasta dist/ para um bucket S3 com static hosting habilitado
```

Esta opção é mais robusta mas requer configurar S3 static hosting —
documentação: AWS S3 → Static website hosting.

---

## Parte 4 — Manutenção

### Atualizar o código após mudanças

```bash
# Na EC2:
cd ~/assistente-maia
git pull origin master
cd maia-backend
docker-compose -f docker-compose.prod.yml up -d --build
```

### Ver logs em tempo real

```bash
docker-compose -f docker-compose.prod.yml logs -f api
```

### Reiniciar o backend

```bash
docker-compose -f docker-compose.prod.yml restart api
```

### Adicionar novos arquivos ao knowledge/ e reingerir

```bash
# Copiar o novo arquivo para knowledge/ na EC2
# Depois rodar ingestão incremental (só processa arquivos novos/alterados):
docker-compose -f docker-compose.prod.yml run --rm api \
  python -m app.rag.ingest --source /data/knowledge
```

---

## Resumo de custos (free tier)

| Recurso | Custo |
|---|---|
| EC2 t3.micro (12 meses) | Grátis |
| Pinecone serverless (até 100k vetores) | Grátis |
| Supabase (até 500MB DB) | Grátis |
| OpenAI embeddings (ingestão única ~$0.001) | Quase grátis |
| **Total mensal** | **$0** |

Após 12 meses de free tier AWS: EC2 t3.micro custa ~$8/mês.

---

## Solução de problemas comuns

**Backend não sobe — erro de memória:**
```bash
# t3.micro tem 1GB — verifique uso
free -h
# Se swap estiver zerado, adicionar swap ajuda:
sudo dd if=/dev/zero of=/swapfile bs=128M count=8
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile
```

**Erro "Pinecone index not found":**
- Confirme que o nome do índice no .env é exatamente `maia-rag`
- Confirme que o índice está `Ready` no dashboard do Pinecone

**Backend responde mas RAG retorna vazio:**
- O índice Pinecone está vazio — rode a ingestão (Parte 1, passo 1.5)
- Confirme no dashboard do Pinecone que `Vector Count > 0`

**Frontend não consegue chamar o backend (CORS):**
- Abra a porta 8000 no Security Group (passo 2.8)
- Verifique se `PUBLIC_API_URL` no .env do frontend aponta para o IP correto
