# Sprint 11 — Perfil de Usuário + Gestão de Conversas

**Data:** 2026-05-18
**Objetivo:** Três features independentes que se complementam: perfil persistente da família (injetado no chat), nomeação automática de conversas pelo LLM, e context menu na sidebar para renomear/exportar/apagar conversas.

---

## Decisões travadas

| Decisão | Escolha |
|---|---|
| Preenchimento do perfil | Automático (extraído de mensagens) + diretiva no system prompt para MaIA perguntar na primeira interação |
| Compartilhar conversa | Copiar transcrição como Markdown (sem URL pública por ora) |
| Apagar conversa | Soft delete (`deleted_at` timestamp, não remove do DB) |
| LLM para título automático | `gpt-4o-mini` (barato, independente de `LLM_MODEL`) |

---

## Feature A — Perfil persistente da família

### A.1 Banco de dados (Supabase)

Criar migration SQL:

```sql
create table user_family_profiles (
  id          uuid primary key default gen_random_uuid(),
  user_id     uuid not null unique references auth.users(id) on delete cascade,
  mother_name text,
  child_name  text,
  child_age   int check (child_age between 0 and 12),
  child_birth_date date,
  raw_context jsonb default '{}',   -- dados extras extraídos automaticamente
  created_at  timestamptz not null default now(),
  updated_at  timestamptz not null default now()
);

-- RLS
alter table user_family_profiles enable row level security;
create policy "Usuário lê próprio perfil"
  on user_family_profiles for select using (auth.uid() = user_id);
create policy "Usuário atualiza próprio perfil"
  on user_family_profiles for all using (auth.uid() = user_id);

-- trigger updated_at (reusar função set_updated_at() já existente)
create trigger set_updated_at
  before update on user_family_profiles
  for each row execute function set_updated_at();
```

### A.2 Backend

**Novos arquivos:**
- `app/services/profile_service.py`
  - `get_or_create_profile(user_id) -> FamilyProfile`
  - `update_profile(user_id, data) -> FamilyProfile`
  - `extract_and_update_profile(user_id, message)` — varre mensagem buscando nome/idade, faz upsert incremental (não sobrescreve campos já preenchidos)

**Endpoints novos em `app/api/v1/profile.py`:**
```
GET  /v1/profile   → retorna perfil atual (cria vazio se não existir)
PUT  /v1/profile   → atualiza campos (todos opcionais)
```

**Editar `app/db/models.py`:**
```python
class FamilyProfile(BaseModel):
    id: UUID
    user_id: UUID
    mother_name: str | None = None
    child_name: str | None = None
    child_age: int | None = None
    child_birth_date: str | None = None
    created_at: datetime
    updated_at: datetime

class FamilyProfileUpdate(BaseModel):
    mother_name: str | None = None
    child_name: str | None = None
    child_age: int | None = None
    child_birth_date: str | None = None
```

**Editar `app/llm/prompts/__init__.py` / `get_system_prompt()`:**
- Aceitar `profile: FamilyProfile | None = None`
- Se perfil tiver dados, injetar bloco no system prompt:
```
<perfil_familia>
Nome da mãe: {mother_name}
Nome da criança: {child_name}
Idade da criança: {child_age} anos
</perfil_familia>
```
- Se perfil estiver vazio, injetar diretiva diferente (ver A.3)

**Editar `app/llm/prompts/system_anthropic.py`:**
- Adicionar seção `<perfil_familia>` no prompt com instrução:
  - Se perfil preenchido: usar nomes de forma natural na conversa
  - Se perfil vazio e é primeira interação: perguntar o nome da mãe e o nome/idade da criança de forma acolhedora, antes de responder a dúvida

**Editar `app/services/chat_service.py`:**
- Após salvar mensagem do usuário, chamar `extract_and_update_profile(user_id, message)` (async-like — não bloquear resposta)
- Carregar perfil via `get_or_create_profile(user_id)`
- Passar perfil para `get_system_prompt(profile=profile)`

**Diretiva a adicionar no `system_anthropic.py`:**
```xml
<perfil_familia>
{PERFIL_PLACEHOLDER}

Se não houver informações da família preenchidas acima, e esta for uma das primeiras mensagens da conversa, apresente-se brevemente e pergunte o nome da mãe e o nome e idade da criança, de forma natural e acolhedora — antes de responder a dúvida dela. Algo como "Antes de te responder, me conta: como você se chama? E seu filho(a), qual é o nome e quantos anos tem?". Depois que tiver essas informações, use os nomes naturalmente na conversa. Nunca pergunte de novo o que já sabe.
</perfil_familia>
```

**Editar `app/main.py`:** registrar router de profile.

---

## Feature B — Nomeação automática de conversas

### B.1 Backend

**Editar `app/core/config.py`:**
```python
TITLE_LLM_MODEL: str = "gpt-4o-mini"  # modelo barato para geração de títulos
```

**Editar `app/services/conversation_service.py`:**
- Adicionar `update_conversation_title(conversation_id, title)` — PATCH no DB
- Adicionar `generate_title(first_user_message: str) -> str`:
  - Chama OpenAI diretamente com `gpt-4o-mini` (hardcoded — não usar factory LLM para não acoplar)
  - Prompt: `"Em até 6 palavras em português, crie um título para uma conversa que começa com: '{mensagem}'. Responda APENAS o título, sem aspas, sem ponto final."`
  - Timeout: 5s, sem retry (falha silenciosa — mantém "Nova conversa")

**Editar `app/services/chat_service.py`:**
- Após salvar resposta do assistente, se `conversation.title == "Nova conversa"` (primeira mensagem):
  - Chamar `generate_title(message)` → `update_conversation_title(conversation.id, title)`
  - Não bloquear — pode ser feito depois do return (ou aceitar latência de ~1s na primeira mensagem)

**Endpoint novo:**
```
PATCH /v1/conversations/{id}   body: { title: str }  → renomear
```
(usado tanto pela nomeação automática quanto pelo renomear manual)

### B.2 Frontend

Sidebar já exibe `c.title` — quando backend preencher automaticamente, aparece. Nenhuma mudança necessária para nomeação automática.

Para renomear manual: ver Feature C.

---

## Feature C — Context menu na sidebar

### C.1 Backend

**Editar `app/db/models.py`:**
- Adicionar `deleted_at: datetime | None = None` em `Conversation`

**Migration SQL:**
```sql
alter table conversations add column deleted_at timestamptz;

-- conversations list já deve filtrar soft deleted
-- (ajustar query em list_conversations para WHERE deleted_at IS NULL)
```

**Endpoints:**
```
PATCH  /v1/conversations/{id}          body: { title: str }   → renomear
DELETE /v1/conversations/{id}          → soft delete (set deleted_at = now())
GET    /v1/conversations/{id}/export   → retorna transcrição Markdown
```

**`export` endpoint** — gerar Markdown:
```markdown
# {titulo}
*Conversa exportada em {data}*

---

**Você:** {mensagem}

**MaIA:** {resposta}

---
...
```

### C.2 Frontend

**Editar `maia-frontend/src/lib/api.ts`:**
```typescript
api.conversations.rename(id, title)   // PATCH /v1/conversations/{id}
api.conversations.delete(id)           // DELETE /v1/conversations/{id}
api.conversations.export(id)           // GET /v1/conversations/{id}/export → string Markdown
```

**Editar `maia-frontend/src/components/ConversationSidebar.tsx`:**

Cada item de conversa recebe:
- `onContextMenu` → abre menu flutuante (`position: fixed` baseado em `e.clientX/Y`)
- Menu com 3 opções:
  1. **Renomear** → substitui o botão por `<input>` inline com o título atual, `onBlur`/`Enter` confirma, `Escape` cancela → chama `api.conversations.rename()`
  2. **Copiar transcrição** → chama `api.conversations.export()` → `navigator.clipboard.writeText(markdown)` → toast "Copiado!"
  3. **Apagar** → modal de confirmação simples ("Tem certeza? Esta conversa será apagada.") → `api.conversations.delete()` → remove da lista local

**Props novas em `ConversationSidebar`:**
```typescript
onRename: (id: string, title: string) => void
onDelete: (id: string) => void
onExport: (id: string) => void
```

**Editar `ChatApp.tsx`:**
- Implementar handlers `handleRename`, `handleDelete`, `handleExport`
- `handleDelete`: se `id === activeConvId`, resetar para tela vazia
- Passar handlers para `ConversationSidebar`

---

## Ordem de execução

```
1. Migration SQL (user_family_profiles + soft delete em conversations)
2. Backend: models.py — FamilyProfile, FamilyProfileUpdate, deleted_at
3. Backend: profile_service.py — get_or_create, update, extract_and_update
4. Backend: prompts — get_system_prompt() aceita profile, diretiva de apresentação
5. Backend: chat_service — carregar perfil, injetar no prompt, extrair após mensagem
6. Backend: conversation_service — generate_title, update_title, soft delete, export
7. Backend: endpoints /v1/profile (GET, PUT) + /v1/conversations PATCH/DELETE/export
8. Backend: config.py — TITLE_LLM_MODEL
9. Backend: main.py — registrar routers
10. Frontend: api.ts — novos métodos
11. Frontend: ConversationSidebar — context menu + inline rename
12. Frontend: ChatApp — handlers rename/delete/export
```

---

## Critérios de conclusão

- [ ] Na primeira mensagem, MaIA pergunta nome da mãe e da criança antes de responder
- [ ] Após a mãe informar os nomes, próximas respostas usam os nomes naturalmente
- [ ] Perfil persiste entre sessões e conversas
- [ ] Título da conversa gerado automaticamente após primeira troca
- [ ] Clique direito na sidebar exibe menu com Renomear / Copiar transcrição / Apagar
- [ ] Renomear funciona inline (sem modal)
- [ ] Copiar transcrição coloca Markdown no clipboard
- [ ] Apagar faz soft delete, remove da sidebar imediatamente
- [ ] Se conversa ativa for apagada, chat reseta para tela vazia

---

## Arquivos que serão criados/editados

### Criados
- `maia-backend/app/services/profile_service.py`
- `maia-backend/app/api/v1/profile.py`
- `maia-backend/migrations/002_sprint11.sql`

### Editados
- `maia-backend/app/core/config.py` — `TITLE_LLM_MODEL`
- `maia-backend/app/db/models.py` — `FamilyProfile`, `FamilyProfileUpdate`, `deleted_at` em `Conversation`
- `maia-backend/app/llm/prompts/__init__.py` — `get_system_prompt(profile=...)`
- `maia-backend/app/llm/prompts/system_anthropic.py` — seção `<perfil_familia>`
- `maia-backend/app/llm/prompts/system_openai.py` — seção equivalente
- `maia-backend/app/services/chat_service.py` — carregar perfil + gerar título
- `maia-backend/app/services/conversation_service.py` — generate_title, soft delete, export, filtro deleted_at
- `maia-backend/app/api/v1/conversations.py` — PATCH, DELETE, export endpoints
- `maia-backend/app/main.py` — registrar profile router
- `maia-frontend/src/lib/api.ts` — rename, delete, export
- `maia-frontend/src/components/ConversationSidebar.tsx` — context menu
- `maia-frontend/src/components/ChatApp.tsx` — handlers
