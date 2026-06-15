#!/usr/bin/env bash
# setup-ec2.sh — Prepara EC2 Debian para rodar o backend MaIA
# Rodar como usuário 'admin' (não root) numa instância Debian 12 limpa.
# Uso: bash setup-ec2.sh [seu@email.com]
#
# O que faz:
#   1. Atualiza sistema
#   2. Instala Docker + Compose
#   3. Instala Certbot
#   4. Cria swap de 1GB
#   5. Obtém certificado TLS para api.aretech.com.br
#   6. Clona o repo e sobe os containers
#   7. Instala cron de renovação TLS

set -euo pipefail

EMAIL="${1:-}"
DOMAIN="api.aretech.com.br"
REPO="https://github.com/rlnovak/assistente-maia.git"
APP_DIR="$HOME/maia"

# ── Helpers ───────────────────────────────────────────────────────────────────
log()  { echo -e "\n\033[1;32m▶ $*\033[0m"; }
err()  { echo -e "\033[1;31m✗ $*\033[0m" >&2; exit 1; }
need() { command -v "$1" &>/dev/null || err "comando '$1' não encontrado após instalação"; }

[[ -z "$EMAIL" ]] && err "Uso: bash setup-ec2.sh seu@email.com"

# ── 1. Atualizar sistema ───────────────────────────────────────────────────────
log "1/7 Atualizando sistema"
sudo apt-get update -q
sudo apt-get upgrade -y -q

# ── 2. Instalar Docker ────────────────────────────────────────────────────────
log "2/7 Instalando Docker + Compose"
if ! command -v docker &>/dev/null; then
    sudo apt-get install -y -q ca-certificates curl gnupg

    sudo install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/debian/gpg \
        | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    sudo chmod a+r /etc/apt/keyrings/docker.gpg

    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/debian $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    sudo apt-get update -q
    sudo apt-get install -y -q docker-ce docker-ce-cli containerd.io docker-compose-plugin

    sudo systemctl enable --now docker
    sudo usermod -aG docker "$USER"
    echo "⚠  Docker instalado. Grupo docker adicionado — será necessário novo login para efeito."
else
    echo "   Docker já instalado: $(docker --version)"
fi
need docker

# ── 3. Instalar Certbot ───────────────────────────────────────────────────────
log "3/7 Instalando Certbot"
if ! command -v certbot &>/dev/null; then
    sudo apt-get install -y -q certbot
fi
need certbot
echo "   Certbot: $(certbot --version 2>&1)"

# ── 4. Criar swap 1GB ─────────────────────────────────────────────────────────
log "4/7 Configurando swap 1GB"
if ! swapon --show | grep -q '/swapfile'; then
    sudo fallocate -l 1G /swapfile
    sudo chmod 600 /swapfile
    sudo mkswap /swapfile
    sudo swapon /swapfile
    echo '/swapfile none swap sw 0 0' | sudo tee -a /etc/fstab > /dev/null
    echo "   Swap criado: $(free -h | grep Swap)"
else
    echo "   Swap já existe: $(free -h | grep Swap)"
fi

# ── 5. Clonar repo ────────────────────────────────────────────────────────────
log "5/7 Clonando repositório"
if [[ -d "$APP_DIR/.git" ]]; then
    echo "   Repo já existe — fazendo pull"
    git -C "$APP_DIR" pull --ff-only
else
    git clone "$REPO" "$APP_DIR"
fi

# Verificar que arquivos de produção existem
[[ -f "$APP_DIR/docker-compose.prod.yml" ]]  || err "docker-compose.prod.yml não encontrado no repo"
[[ -f "$APP_DIR/nginx/nginx.conf" ]]          || err "nginx/nginx.conf não encontrado no repo"
[[ -f "$APP_DIR/maia-backend/Dockerfile.prod" ]] || err "Dockerfile.prod não encontrado no repo"

# ── 6. .env.prod ──────────────────────────────────────────────────────────────
log "6/7 Verificando .env.prod"
if [[ ! -f "$APP_DIR/.env.prod" ]]; then
    cat <<'EOF'

  ⚠  ATENÇÃO: .env.prod não encontrado em ~/maia/.env.prod
  Crie o arquivo antes de continuar:

    nano ~/maia/.env.prod

  Template em: ~/maia/.env.prod.example (se existir no repo)

  Variáveis obrigatórias:
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

  Após criar o arquivo, execute novamente:
    bash setup-ec2.sh $EMAIL

EOF
    exit 0
fi

# ── 7. Certificado TLS ────────────────────────────────────────────────────────
log "7a/7 Obtendo certificado TLS para $DOMAIN"
if [[ ! -d "/etc/letsencrypt/live/$DOMAIN" ]]; then
    # Porta 80 precisa estar livre — parar nginx se estiver rodando
    sudo docker compose -f "$APP_DIR/docker-compose.prod.yml" stop nginx 2>/dev/null || true

    sudo certbot certonly --standalone \
        -d "$DOMAIN" \
        --email "$EMAIL" \
        --agree-tos \
        --non-interactive
    echo "   Certificado obtido em /etc/letsencrypt/live/$DOMAIN/"
else
    echo "   Certificado já existe — pulando"
fi

# ── 8. Subir containers ───────────────────────────────────────────────────────
log "7b/7 Subindo containers"

# Recarregar grupo docker sem precisar logout (newgrp não funciona em script)
if ! groups | grep -q docker; then
    echo "   Executando docker compose via sudo (grupo docker ainda não ativo nesta sessão)"
    DOCKER_CMD="sudo docker compose"
else
    DOCKER_CMD="docker compose"
fi

$DOCKER_CMD -f "$APP_DIR/docker-compose.prod.yml" up -d --build
$DOCKER_CMD -f "$APP_DIR/docker-compose.prod.yml" ps

# ── 9. Cron renovação TLS ─────────────────────────────────────────────────────
log "7c/7 Instalando cron de renovação TLS"
CRON_JOB="0 3 * * * certbot renew --quiet --pre-hook \"docker compose -f $APP_DIR/docker-compose.prod.yml stop nginx\" --post-hook \"docker compose -f $APP_DIR/docker-compose.prod.yml start nginx\""

if ! sudo crontab -l 2>/dev/null | grep -qF "certbot renew"; then
    (sudo crontab -l 2>/dev/null; echo "$CRON_JOB") | sudo crontab -
    echo "   Cron instalado"
else
    echo "   Cron já existe — pulando"
fi

# ── Verificação final ─────────────────────────────────────────────────────────
log "Verificação final"
sleep 3
HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" "https://$DOMAIN/v1/health" || echo "000")
if [[ "$HTTP_STATUS" == "200" ]]; then
    echo "✅ Backend OK — https://$DOMAIN/v1/health → 200"
else
    echo "⚠  Health check retornou HTTP $HTTP_STATUS — verificar logs:"
    echo "   $DOCKER_CMD -f $APP_DIR/docker-compose.prod.yml logs api --tail=50"
fi

echo ""
echo "======================================================"
echo " Setup concluído!"
echo " Logs:    docker compose -f $APP_DIR/docker-compose.prod.yml logs api --tail=50"
echo " Status:  docker compose -f $APP_DIR/docker-compose.prod.yml ps"
echo " Restart: docker compose -f $APP_DIR/docker-compose.prod.yml restart"
echo "======================================================"
