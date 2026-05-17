# Sprint 10 — Gerador de Histórias Infantis (v1)

**Data:** 2026-05-17
**Objetivo:** Implementar o gerador de histórias do zero até uma versão funcional completa — DB, backend, frontend, áudio.

---

## Escopo do Sprint

### Fora do escopo (backlog futuro)
- Clonagem de voz da mãe (ElevenLabs premium)
- Few-shot com histórias bem avaliadas
- Exportar PDF
- Modo "continuar história"
- Notificação push de expiração de áudio

---

## Tarefas

### 1 — Banco de dados (Supabase)

**1.1** Criar migration SQL com tabelas `stories` e `story_audios`:
- `stories`: campos de input, campos de output (titulo, historia, moral, tags), rating (1–5), rating_notes, model_used, context_extracted (jsonb), created_at
- `story_audios`: FK para stories, voice_id, storage_path, expires_at (now + 7d), duration_seconds, created_at

**1.2** RLS policies:
- Usuário lê/escreve apenas suas próprias histórias e áudios
- Service role sem restrição (para o backend)

**1.3** Criar bucket `story-audios` no Supabase Storage com política de acesso privado (signed URLs).

**1.4** Criar função SQL ou pg_cron job para deletar arquivos de Storage onde `story_audios.expires_at < now()`.

---

### 2 — Backend (FastAPI)

**2.1** `app/llm/prompts/system_stories.py`
- Constante `SYSTEM_PROMPT_STORIES` — system prompt especializado em literatura infantil
- Função `build_story_prompt(child_name, characters, theme, lesson, size, reference, context)` → string
- Tabela `SIZE_MAP` de palavras por tamanho + tabela `AGE_SIZE_FALLBACK` por faixa etária

**2.2** `app/llm/story_client.py`
- Classe `StoryClient` com método `generate(prompt_inputs) -> StoryOutput`
- Chama LLM (inicialmente Anthropic, configurável via settings)
- Parseia JSON de resposta → valida campos obrigatórios
- Lança exceção tipada se JSON inválido

**2.3** `app/services/story_service.py`
- `extract_context_from_conversations(user_id) -> dict` — varre histórico do chat e extrai nome da criança, idade e outras informações relevantes
- `create_story(user_id, inputs, context) -> Story` — chama StoryClient, salva em DB
- `get_stories(user_id) -> list[Story]`
- `get_story(user_id, story_id) -> Story`
- `rate_story(user_id, story_id, rating, notes) -> Story`

**2.4** `app/services/audio_service.py`
- `generate_audio(user_id, story_id, voice_id) -> StoryAudio` — chama ElevenLabs, faz upload para Storage, salva registro em `story_audios` com `expires_at = now() + 7d`
- `get_audio_url(user_id, story_id) -> str` — retorna signed URL do Storage (válida por tempo curto)
- `list_voices() -> list[Voice]` — retorna vozes pré-definidas disponíveis

**2.5** `app/db/models.py` — adicionar modelos Pydantic:
- `StoryCreate`, `Story`, `StoryAudio`, `StoryRating`, `StoryGenerateRequest`, `StoryGenerateResponse`, `AudioGenerateRequest`, `AudioGenerateResponse`

**2.6** `app/core/config.py` — adicionar settings:
- `ELEVENLABS_API_KEY: str`
- `STORIES_LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"` (independente do chat)
- `STORIES_LLM_MODEL: str = "claude-sonnet-4-6"`
- `SUPABASE_STORAGE_BUCKET_AUDIOS: str = "story-audios"`
- `AUDIO_EXPIRY_DAYS: int = 7`

**2.7** `app/api/v1/stories.py` — router com endpoints:
```
POST   /v1/stories/generate          → gera história
GET    /v1/stories                   → lista histórias do usuário
GET    /v1/stories/{story_id}        → detalhe de uma história
POST   /v1/stories/{story_id}/rating → salva rating e nota
POST   /v1/stories/{story_id}/audio  → gera áudio
GET    /v1/stories/{story_id}/audio  → retorna signed URL do áudio
GET    /v1/stories/voices            → lista vozes disponíveis
```

**2.8** Registrar router em `app/main.py`.

---

### 3 — Frontend (Astro + React)

**3.1** `maia-frontend/src/lib/api.ts` — adicionar funções:
- `api.stories.generate(inputs)`
- `api.stories.list()`
- `api.stories.get(id)`
- `api.stories.rate(id, rating, notes)`
- `api.stories.generateAudio(id, voiceId)`
- `api.stories.getAudioUrl(id)`
- `api.stories.voices()`

**3.2** `maia-frontend/src/pages/stories.astro` — página da aba histórias.

**3.3** `maia-frontend/src/components/StoryForm.tsx`
- Formulário com campos obrigatórios + opcionais
- Seletor de tamanho (Curta / Média / Longa / Não sei)
- "Não sei" → exibe campo de idade para usar fallback da tabela
- Loading state durante geração

**3.4** `maia-frontend/src/components/StoryDisplay.tsx`
- Exibe título, texto da história, moral
- Rating: 5 estrelas clicáveis + campo de nota opcional
- Botão "Ouvir" → aciona geração de áudio
- Player de áudio inline (HTML `<audio>` nativo + estilizado)
- Botão de download + aviso de expiração em 7 dias

**3.5** `maia-frontend/src/components/StoryLibrary.tsx`
- Lista de histórias geradas (card com título, data, rating)
- Filtros por nome da criança e tema/tag
- Indicador visual quando áudio está expirado ou ainda disponível
- Clique no card → expande ou navega para a história completa com opção de ouvir/baixar áudio

**3.6** Navegação: adicionar link "Histórias" na topbar (mobile) e sidebar (desktop) do `ChatApp.tsx`.

**3.7** `maia-frontend/src/components/VoiceSelector.tsx`
- Dropdown com vozes disponíveis (nome + sample de texto)
- Persistir escolha em localStorage

---

### 4 — Configuração e infra

**4.1** Adicionar `ELEVENLABS_API_KEY` e demais settings novas ao `.env.example` (backend).

**4.2** Testar expiração de áudio: gerar áudio, confirmar signed URL funciona, confirmar que após `expires_at` o arquivo é inacessível.

**4.3** Rate limiting: endpoint `POST /v1/stories/generate` — limite mais restrito (geração de história é cara). Sugestão: 5 req/hora por usuário.

---

## Ordem de execução sugerida

```
1. DB (migrations + Storage bucket)         ← desbloqueia tudo
2. Backend models + config                  ← base para services
3. story_client.py + system_stories.py      ← núcleo da geração
4. story_service.py + audio_service.py      ← lógica de negócio
5. API router + registrar em main.py        ← endpoints prontos
6. Frontend: api.ts                         ← integração
7. Frontend: StoryForm + StoryDisplay       ← fluxo principal
8. Frontend: StoryLibrary + VoiceSelector   ← features complementares
9. Navegação entre chat e histórias         ← UX final
10. Testes end-to-end + rate limiting       ← finalização
```

---

## Dependências externas

- **ElevenLabs API** — criar conta, obter API key, selecionar 3–5 vozes femininas pré-definidas para v1
- **Supabase pg_cron** — habilitar extensão no projeto para job de limpeza de áudios expirados (ou implementar como endpoint chamado por cron externo)

---

## Critérios de conclusão

- [ ] Mãe consegue preencher formulário e receber história gerada
- [ ] Rating de 1–5 estrelas salvo no DB
- [ ] Áudio gerado e reproduzível inline no mobile
- [ ] Download de áudio funcional
- [ ] Áudio inacessível após 7 dias
- [ ] Biblioteca lista histórias anteriores com status do áudio e filtros por criança/tema
- [ ] Navegação entre chat principal e aba histórias
