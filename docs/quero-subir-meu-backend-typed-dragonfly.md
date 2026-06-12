# Plano: Deploy MaIA — AWS EC2 + Nginx + Cloudflare Pages

## Status — 2026-05-30

| Fase | Status |
|---|---|
| Fase 1 — Migrar DNS para Cloudflare | ✅ |
| Fase 2 — Criar EC2 + Elastic IP + DNS | ✅ EC2 Debian 13, IP 98.89.15.12 |
| Fase 3 — Instalar Docker + Certbot | ✅ Docker 29.5.2, Compose v5.1.4, Certbot 4.0.0 |
| Fase 4 — Criar arquivos de produção | ✅ Dockerfile.prod, docker-compose.prod.yml, nginx.conf, .env.prod |
| Fase 5 — Deploy backend EC2 | ✅ `curl https://api.aretech.com.br/v1/health` → `{"status":"ok"}` |
| Fase 6 — CORS atualizado | ✅ `maia.aretech.com.br` adicionado |
| Fase 7 — Frontend Cloudflare Pages | ✅ `maia.aretech.com.br` ativo |
| Fase 8 — Auth end-to-end | ✅ Magic link + callback PKCE funcionando |
| Pós-deploy: Migration 002 Supabase | ✅ `user_family_profiles` confirmada |
| Pós-deploy: Cron renovação TLS | ✅ cron instalado, hook configurado |
| Pós-deploy: Swap 1GB EC2 | ✅ |
| Pós-deploy: Webhook Hubla | ⏳ pendente |
| Pós-deploy: ElevenLabs API key | ⏳ pendente |

**Pitfall resolvido:** race condition no callback PKCE — `exchangeCodeForSession` redirecionava para `/chat` antes do SDK persistir sessão no localStorage. Fix: aguardar `onAuthStateChange` confirmar sessão antes de navegar.

---

## Contexto

Backend FastAPI containerizado (porta 8000), frontend Astro estático (output `dist/`).
Objetivo: backend rodando em EC2 t3.micro atrás de Nginx com HTTPS, frontend em Cloudflare Pages,
ambos se comunicando via domínio real com TLS.

Stack definida:
- **AWS EC2** t3.micro (Ubuntu 24.04)
- **Nginx** como reverse proxy + TLS (Let's Encrypt via Certbot)
- **Cloudflare Pages** para o frontend Astro (static)
- **Domínio:** `aretech.com.br` (Hostgator) → migrar nameservers para Cloudflare
- **Subdomínios:** `maia.aretech.com.br` (frontend) e `api.aretech.com.br` (backend)
- **Repo:** `github.com/rlnovak/assistente-maia` (monorepo — backend + frontend)
- **Secrets:** `.env` no servidor
- **Vector store:** Pinecone (sem ChromaDB local — economiza RAM no t3.micro)

---

## Fase 1 — Migrar DNS para Cloudflare e configurar subdomínios

### 1.1 Adicionar domínio na Cloudflare
1. Cloudflare Dashboard → "Add a site" → digitar `aretech.com.br`
2. Escolher plano Free
3. Cloudflare escaneia registros DNS existentes da Hostgator (importa automaticamente)
4. **Anotar os 2 nameservers** fornecidos pela Cloudflare (ex: `ada.ns.cloudflare.com`, `ivan.ns.cloudflare.com`)

### 1.2 Trocar nameservers na Hostgator
1. Painel Hostgator → Domínios → `aretech.com.br` → Gerenciar DNS / Nameservers
2. Substituir pelos nameservers da Cloudflare (dois campos)
3. Aguardar propagação: **geralmente 1–24h**, Cloudflare avisa por e-mail quando ativo

> Enquanto propaga: o site atual em `aretech.com.br` continua funcionando — a Cloudflare importou os registros existentes no passo 1.1.

---

## Fase 2 — Criar e configurar EC2

### 2.1 Criar instância EC2
No console AWS (ou via CLI):
- **AMI:** Ubuntu Server 24.04 LTS (free tier eligible)
- **Tipo:** t3.micro
- **Par de chaves:** criar novo key pair (`.pem`) e salvar localmente
  - Ex: `maia-key.pem` em `~/.ssh/`
  - `chmod 400 ~/.ssh/maia-key.pem`
- **Security Group** (criar novo `maia-sg`):
  - Porta **22** (SSH) — source: Meu IP
  - Porta **80** (HTTP) — source: `0.0.0.0/0` (necessário para Certbot)
  - Porta **443** (HTTPS) — source: `0.0.0.0/0`
  - **NÃO expor porta 8000** ao público — Nginx faz o proxy internamente
- **Storage:** 20GB gp3 (padrão free tier)
- **Elastic IP:** alocar e associar à instância (IP fixo — não muda ao reiniciar)

### 2.2 Configurar DNS na Cloudflare
No Cloudflare DNS (após instância criada e Elastic IP alocado):
```
Tipo A  |  api   |  <Elastic IP da EC2>  |  Proxy: DNS only (nuvem cinza)
```
> **Proxy desligado** (cinza) para `api.aretech.com.br`: Certbot precisa alcançar o servidor diretamente na porta 80 para validar o domínio. Após TLS configurado, pode ligar o proxy laranja — mas é opcional para API.

O subdomínio `maia.aretech.com.br` (frontend) será configurado pelo próprio Cloudflare Pages automaticamente ao adicionar o domínio customizado (Fase 7).

---

## Fase 3 — Preparar servidor EC2

> **AMI em uso:** Debian 12. Usuário SSH: `admin`.

### 3.1 Conectar via SSH (Windows PowerShell)
```powershell
# Corrigir permissões do .pem (obrigatório no Windows — fazer uma vez)
$keyPath = "$env:USERPROFILE\.ssh\maia-aws-rsa-key.pem"
icacls $keyPath /inheritancelevel:r
icacls $keyPath /remove "NT AUTHORITY\Authenticated Users"
icacls $keyPath /remove "BUILTIN\Users"
icacls $keyPath /remove "Everyone"
icacls $keyPath /grant:r "${env:USERNAME}:R"

# Conectar
ssh -i "$env:USERPROFILE\.ssh\maia-aws-rsa-key.pem" admin@<Elastic IP>
```

### 3.2 Atualizar sistema
```bash
sudo apt update && sudo apt upgrade -y
```

### 3.3 Instalar Docker
```bash
sudo apt install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
  | sudo tee /etc/apt/sources.list.d/docker.list

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker admin

# Sair e reconectar para grupo docker ter efeito
exit
```

Reconectar e verificar:
```bash
docker --version && docker compose version
```

### 3.4 Instalar Certbot
```bash
sudo apt install -y certbot
certbot --version
```

---

## Fase 4 — Criar arquivos de produção no repositório

Estes arquivos serão criados no repo local e enviados ao servidor.

### 4.1 `maia-backend/Dockerfile.prod`
Diferenças do Dockerfile dev:
- Sem `--reload`
- Workers múltiplos (`--workers 2`)
- `ENV=production`

```dockerfile
FROM python:3.11-slim
WORKDIR /app
RUN apt-get update && apt-get install -y build-essential && rm -rf /var/lib/apt/lists/*
COPY pyproject.toml .
COPY app/ ./app/
RUN pip install --no-cache-dir ".[dev]"
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

### 4.2 `docker-compose.prod.yml` (raiz do repo)
Dois serviços: `api` + `nginx`.

```yaml
services:
  api:
    build:
      context: ./maia-backend
      dockerfile: Dockerfile.prod
    env_file: .env.prod
    restart: unless-stopped
    # porta 8000 NÃO exposta ao host — nginx acessa via rede interna Docker

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - /etc/letsencrypt:/etc/letsencrypt:ro
    depends_on:
      - api
    restart: unless-stopped

networks:
  default:
    name: maia-net
```

### 4.3 `nginx/nginx.conf`
```nginx
server {
    listen 80;
    server_name api.aretech.com.br;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name api.aretech.com.br;

    ssl_certificate     /etc/letsencrypt/live/api.aretech.com.br/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.aretech.com.br/privkey.pem;

    location / {
        proxy_pass         http://api:8000;
        proxy_set_header   Host $host;
        proxy_set_header   X-Real-IP $remote_addr;
        proxy_set_header   X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header   X-Forwarded-Proto $scheme;
    }
}
```

### 4.4 `.env.prod` (template — NÃO commitar com valores reais)
Criar `.env.prod.example` no repo e o arquivo real `.env.prod` só no servidor:
```env
ENV=production
LLM_PROVIDER=anthropic
LLM_MODEL=claude-3-5-haiku-20241022
ANTHROPIC_API_KEY=sk-...
OPENAI_API_KEY=sk-...
EMBEDDING_PROVIDER=openai
EMBEDDING_MODEL=text-embedding-3-small
VECTOR_STORE_BACKEND=pinecone
PINECONE_API_KEY=...
PINECONE_INDEX=...
PINECONE_ENVIRONMENT=...
SUPABASE_URL=https://xxx.supabase.co
SUPABASE_ANON_KEY=...
SUPABASE_SERVICE_ROLE_KEY=...
SUPABASE_JWT_SECRET=...
RESEND_API_KEY=...
ELEVENLABS_API_KEY=...
SUPABASE_STORAGE_BUCKET_AUDIOS=audios
AUDIO_EXPIRY_DAYS=7
```

---

## Fase 5 — Deploy do backend no EC2

### 5.1 Enviar arquivos ao servidor
No PowerShell local (de dentro do repo):
```powershell
$key = "$env:USERPROFILE\.ssh\maia-aws-rsa-key.pem"
$ip = "<Elastic IP>"

# Criar estrutura no servidor
ssh -i $key ec2-user@$ip "mkdir -p ~/maia/nginx"

# Enviar arquivos de configuração
scp -i $key docker-compose.prod.yml ec2-user@${ip}:~/maia/
scp -i $key nginx/nginx.conf ec2-user@${ip}:~/maia/nginx/
scp -i $key -r maia-backend ec2-user@${ip}:~/maia/
```

### 5.2 Criar `.env.prod` no servidor
```bash
# (dentro do servidor, após ssh)
nano ~/maia/.env.prod   # colar os valores reais
```

### 5.3 Obter certificado TLS (antes de subir Nginx)
O Certbot standalone precisa da porta 80 livre:
```bash
sudo certbot certonly --standalone -d api.aretech.com.br \
  --email seu@email.com --agree-tos --non-interactive
```
Certificados salvos em `/etc/letsencrypt/live/api.aretech.com.br/`.

**Renovação automática:**
```bash
sudo crontab -e
# Adicionar:
0 3 * * * certbot renew --quiet --pre-hook "docker compose -f /home/ec2-user/maia/docker-compose.prod.yml stop nginx" --post-hook "docker compose -f /home/ec2-user/maia/docker-compose.prod.yml start nginx"
```

### 5.4 Subir containers
```bash
cd ~/maia
docker compose -f docker-compose.prod.yml up -d --build
docker compose -f docker-compose.prod.yml ps    # verificar status
docker compose -f docker-compose.prod.yml logs api --tail=50  # checar erros
```

### 5.5 Testar backend
```bash
curl https://api.aretech.com.br/v1/health
# Esperado: {"status":"ok","version":"0.1.0"}
```

---

## Fase 6 — Atualizar CORS no backend

Em `maia-backend/app/main.py`, adicionar a URL de produção do frontend à lista de CORS:

**Arquivo:** `maia-backend/app/main.py`
```python
allow_origins=[
    "http://localhost:4321",
    "http://localhost:4322",
    "http://localhost:3000",
    "https://maia.aretech.com.br",   # ← adicionar
]
```

---

## Fase 7 — Deploy do frontend no Cloudflare Pages (via GitHub — igual à página de captura)

O monorepo `github.com/rlnovak/assistente-maia` contém o frontend em `maia-frontend/`.
Cloudflare Pages suporta monorepo: basta configurar o diretório raiz como `maia-frontend/`.

### 7.1 Criar projeto no Cloudflare Pages
1. Cloudflare Dashboard → Pages → "Create a project" → "Connect to Git"
2. Autorizar acesso ao GitHub → selecionar repo `rlnovak/assistente-maia`
3. Configurar build:
   - **Project name:** `maia-frontend`
   - **Root directory:** `maia-frontend`
   - **Build command:** `npm run build`
   - **Build output directory:** `dist`
4. Em **Environment variables** (Production), adicionar:
   ```
   PUBLIC_SUPABASE_URL      = https://xxx.supabase.co
   PUBLIC_SUPABASE_ANON_KEY = eyJ...
   PUBLIC_API_URL           = https://api.aretech.com.br
   ```
5. Clicar "Save and Deploy"

A partir daí: todo push para `master` dispara deploy automático — mesmo comportamento da sua página de captura.

### 7.2 Domínio customizado `maia.aretech.com.br`
1. Cloudflare Pages → projeto `maia-frontend` → Settings → Custom domains
2. Adicionar `maia.aretech.com.br`
3. Cloudflare cria o registro DNS automaticamente (CNAME para `maia-frontend.pages.dev`)
4. TLS provisionado automaticamente — sem Certbot necessário para o frontend

---

## Fase 8 — Autenticação da API (resposta à sua pergunta)

> "Esse acesso tem que ter algum tipo de autenticação (chave secreta)?"

**Resposta: a autenticação já existe e é JWT via Supabase.**

Todos os endpoints protegidos (chat, conversations, profile, stories) exigem:
```
Authorization: Bearer <supabase-access-token>
```

O token é emitido pelo Supabase após login do usuário no frontend.
O backend valida a assinatura JWT com a chave pública do Supabase (ES256 em produção).

**O que NÃO é necessário:** chave secreta de API adicional entre frontend e backend, pois o JWT do Supabase já garante que só usuários autenticados acessam os dados.

**O que SIM é importante:**
- Porta 8000 **não exposta** ao público (só Nginx na 443)
- Security Group da EC2 bloqueia tudo exceto 22, 80, 443
- CORS restrito ao domínio do frontend em produção

---

## Resumo da arquitetura final

```
Usuário
  │
  ▼
Cloudflare Pages (maia.aretech.com.br)          ← deploy automático via push no GitHub
  │  HTML/CSS/JS estático (build de maia-frontend/)
  │  PUBLIC_API_URL=https://api.aretech.com.br
  │
  ▼  (HTTPS + Bearer JWT Supabase)
Cloudflare DNS
  ├── maia.aretech.com.br → CNAME maia-frontend.pages.dev   (gerenciado pelo Pages)
  └── api.aretech.com.br  → A <Elastic IP EC2>               (proxy desligado)
                                │
                                ▼
                    EC2 t3.micro (Ubuntu 24.04)
                    ├── Security Group: 22/80/443 open, 8000 closed
                    ├── Nginx :443 → TLS (Certbot) → proxy_pass http://api:8000
                    └── Docker network maia-net
                          └── api :8000 (FastAPI + Uvicorn 2 workers)
                                └── Pinecone (cloud) + Supabase (cloud)

Domínio: aretech.com.br (Hostgator) → nameservers → Cloudflare
```

---

## Arquivos a criar/modificar

| Arquivo | Ação |
|---------|------|
| `maia-backend/Dockerfile.prod` | Criar |
| `docker-compose.prod.yml` | Criar (raiz do repo) |
| `nginx/nginx.conf` | Criar |
| `.env.prod.example` | Criar (template sem valores reais) |
| `maia-backend/app/main.py` | Modificar CORS origins |
| `.github/workflows/deploy-frontend.yml` | Criar (opcional CI/CD) |

---

## Verificação end-to-end

1. `curl https://api.aretech.com.br/v1/health` → `{"status":"ok"}`
2. Abrir `https://maia.aretech.com.br` → tela de login carrega
3. Fazer login com Supabase Magic Link
4. Enviar mensagem no chat → resposta da MaIA chega
5. `docker compose -f docker-compose.prod.yml logs api` → sem erros 500

---

## Apêndice — Migração para domínio definitivo

Quando registrar domínio definitivo para MaIA, todas as mudanças são de configuração — sem tocar em lógica de negócio.

### 1. Cloudflare DNS
- Adicionar novo domínio ao Cloudflare (ou criar subdomínios se for subdomínio do mesmo domínio)
- Recriar registros:
  ```
  A      api.<novoDominio>   <Elastic IP EC2>   proxy: off
  CNAME  maia.<novoDominio>  maia-frontend.pages.dev
  ```

### 2. Backend — EC2
Atualizar `nginx/nginx.conf` (2 ocorrências):
```nginx
server_name api.<novoDominio>;
ssl_certificate     /etc/letsencrypt/live/api.<novoDominio>/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/api.<novoDominio>/privkey.pem;
```
Obter novo certificado TLS:
```bash
sudo certbot certonly --standalone -d api.<novoDominio> \
  --email seu@email.com --agree-tos --non-interactive
```
Reiniciar Nginx (único momento de downtime):
```bash
cd ~/maia && docker compose -f docker-compose.prod.yml restart nginx
```

### 3. Frontend — Cloudflare Pages
- Painel Pages → projeto `maia-frontend` → Settings → Environment variables
  - Atualizar `PUBLIC_API_URL` para `https://api.<novoDominio>`
- Settings → Custom domains → adicionar `maia.<novoDominio>` → remover `maia.aretech.com.br`
- Disparar novo deploy (ou aguardar próximo push)

### 4. Código — CORS
`maia-backend/app/main.py` — atualizar `allow_origins`:
```python
allow_origins=[
    "http://localhost:4321",
    "https://maia.<novoDominio>",   # substituir aretech
]
```
Rebuild + redeploy no EC2:
```bash
cd ~/maia && docker compose -f docker-compose.prod.yml up -d --build
```

### 5. Supabase
Dashboard → Authentication → URL Configuration:
- **Site URL:** `https://maia.<novoDominio>`
- **Redirect URLs:** adicionar `https://maia.<novoDominio>/auth/callback`
- Remover URLs antigas (opcional, mas recomendado)
