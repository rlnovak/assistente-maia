# Relatório de Progresso — Projeto MaIA
*referência: 2026-06-11*

---

## 1. O QUE FOI FEITO

### Produto / Funil (Arsenal de Funis)

| Entrega | Status |
|---|---|
| Pesquisa de mercado | ✅ |
| Briefing + Big Idea + posicionamento | ✅ |
| Brandbook v1.0 (paleta, tipografia, tokens) | ✅ |
| Isca digital — Kit Mágico pra Mães (3 prompts ChatGPT) | ✅ |
| Landing page de captura ao vivo | ✅ `captura-projeto-maes.pages.dev` |
| Página de vendas (rascunho) | ✅ parcial — 7 markers `EDITÁVEL` pendentes |
| Integração Supabase captura de leads | ✅ tabela `leads` com UTMs |

### Assistente — Sprints técnicos

| Sprint | Feature | Status |
|---|---|---|
| Sprint 07 | RAG Ingestion — ChromaDB, chunking, embeddings OpenAI | ✅ |
| Sprint 08 | Backend FastAPI — `/v1/chat`, auth Supabase JWT, Docker dev | ✅ |
| Sprint 09 | Frontend Astro + React — login magic link, ChatApp, sidebar | ✅ |
| Benchmark | Chunking params — decisão: manter `max_words=1000` | ✅ |
| Sprint 10 | Gerador de Histórias Infantis — 7 endpoints, 6 componentes | ✅ |
| Pinecone | PineconeVectorStore implementada, ingestão executada | ✅ |
| Sprint 11 | Perfil família + título automático de conversas + context menu | ✅ |

### Deploy — concluído em 2026-05-30

| Etapa | Status |
|---|---|
| DNS `aretech.com.br` migrado para Cloudflare | ✅ |
| EC2 Debian 13, t3.micro, Elastic IP `98.89.15.12` | ✅ |
| Docker 29.5.2 + Compose v5.1.4 + Certbot 4.0.0 | ✅ |
| Backend ao vivo: `https://api.aretech.com.br` | ✅ |
| Frontend ao vivo: `https://maia.aretech.com.br` | ✅ (Cloudflare Pages, auto-deploy via GitHub) |
| Migration 002 Supabase (`user_family_profiles`) | ✅ |
| Cron renovação TLS (expira 2026-08-28) | ✅ |
| Swap 1GB na EC2 | ✅ |
| Auth magic link end-to-end funcionando | ✅ |

### Bugs corrigidos no deploy

| Bug | Fix |
|---|---|
| Race condition PKCE: redirect antes do SDK persistir sessão | Aguardar `onAuthStateChange` no callback antes de navegar |
| `PKCE code verifier not found in storage` em nova aba | Trocar `flowType: 'pkce'` por `'implicit'` — verifier não sobrevive cross-tab |

---

## 2. ONDE ESTAMOS AGORA

**Produto técnico: MVP em produção, autenticação funcionando.**

`https://maia.aretech.com.br` está ao vivo. Login por magic link funciona. Chat com RAG + perfil de família operacional. Histórias geradas (sem áudio — ElevenLabs pendente).

**Funil: ao vivo, captando leads, não converte ainda.**

Página de captura no ar. Não há página de vendas finalizada, nem integração de pagamento, nem domínio definitivo.

---

## 3. O QUE FALTA FAZER

### Crítico — bloqueia monetização

| Ação | Detalhe |
|---|---|
| **Webhook Hubla** | `/v1/webhooks/hubla.py` é stub. Compra não ativa plano do usuário |
| **ElevenLabs API key** | Áudio de histórias lança `NotImplementedError`. Obter key + uncommentar `audio_service.py` + rebuild EC2 |
| **Página de vendas** | 7 markers `EDITÁVEL` — história da Eliza, 3 depoimentos beta, 4 imagens reais |
| **Nome definitivo + domínio** | MaIA é provisório. Define URL, email de suporte, LGPD |
| **Política de Privacidade + Termos** | Obrigatório LGPD antes de vender |

### Importante — qualidade e estabilidade

| Ação | Detalhe |
|---|---|
| **Testes automatizados** | `test_auth.py` (token expirado/inválido), `test_chat.py`, `test_profile.py`, `test_stories.py` (parse JSON LLM) |
| **Rate limiting `/v1/stories/generate`** | Sem limite específico hoje — sugestão: 5 req/hora |
| **Email de suporte** | `oi@[dominio]` via Cloudflare Email Routing — aguarda domínio |

### Backlog futuro

| Ação | Detalhe |
|---|---|
| WhatsApp webhook | `/v1/webhooks/whatsapp` é stub |
| Clonagem de voz da mãe | ElevenLabs — após integração básica de áudio |
| Few-shot com histórias bem avaliadas | RAG de histórias |
| Isca no Notion | Publicar Kit Mágico como página duplicável |

---

## 4. AÇÕES CRÍTICAS — ORDEM SUGERIDA

```
1. ElevenLabs key                    ← feature de áudio viva, relativamente rápido
2. Webhook Hubla                     ← monetização
3. Página de vendas (7 markers)      ← conversão
4. Nome definitivo + domínio         ← antes de escalar tráfego
5. LGPD + email de suporte           ← antes de vender
6. Testes prioritários               ← antes de usuários reais em volume
```

---

## 5. REFERÊNCIAS

| Recurso | Localização |
|---|---|
| Plano de deploy detalhado | `C:\Users\rlnov\.claude\plans\quero-subir-meu-backend-typed-dragonfly.md` |
| Obsidian — deploy | `7 - Claude Code/2026-05-20 — Deploy MaIA AWS EC2 Nginx Cloudflare Pages.md` |
| Obsidian — Sprint 11 | `7 - Claude Code/2026-05-19 — Sprint 11 Perfil Conversas MaIA.md` |
| Obsidian — funil completo | `7 - Claude Code/2026-04-02 — Funil MaIA Pipeline Completo.md` |
| Backend ao vivo | `https://api.aretech.com.br/v1/health` |
| Frontend ao vivo | `https://maia.aretech.com.br` |
| EC2 SSH | `ssh -i ~/.ssh/maia-aws-rsa-key.pem admin@98.89.15.12` |
