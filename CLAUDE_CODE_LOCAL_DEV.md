# MaIA — Instruções para Claude Code: Versão Local Dev

**Modelo recomendado:** Opus 4.x (Sonnet 4.x para o webapp).
**Repositórios envolvidos:** `maia-backend` e `maia-webapp`.
**Escopo deste documento:** rodar o MaIA inteiro (RAG + backend + webapp) em
ambiente de **desenvolvimento local**, sem deploy, sem nuvem, sem TLS.

Este arquivo consolida e adapta os Sprints 07 (Ingestão RAG), 08 (Backend
FastAPI) e 09 (Webapp Chat) do `PROJECT.md` para o contexto local-dev.

---

## 0. Contexto e princípios

### 0.1 Visão de produto

O MaIA é um assistente virtual com IA para mães de crianças de 1 a 5
anos (com aplicação parcial a recém-nascidos e idade escolar inicial,
conforme o corpus em `knowledge/`). O conteúdo está organizado em **seis
blocos temáticos** que vão do mais íntimo (a mãe) ao mais comunitário
(a rede), conforme definido no `00-indice.md`:

- **Bloco I** — Bem-estar e saúde mental dos cuidadores
- **Bloco II** — Regulação emocional e disciplina
- **Bloco III** — Comportamentos desafiadores
- **Bloco IV** — Rotinas e infraestrutura familiar
- **Bloco V** — Brincar e ambiente preparado
- **Bloco VI** — Síntese cultural integradora

Toda a copy e respostas são em **português do Brasil (pt-BR)**, no tom
"amiga especialista" — acolhedor, validador, evidência traduzida em
linguagem cotidiana, dicas acionáveis, sem jargão.

### 0.2 Decisões travadas (não questionar, não substituir)

- **LLM:** **multi-provider** em dev — Anthropic OU OpenAI, configurável
  via env. Modelos suportados nesta sprint:
  - **Anthropic:** `claude-sonnet-4-5` (qualidade) ou
    `claude-haiku-4-5-20251001` (mais barato).
  - **OpenAI:** `gpt-5.4` (qualidade) ou `gpt-5.4-mini` (mais barato).
  - **Futuro (não nesta sprint):** LLMs chineses (DeepSeek, Qwen, etc.) —
    a abstração deve permitir adição trivial.
- **Banco relacional + Auth:** Supabase (Postgres gerenciado).
- **Vector DB local:** **ChromaDB embedded** (mudança estrutural vs
  `PROJECT.md` para a versão local-dev).
- **Vector DB de produção:** Pinecone (será usado depois — não nesta sprint).
- **Backend:** FastAPI + Uvicorn, containerizado com Docker Compose.
- **Webapp:** Astro + React (islands) + Tailwind.
- **Idioma:** pt-BR em toda copy, system prompts e UI.

### 0.2.1 Princípio arquitetural complementar: abstração `LLMClient`

Análogo ao `VectorStore`. O backend define uma interface `LLMClient`
abstrata, com implementações `AnthropicClient` e `OpenAIClient`. A escolha
é controlada por `LLM_PROVIDER={anthropic|openai}` e `LLM_MODEL=<nome>`.
Nenhum código fora de `app/llm/` deve importar `anthropic` ou `openai`
diretamente — sempre via factory `get_llm_client()`.

**System prompts são por provider, não compartilhados.** Claude e GPT
respondem de forma diferente a instruções de personalidade, recusas e
formatação. O conteúdo (6 blocos temáticos, guardrails SAMU/CVV, tom
pt-BR) é o mesmo; o **estilo de instrução** muda — XML tags e estrutura
hierárquica para Claude, seções nomeadas e formatação direta para GPT.

Adicionar um terceiro provider no futuro (ex: DeepSeek) deve exigir
apenas: nova classe `DeepSeekClient` implementando `LLMClient`, novo
arquivo `prompts/system_deepseek.py`, registro na factory.

### 0.3 Princípio arquitetural central: abstração `VectorStore`

A única diferença prática entre dev local e produção é **onde** os vetores
são armazenados. Para isolar essa diferença, o backend define uma interface
`VectorStore` abstrata, com duas implementações: `LocalVectorStore` (Chroma)
e `PineconeVectorStore` (stub agora, completa na sprint de promoção). A
escolha é controlada por uma variável de ambiente
`VECTOR_STORE_BACKEND={local|pinecone}`. Nenhum outro código deve saber qual
backend está em uso.

### 0.4 O que NÃO está em escopo nesta sprint local-dev

Itens explícitos que ficam para sprints futuras (não execute, não configure):

- Deploy no VPS Contabo.
- Nginx como reverse proxy e Certbot/Let's Encrypt.
- `docker-compose.prod.yml`.
- HTTPS / SSL.
- Cloudflare Pages para o webapp.
- GitHub Actions / CI/CD.
- Webhooks de WhatsApp / Hub.la (estes têm sprints próprias).
- Streaming SSE (a menos que o usuário confirme que quer agora — pergunte).
- Sentry e observability stack externa.
- Rate limiting de produção (manter limites generosos em dev).
- PWA / dark mode (perguntar se entram nesta sprint).

---

## 1. Princípio de execução

**Plano primeiro, aprovação, execução.** Antes de escrever qualquer código,
apresente um plano detalhado por sprint (07, 08, 09) e peça aprovação. Não
combine sprints na mesma rodada.

**Pergunte antes de prosseguir se** qualquer item das listas "Perguntar
antes de prosseguir se…" abaixo não estiver claro.

**Nunca invente informações.** Use o conhecimento interno, faça buscas
online, ou use os documentos referenciados (`PROJECT.md`,
`branding-book-maia.html`, `pesquisa-mercado-assistente-ia-maternidade.md`,
arquivos da pasta `knowledge/`).

---

## 2. Pré-requisitos e perguntas iniciais (responder antes do plano da Sprint 07)

Antes de começar a Sprint 07, confirme com o usuário:

1. **Provider de embeddings — DECISÃO JÁ TOMADA.** Modelo:
   `text-embedding-3-small` da OpenAI. Trave em `.env`:
   - `EMBEDDING_PROVIDER=openai`
   - `EMBEDDING_MODEL=text-embedding-3-small`
   - `OPENAI_API_KEY=<chave>`

   **CRÍTICO:** o modelo de embedding DEVE ser o mesmo em ingestão e em
   query. Trocar o modelo invalida todos os vetores existentes — exigirá
   reingestão completa. Esta decisão também é independente da escolha de
   LLM de chat (item 2): você pode usar embedding OpenAI com LLM
   Anthropic, sem problema.

2. **Provider e modelo de LLM para `/v1/chat`.** Multi-provider em dev.
   Confirmar com o usuário qual será o **default inicial**:

   | Provider | Modelo | Quando usar |
   |---|---|---|
   | `anthropic` | `claude-sonnet-4-5` | Anthropic, qualidade |
   | `anthropic` | `claude-haiku-4-5-20251001` | Anthropic, mais barato |
   | `openai` | `gpt-5.4` | OpenAI, qualidade |
   | `openai` | `gpt-5.4-mini` | OpenAI, mais barato |

   Trave em `.env`:
   - `LLM_PROVIDER={anthropic|openai}`
   - `LLM_MODEL=<nome exato do modelo>`

   Trocar de provider deve ser apenas uma mudança no `.env` + restart do
   container — sem mexer em código.

3. **Localização e conteúdo da pasta de referências.**

   **3.1 Caminho absoluto da pasta `knowledge/`** — DEFINIDO.

   - **Host (Windows, disco local — fora do OneDrive):**
     `C:\Users\rlnov\Projetos\assistente-maia\knowledge`
   - **Container (caminho canônico):** `/data/knowledge`

   Configuração do `docker-compose.yml` (bind mount **read-only**):

   ```yaml
   services:
     api:
       volumes:
         - "C:\\Users\\rlnov\\Projetos\\assistente-maia\\knowledge:/data/knowledge:ro"
   ```

   Toda referência ao path no código Python deve usar o caminho do
   container (`/data/knowledge`), **nunca** o path Windows. Use
   `pathlib.Path` em todo o código (não strings com separadores).

   **Cuidados com Windows + Docker:**
   - Verificar que o Docker Desktop tem permissão para acessar o drive
     `C:` (Settings → Resources → File Sharing).
   - O caminho está **fora do OneDrive** intencionalmente — pasta
     sincronizada pelo OneDrive causa problemas de file locking,
     sincronização durante leitura, e Files On-Demand (placeholders com
     tamanho 0). **Não mover o projeto para dentro do OneDrive.**
   - O `.chroma/` (vector DB local persistente) também ficará fora do
     OneDrive por consequência — banco de dados em pasta sincronizada
     corrompe.

   **3.2 Estrutura esperada da pasta `knowledge/`:**
   - Um arquivo `00-indice.md` na raiz — manifesto estruturado com 19
     ensaios organizados em 6 blocos temáticos (I-VI), com
     palavras-chave, autoridades e referências cruzadas para cada
     ensaio (ver §3.2.1 para detalhes do parser).
   - **19 ensaios consolidados** em Markdown (`01-*.md` a `19-*.md`),
     cada um com Visão geral + seções H2 + Glossário + Referências.
   - Total: 20 arquivos. Tamanho aproximado: ~165 mil palavras.

   **3.3 Tarefas na inspeção inicial:**
   - Listar todos os arquivos com tipos e tamanhos.
   - Sinalizar PDFs escaneados (precisam OCR — pare e pergunte).
   - Confirmar direitos autorais antes de commitar conteúdo no git.
   - **Validar consistência do índice:** todos os arquivos listados em
     `00-indice.md` existem na pasta? Há arquivos na pasta que não estão
     listados no índice? Reportar discrepâncias antes de prosseguir.

4. **Streaming SSE no `/v1/chat`.** Implementar nesta sprint ou deixar
   para depois? Default: deixar para depois. **Atenção:** se entrar
   nesta sprint, ambas as implementações (`AnthropicClient` e
   `OpenAIClient`) precisam suportar streaming — não só uma delas.

5. **Dark mode no webapp.** Implementar agora ou depois? Default: depois.

6. **PWA no webapp.** Implementar agora ou depois? Default: depois.

7. **Variáveis de ambiente já disponíveis.** Pedir ao usuário um `.env`
   inicial com:
   - `LLM_PROVIDER`, `LLM_MODEL` (decisão do item 2)
   - `ANTHROPIC_API_KEY` (sempre incluir, mesmo se default for OpenAI —
     permite trocar de provider sem reconfigurar)
   - `OPENAI_API_KEY` (sempre incluir — usado tanto para LLM quanto para
     embeddings)
   - `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
     `SUPABASE_JWT_SECRET`
   - `EMBEDDING_PROVIDER=openai`, `EMBEDDING_MODEL=text-embedding-3-small`
   - `RESEND_API_KEY` (pode ficar vazio se email transacional não for
     testado nesta sprint — perguntar)

8. **Projeto Supabase de dev.** Confirmar se o usuário criou um projeto
   separado para dev (recomendado) ou se vai usar o projeto único. Em
   ambos os casos, NÃO escrever em produção a partir do dev.

---

## 3. Sprint 07 adaptado — Ingestão RAG com abstração VectorStore

**Repositório:** `maia-backend`.
**Objetivo:** Pipeline de ingestão que lê `knowledge/`, faz chunking,
gera embeddings, e popula o ChromaDB local. Pipeline idempotente e
reexecutável.

### 3.1 DIFF vs sprint original

| Aspecto | Sprint original | Versão local-dev |
|---|---|---|
| Vector DB | Pinecone | ChromaDB embedded (path local: `./.chroma/`) |
| `pinecone_client.py` | Cliente Pinecone direto | Substituído por `vector_store.py` (interface ABC) + duas implementações |
| Variável de controle | — | `VECTOR_STORE_BACKEND=local` |
| Free tier check | Pinecone | Sem limite prático local; só cuidado com tamanho da pasta |

### 3.2 Estrutura de código em `maia-backend/app/rag/`

```
app/rag/
  __init__.py
  loaders.py            # leitores por tipo (PDF, DOCX, MD, TXT)
  manifest.py           # parse do 00-indice.md e enriquecimento de metadata
  chunking.py           # chunking semântico
  embeddings.py         # wrapper sobre o provider escolhido
  vector_store.py       # interface ABC + LocalVectorStore + PineconeVectorStore (stub)
  ingest.py             # CLI: python -m app.rag.ingest --source /data/knowledge
  README.md
```

**Nota sobre `--source`:** o caminho default é `/data/knowledge`
(caminho do container, conforme bind mount definido na §2 item 3.1).
Permitir override via flag `--source` para permitir testes com pastas
alternativas.

### 3.2.1 Tratamento especial do `00-indice.md` (NOVO — não estava no sprint original)

O arquivo `00-indice.md` é um **manifesto estruturado e altamente
informativo** do corpus. Ele não é um documento qualquer — é uma
especificação rica de metadata que o autor (Rafa) construiu pensando
explicitamente em RAG (o próprio índice contém uma seção "Notas para uso
do índice e da base" com diretrizes técnicas).

O pipeline de ingestão usa esse arquivo em duas frentes: como fonte de
metadata para enriquecer todos os outros documentos, e como documento
ingerido em si.

#### Estrutura real do índice (confirmada)

O corpus tem **19 ensaios consolidados** (~165 mil palavras, ~697
referências bibliográficas) organizados em **6 blocos temáticos**:

- **Bloco I** — Bem-estar e saúde mental dos cuidadores (arquivos 01-02)
- **Bloco II** — Regulação emocional e disciplina (03, 04, 19, 05)
- **Bloco III** — Comportamentos desafiadores (06-09)
- **Bloco IV** — Rotinas e infraestrutura familiar (10-13, 15)
- **Bloco V** — Brincar e ambiente preparado (14, 16, 18)
- **Bloco VI** — Síntese cultural integradora (17)

Cada arquivo tem o padrão: bloco de metadados HTML + Visão geral +
seções H2 fluídas + Glossário + Referências numeradas.

Cada entrada do índice contém, em formato consistente:
- Heading H3 com número e título completo do ensaio
- Parágrafo de descrição
- Lista bullet `**Palavras-chave**:` (separadas por vírgula)
- Lista bullet `**Autoridades**:` (separadas por vírgula)
- Lista bullet `**Ver também**:` (referências cruzadas a outros arquivos)

#### Fluxo de processamento

**Etapa 1 — Parse do manifesto (`app/rag/manifest.py`):**

1. Lê `00-indice.md` inteiro.
2. Extrai a tabela "Visão de conjunto" (formato Markdown table) para
   pegar `file_number`, `source_file`, `palavras` (contagem),
   `refs` (contagem), `tema_central`.
3. Identifica os 6 blocos temáticos pelos H2 (`## Bloco I`, `## Bloco II`,
   etc.) e mapeia cada arquivo para seu bloco.
4. Para cada arquivo, parseia a entrada H3 e extrai descrição,
   palavras-chave, autoridades, "ver também" (lista de números de outros
   arquivos referenciados).
5. Constrói um dicionário `manifest_data` no formato:

   ```python
   {
       "06-desobediencia.md": {
           "file_number": 6,
           "file_title": "Quando seu filho diz \"não\" o tempo todo...",
           "bloco_tematico": "III",
           "bloco_nome": "Comportamentos desafiadores",
           "tema_central": "Quando a criança diz 'não' o tempo todo",
           "descricao_curta": "Ensaio sobre desobediência em crianças...",
           "palavras_chave": ["desobediência", "autonomia", "fase do não", ...],
           "autoridades": ["Sanders (Triple P)", "Eyberg (PCIT)", ...],
           "ver_tambem": [4, 5, 13],  # números dos arquivos referenciados
           "palavras_count": 10450,
           "refs_count": 46,
       },
       # ... 19 entradas no total
   }
   ```

6. **Validação cruzada:**
   - Todo arquivo da pasta (exceto `00-indice.md`) deve aparecer no
     manifest. Se faltar, **parar e perguntar**.
   - Todo arquivo listado no manifest deve existir na pasta. Se faltar,
     **parar e perguntar**.
   - Total deve bater: 19 arquivos + 1 índice = 20 arquivos.

**Etapa 2 — Ingestão dos 19 ensaios com chunking por H2:**

Ao processar cada ensaio, o pipeline:

1. Identifica seções por H2 dentro do arquivo. Cada H2 define um chunk
   candidato (ver §3.5 para a estratégia de chunking detalhada).
2. Identifica o `section_type` de cada seção:
   - `"visao_geral"` — primeira seção H2 (visão geral)
   - `"conteudo"` — seções H2 principais
   - `"glossario"` — H2 chamado "Glossário"
   - `"referencias"` — H2 chamado "Referências"
3. Para cada chunk gerado, **adiciona à metadata** todos os campos do
   manifest correspondentes ao arquivo (ver schema completo em §3.6).

**Etapa 3 — Ingestão do próprio `00-indice.md`:**

Por último, o índice é ingerido como documento, **com tratamento
diferenciado**:

- Chunking conservador: cada bloco temático (`## Bloco I`, etc.) vira um
  chunk único, sem subdivisão.
- Metadata: `is_manifest: true`, `source_file: "00-indice.md"`,
  `file_number: 0`, `bloco_tematico: "0"`, `bloco_nome: "Índice mestre"`.
- A tabela "Visão de conjunto" e a seção "Mapa de referências cruzadas"
  são chunks separados, com `section_type: "indice_visao_geral"` e
  `section_type: "indice_referencias_cruzadas"`.

#### Como isso melhora a recuperação

Com `bloco_tematico` e `palavras_chave` na metadata, queries futuras
podem filtrar e priorizar chunks. Exemplos de melhorias iterativas
**não obrigatórias** nesta sprint:

- Filtro por bloco: `filter={"bloco_tematico": "III"}` para perguntas
  sobre comportamento desafiador.
- Fallback de retrieval via `ver_tambem`: se a primeira query top-5 não
  retornar resultados de qualidade suficiente, expandir buscando chunks
  de arquivos referenciados na lista "Ver também" do arquivo top-1.
- Boosting de chunks `section_type: "conteudo"` em detrimento de
  `"glossario"` e `"referencias"`, para evitar respostas que citem
  glossário como conteúdo principal.

Nada disso é obrigatório agora — basta gravar a metadata corretamente.
A exploração desses filtros fica como melhoria iterativa após validação
qualitativa da recuperação.

#### Perguntar antes de prosseguir se…

- O parser do índice falhar em qualquer arquivo (formato divergente do
  padrão H3 + bullets de Palavras-chave/Autoridades/Ver também).
- A contagem de arquivos não bater com o esperado (19 ensaios + 1
  índice = 20 arquivos).

### 3.3 Interface `VectorStore` (NOVO — não estava no sprint original)

Em `app/rag/vector_store.py`, defina uma classe abstrata e duas
implementações:

**Interface ABC:**

- `upsert(items: list[VectorItem]) -> None` — insere ou atualiza chunks
  em batch. Cada `VectorItem` contém: `id` (str determinístico), `vector`
  (list[float]), `metadata` (dict), `content` (str).
- `query(vector: list[float], top_k: int = 5, filter: dict | None = None) -> list[QueryResult]` — retorna chunks mais similares.
- `delete_by_filter(filter: dict) -> int` — deleta por metadata (ex:
  todos os chunks de um `source_file` específico). Retorna quantidade
  deletada.
- `count() -> int` — total de vetores no índice.

**`LocalVectorStore` (Chroma):**

- Backend: `chromadb.PersistentClient(path=settings.CHROMA_PATH)`.
- Collection name: `maia-rag` (configurável via env).
- `path` default: `./.chroma/` na raiz de `maia-backend` — adicionar ao
  `.gitignore`.
- Distância: cosseno.
- Implementa todos os métodos da interface usando a API do Chroma.

**`PineconeVectorStore` (stub):**

- Importa `pinecone` (mas marca import como opcional — `try/except
  ImportError` com mensagem clara).
- Construtor recebe `api_key`, `index_name`, `environment` de `settings`.
- **Todos os métodos lançam `NotImplementedError("PineconeVectorStore
  será implementado na sprint de promoção a produção. Por enquanto, use
  VECTOR_STORE_BACKEND=local.")`** EXCETO `__init__`, que valida que as
  envs do Pinecone existem (para falhar cedo se mal configurado).
- A assinatura dos métodos é **idêntica** à do `LocalVectorStore` — esta
  é a garantia da abstração.

**Factory:**

```python
def get_vector_store() -> VectorStore:
    """Retorna a implementação configurada via VECTOR_STORE_BACKEND."""
    backend = settings.VECTOR_STORE_BACKEND
    if backend == "local":
        return LocalVectorStore(...)
    if backend == "pinecone":
        return PineconeVectorStore(...)
    raise ValueError(f"VECTOR_STORE_BACKEND inválido: {backend}")
```

Todo código fora de `app/rag/vector_store.py` deve consumir apenas
`get_vector_store()` ou a interface — **nunca** importar Chroma ou
Pinecone diretamente.

### 3.4 Demais módulos (atualizado para o corpus real)

- `loaders.py` — PDF (`pypdf` ou `pdfplumber`), DOCX (`python-docx`),
  MD/TXT (builtin). **O corpus em `knowledge/` é majoritariamente
  Markdown** (19 ensaios `.md` + o índice `.md`), então o loader de MD
  é o mais crítico. Pare e pergunte se encontrar PDF escaneado.

- `chunking.py` — **chunking primário por H2** (estratégia indicada
  pelo próprio autor do corpus em `00-indice.md` §"Notas para uso").
  Detalhamento:

  - **Unidade base:** cada `## H2` dentro de um arquivo é uma unidade
    semântica autocontida e vira um chunk candidato.
  - **Tamanho típico esperado:** entre 400 e 1200 palavras por seção
    H2 (já confirmado pelo autor do corpus).
  - **Subdivisão:** se uma seção H2 exceder ~1500 tokens (≈1000-1100
    palavras), subdividir respeitando fronteiras de parágrafo, com
    overlap de ~10% (manter o título do H2 como cabeçalho de cada
    sub-chunk para preservar contexto).
  - **`section_type` por chunk** (gravado em metadata):
    - `"visao_geral"` — primeiro H2 do arquivo (geralmente "Visão
      geral" ou similar)
    - `"conteudo"` — H2 principais do ensaio (default)
    - `"glossario"` — H2 chamado "Glossário"
    - `"referencias"` — H2 chamado "Referências"
    - `"indice_visao_geral"`, `"indice_referencias_cruzadas"` —
      apenas para chunks do `00-indice.md`
  - **Cabeçalho preservado:** o título do H2 de origem é incluído como
    primeira linha do chunk (`# <título do H2>`), facilitando re-ranking
    e exibição em debug.
  - **Não usar chunking fixo de caracteres ignorando estrutura.**

- `embeddings.py` — wrapper sobre OpenAI `text-embedding-3-small`
  (decisão travada na §0.2 e §2 item 1). Retry/backoff exponencial em
  rate limit (429) e erros 5xx.

- `ingest.py` — CLI principal. Comando: `python -m app.rag.ingest --source /data/knowledge`.

### 3.5 Idempotência

Cada chunk recebe `id` determinístico = hash do conteúdo normalizado +
`source_file` + `chunk_index`. Re-rodar o script:

- Em diretório inalterado → zero upserts novos.
- Arquivo modificado → deleta todos os chunks antigos daquele
  `source_file` (via `delete_by_filter({"source_file": ...})`) e
  reingere.

### 3.6 Metadata schema

```python
{
    # === Identificação do chunk ===
    "source_file": str,                # ex: "06-desobediencia.md"
    "file_number": int,                # ex: 6 (0 para o índice, 1-19 para ensaios)
    "chunk_index": int,                # índice do chunk dentro do arquivo
    "ingested_at": str,                # ISO 8601

    # === Estrutura no documento ===
    "section_h2": str,                 # heading H2 da seção de origem
    "section_type": str,               # "visao_geral" | "conteudo" | "glossario"
                                       # | "referencias" | "indice_visao_geral"
                                       # | "indice_referencias_cruzadas"

    # === Metadata do manifesto (do 00-indice.md) ===
    "file_title": str,                 # título completo do ensaio
    "bloco_tematico": str,             # "I" | "II" | "III" | "IV" | "V" | "VI" | "0"
    "bloco_nome": str,                 # ex: "Comportamentos desafiadores"
    "tema_central": str,               # frase curta da tabela "Visão de conjunto"
    "descricao_curta": str,            # parágrafo de descrição do índice
    "palavras_chave_csv": str,         # CSV: "desobediência,autonomia,fase do não,..."
    "autoridades_csv": str,            # CSV: "Sanders (Triple P),Eyberg (PCIT),..."
    "ver_tambem_csv": str,             # CSV de números: "4,5,13"
    "palavras_count": int,             # contagem de palavras do arquivo
    "refs_count": int,                 # contagem de referências bibliográficas

    # === Flags ===
    "is_manifest": bool,               # True apenas para chunks do 00-indice.md

    # === Debug ===
    "content_preview": str,            # primeiros 200 chars do chunk
}
```

**Restrição de tipos no Chroma — importante:** valores de metadata no
Chroma só aceitam tipos primitivos (`str`, `int`, `float`, `bool`). Não
aninhar dicts nem listas. Por isso `palavras_chave`, `autoridades` e
`ver_tambem` são serializados como **strings CSV** (sufixo `_csv`).

Para queries que precisem trabalhar com essas listas, criar um helper
`parse_csv_metadata(value: str) -> list[str]` em `app/rag/manifest.py`,
e usar à vontade no código que consome a metadata. Manter a serialização
CSV simples: separador vírgula, sem aspas, sem escape (os campos do
índice não contêm vírgulas dentro dos próprios itens).

**Sobre campos `None`:** Chroma rejeita `None` em metadata. Se um campo
não se aplica (ex: chunk do `00-indice.md` não tem
`descricao_curta` próprio), omitir a chave inteira em vez de gravar
`None`.

### 3.7 Avaliação qualitativa

- Criar `tests/rag/queries.jsonl` com 10–15 perguntas de exemplo
  (sugeridas pelo Claude Code com base no conteúdo de `knowledge/`,
  mas com confirmação do usuário antes de gravar).
- Script `eval_retrieval.py` que roda top-k=5 para cada query e imprime
  os chunks retornados. Avaliação manual pelo usuário.

### 3.8 Inventário e observabilidade

- Antes de processar: relatório `docs/rag-inventory.md` listando todos os
  arquivos, tamanhos e tipos.
- Durante: log estruturado de arquivos processados, chunks gerados,
  tempo por etapa, custo estimado de embeddings.
- Após: summary em `data/rag-ingestion-<timestamp>.json`.

### 3.9 Documentação

`app/rag/README.md` cobre:

- Como adicionar novos documentos.
- Como reingerir um arquivo específico.
- Como limpar o índice local (`rm -rf .chroma/` + reingest).
- Como rodar a avaliação.
- **Como será a promoção para Pinecone no futuro:** mesma rotina de
  ingestão, mudando `VECTOR_STORE_BACKEND=pinecone` e exportando as envs
  do Pinecone. Nenhum código de domínio muda.

### 3.10 Critérios de aceite — Sprint 07

- [ ] Bind mount do Docker funciona: arquivos de `knowledge/` são
      visíveis em `/data/knowledge` dentro do container.
- [ ] `00-indice.md` é parseado com sucesso, extraindo os 19 ensaios
      organizados em 6 blocos temáticos (I-VI), com palavras-chave,
      autoridades e referências cruzadas para cada um.
- [ ] Validação cruzada do índice passa: total de 20 arquivos (19
      ensaios + 1 índice), todos os ensaios listados existem na pasta,
      e nenhum arquivo da pasta está fora do índice.
- [ ] Chunking por H2 funciona: cada seção H2 vira um chunk (com
      subdivisão apenas se exceder ~1500 tokens). Cabeçalho do H2 é
      preservado como primeira linha de cada chunk.
- [ ] Cada chunk tem `section_type` correto (`visao_geral`, `conteudo`,
      `glossario`, `referencias`, ou variantes do índice).
- [ ] **Cada chunk** (exceto chunks do próprio `00-indice.md`) tem
      metadata completa do manifesto: `file_number`, `file_title`,
      `bloco_tematico`, `bloco_nome`, `tema_central`, `descricao_curta`,
      `palavras_chave_csv`, `autoridades_csv`, `ver_tambem_csv`.
- [ ] Chunks do próprio `00-indice.md` têm `is_manifest: true`,
      `bloco_tematico: "0"`.
- [ ] `LocalVectorStore.count()` retorna número consistente com chunks
      gerados.
- [ ] Query manual com filtro `{"bloco_tematico": "III"}` retorna
      apenas chunks dos arquivos 06-09 (Bloco III) — prova que metadata
      foi gravada corretamente.
- [ ] Helper `parse_csv_metadata()` funciona: dado um chunk, extrai
      `palavras_chave` como lista de strings.
- [ ] Re-rodar em diretório inalterado → zero upserts novos.
- [ ] Modificar um arquivo → apenas chunks daquele arquivo atualizados.
- [ ] `eval_retrieval.py` retorna chunks plausíveis para 10+ queries.
- [ ] Custo de embeddings da rodada inicial documentado (esperado:
      ~165k palavras × ~1.3 tokens/palavra × $0.02/1M tokens =
      aproximadamente $0.005 — barato, mas confirmar com a contagem real).
- [ ] `PineconeVectorStore.__init__` instancia sem erro quando envs
      estão setadas (mesmo sem implementação dos métodos).
- [ ] Trocar `VECTOR_STORE_BACKEND=pinecone` no `.env` faz a aplicação
      tentar usar Pinecone (e levantar `NotImplementedError` ao chamar
      um método) — **prova** que a abstração está corretamente plugada.
- [ ] README do módulo completo, incluindo: seção sobre os 6 blocos
      temáticos, como o parser do índice funciona, como atualizar o
      manifesto ao adicionar novos documentos, exemplos de queries
      filtradas por bloco/section_type.

### 3.11 Não fazer — Sprint 07

- Não use chunking fixo de caracteres sem respeitar fronteiras de
  sentença/parágrafo.
- Não importe `chromadb` ou `pinecone` fora de `vector_store.py`.
- Não ingira PDFs escaneados sem OCR — pare e pergunte.
- Não commite `.chroma/` no git (adicionar ao `.gitignore`).
- Não commite o conteúdo de `knowledge/` se houver dúvida de direitos
  autorais — confirme com o usuário.

### 3.12 Perguntar antes de prosseguir se…

- `knowledge/` incluir PDFs escaneados.
- Houver dúvida sobre direitos autorais dos documentos.

(Provider de embeddings já está travado: `text-embedding-3-small` da
OpenAI — ver §0.2 e §2 item 1.)

---

## 4. Sprint 08 adaptado — Backend FastAPI local-dev

**Repositório:** `maia-backend`.
**Objetivo:** Backend FastAPI completo rodando em `http://localhost:8000`,
com auth Supabase JWT, endpoint `/v1/chat` que orquestra RAG + Claude +
persistência, **sem Nginx, sem Certbot, sem deploy**.

### 4.1 DIFF vs sprint original

| Aspecto | Sprint original | Versão local-dev |
|---|---|---|
| Reverse proxy | Nginx + Certbot em container | **Não tem.** Acesso direto a Uvicorn em `:8000`. |
| TLS | Let's Encrypt | HTTP puro em localhost |
| `docker-compose.prod.yml` | Sim | **Não criar nesta sprint.** |
| `nginx/maia.conf` | Sim | **Não criar nesta sprint.** |
| Workers | Múltiplos workers | 1 worker com `--reload` |
| Volume mount do código | Não (imagem buildada) | Sim (hot reload em dev) |
| Vector DB | Pinecone | ChromaDB via `LocalVectorStore` (factory já cuida) |
| Rate limiting | 60/20/120 req/min | Limites generosos (ex: 1000 req/min) ou desligado em dev |
| Sentry | Opcional | Desligado |
| CI/CD | GitHub Actions | **Não criar nesta sprint.** |
| Domínio | `api.maia.app` | `localhost:8000` |

### 4.2 Estrutura final do repo `maia-backend`

```
app/
  main.py                     # FastAPI app + lifespan
  core/
    config.py                 # pydantic-settings (inclui VECTOR_STORE_BACKEND)
    logging.py                # structlog setup
    security.py               # JWT validation, HMAC
  api/
    deps.py                   # dependencies (current_user, etc)
    v1/
      chat.py                 # POST /v1/chat
      conversations.py        # GET /v1/conversations, /{id}/messages
      health.py               # GET /v1/health
      webhooks/
        hubla.py              # (Sprint 05 — pode ser stub se não existir)
        whatsapp.py           # stub (Sprint 10)
  services/
    chat_service.py           # orquestra RAG + LLM + persistência
    conversation_service.py
    email_service.py          # Resend (pode ser stub em dev)
  rag/                        # (Sprint 07)
  llm/
    llm_client.py             # interface ABC + factory get_llm_client()
    anthropic_client.py       # implementação AnthropicClient
    openai_client.py          # implementação OpenAIClient
    prompts/
      __init__.py             # factory get_system_prompt(provider)
      system_anthropic.py     # system prompt otimizado para Claude
      system_openai.py        # system prompt otimizado para GPT
    tools/
      base.py                 # BaseTool ABC
      __init__.py             # registry (vazio em v1)
  db/
    supabase.py
    models.py                 # Pydantic
  middleware/
    rate_limit.py             # limites generosos em dev
    request_id.py
tests/
  test_chat.py
  test_auth.py
  conftest.py
Dockerfile
docker-compose.yml            # APENAS dev
.env.example
.gitignore                    # inclui .chroma/, .env
pyproject.toml
README.md
```

**Não criar nesta sprint:** `docker-compose.prod.yml`, `nginx/maia.conf`,
arquivos de GitHub Actions.

### 4.3 `docker-compose.yml` (dev)

Um único serviço `api`:

- Build a partir do `Dockerfile` local.
- Volume mount do código fonte (`./app:/app/app`) para hot reload.
- Volume mount do diretório `.chroma/` para persistir embeddings entre
  restarts do container.
- Variáveis de ambiente do `.env`.
- Expor porta `8000:8000`.
- Comando: `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`.
- `restart: unless-stopped` (opcional em dev).

**Não incluir** serviços `nginx` nem `certbot` neste arquivo.

### 4.4 Configuração (`app/core/config.py`)

`pydantic-settings` lendo do `.env`. Variáveis:

**LLM (multi-provider):**
- `LLM_PROVIDER` (default: `anthropic`) — valores aceitos: `anthropic`,
  `openai`.
- `LLM_MODEL` (default: `claude-sonnet-4-5`) — nome exato do modelo
  conforme o provider escolhido.
- `ANTHROPIC_API_KEY` — sempre presente (permite trocar provider sem
  reconfigurar).
- `OPENAI_API_KEY` — sempre presente (usado para LLM E embeddings).

**Validação no boot:** se `LLM_PROVIDER=anthropic`, exigir
`ANTHROPIC_API_KEY` e validar que `LLM_MODEL` começa com `claude-`. Se
`LLM_PROVIDER=openai`, exigir `OPENAI_API_KEY` e validar que `LLM_MODEL`
começa com `gpt-`. Falhar cedo com mensagem clara se inconsistente.

**Supabase:**
- `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`,
  `SUPABASE_JWT_SECRET`.

**Vector store:**
- `VECTOR_STORE_BACKEND` (default: `local`).
- `CHROMA_PATH` (default: `./.chroma`), `CHROMA_COLLECTION` (default:
  `maia-rag`).
- `PINECONE_API_KEY`, `PINECONE_INDEX`, `PINECONE_ENVIRONMENT` (opcionais
  em dev — só validar se `VECTOR_STORE_BACKEND=pinecone`).

**Embeddings (decisão travada — OpenAI):**
- `EMBEDDING_PROVIDER=openai`
- `EMBEDDING_MODEL=text-embedding-3-small`
- (a `OPENAI_API_KEY` já listada acima é reusada para embeddings)

**Outros:**
- `RESEND_API_KEY` (opcional em dev).
- `ENV=development` (controla logs, rate limits, etc).

### 4.5 Autenticação (mantida do sprint original)

- Dependency `get_current_user`:
  - Lê header `Authorization: Bearer <token>`.
  - Valida JWT com `SUPABASE_JWT_SECRET` (algoritmo HS256).
  - Extrai `user_id` (`sub` claim).
  - Consulta tabela `profiles`: usuário deve existir e ter
    `plan in ('trial', 'active')`.
  - Retorna o objeto `User`.
- Rotas públicas (isentas): `/v1/health`, webhooks (validação HMAC
  própria).
- Erros: 401 (token ausente/inválido), 403 (sem plano ativo).

### 4.6 Camada LLM: interface `LLMClient` + system prompts por provider

Esta seção é o coração da abstração multi-provider. Trate com o mesmo
rigor da `VectorStore`.

#### 4.6.1 Interface `LLMClient` (`app/llm/llm_client.py`)

Classe abstrata (ABC) com métodos:

- `complete(messages: list[Message], system: str, model: str, **kwargs) -> CompletionResult` — completion não-streaming. Retorna texto + tokens
  in/out + metadata.
- `stream(messages: list[Message], system: str, model: str, **kwargs) -> AsyncIterator[str]` — só implementar se streaming estiver na sprint.

`Message` é um dataclass/Pydantic com `role` (`user`|`assistant`) e
`content` (str). Cada implementação converte para o formato nativo do
SDK.

`CompletionResult` contém `text`, `input_tokens`, `output_tokens`,
`stop_reason`, `model_used`.

**Factory:**

```python
def get_llm_client() -> LLMClient:
    """Retorna a implementação configurada via LLM_PROVIDER."""
    provider = settings.LLM_PROVIDER
    if provider == "anthropic":
        return AnthropicClient(api_key=settings.ANTHROPIC_API_KEY)
    if provider == "openai":
        return OpenAIClient(api_key=settings.OPENAI_API_KEY)
    raise ValueError(f"LLM_PROVIDER inválido: {provider}")
```

**Factory de system prompt** (`app/llm/prompts/__init__.py`):

```python
def get_system_prompt(provider: str | None = None) -> str:
    """Retorna o system prompt correto para o provider ativo."""
    provider = provider or settings.LLM_PROVIDER
    if provider == "anthropic":
        from .system_anthropic import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    if provider == "openai":
        from .system_openai import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    raise ValueError(f"Provider sem prompt definido: {provider}")
```

#### 4.6.2 Implementações

**`AnthropicClient` (`app/llm/anthropic_client.py`):**
- Wrapper sobre `anthropic.Anthropic` SDK.
- `complete()` chama `client.messages.create(model=..., system=..., messages=...)`.
- Suporta os modelos: `claude-sonnet-4-5`, `claude-haiku-4-5-20251001`.
- Retry/backoff em rate limit (429) e erros 5xx.

**`OpenAIClient` (`app/llm/openai_client.py`):**
- Wrapper sobre `openai.OpenAI` SDK.
- `complete()` chama `client.chat.completions.create(...)` ou
  `client.responses.create(...)` — confirmar API recomendada para
  modelos `gpt-5.4*` na documentação atual da OpenAI.
- O system prompt é passado como primeira mensagem com `role="system"`
  no formato OpenAI (diferente do Anthropic, que usa parâmetro `system`
  separado).
- Suporta os modelos: `gpt-5.4`, `gpt-5.4-mini`.
- Retry/backoff equivalente.

#### 4.6.3 System prompts — conteúdo idêntico, estilo distinto

Ambos os prompts cobrem o mesmo material:

- **Personalidade:** "amiga especialista" — acolhedora, validadora,
  empática, prática, baseada em evidências, sem academicismo nem jargão.
  Tom definido no `00-indice.md`: evidência traduzida em linguagem
  cotidiana, com "como aplicar isso amanhã de manhã".
- **Papel:** assistente conversacional para mães de crianças de **1 a 5
  anos** (com aplicação parcial a recém-nascidos e idade escolar
  inicial). O conteúdo do MaIA cobre os 6 blocos temáticos do corpus
  (ver §0.1 e `00-indice.md`):
  1. Bem-estar e saúde mental dos cuidadores
  2. Regulação emocional e disciplina
  3. Comportamentos desafiadores
  4. Rotinas e infraestrutura familiar
  5. Brincar e ambiente preparado
  6. Síntese cultural integradora (Hunt Gather Parent)
- **Guardrails (não negociáveis):**
  - Nunca dar diagnóstico médico.
  - Em caso de sinal de perigo (depressão pós-parto severa, pensamentos
    suicidas, emergência com a criança), sempre redirecionar para
    profissional / SAMU 192 / CVV 188.
  - Faixa etária do conteúdo: 1 a 5 anos. Para perguntas fora dessa
    faixa, indicar a limitação e sugerir profissional ou recurso
    apropriado.
  - Tom em pt-BR, conversacional, "amiga especialista" — nunca
    professoral.
  - Usar contexto do RAG quando disponível; quando não houver contexto
    relevante, responder com cautela e indicar limitação. Não inventar
    autoridades ou referências (o corpus tem ~697 referências reais —
    citar apenas o que vem nos chunks recuperados).

**O que muda entre os dois prompts é o estilo de instrução:**

`system_anthropic.py` deve usar:
- Estrutura com **XML tags** (`<persona>`, `<guardrails>`,
  `<blocos_tematicos>`, `<rag_handling>`) — Claude responde melhor a
  estrutura hierárquica explícita.
- Linguagem narrativa quando descreve o papel e o tom.
- Os guardrails podem ser dados como princípios; Claude segue bem
  diretrizes em prosa.

`system_openai.py` deve usar:
- Estrutura com **seções nomeadas em markdown** (`## Personalidade`,
  `## Guardrails`, `## Blocos temáticos`).
- Listas numeradas e bullets para regras — GPT segue melhor regras
  enumeradas explicitamente.
- Guardrails formulados como "você deve" + condicional explícito
  ("Se o usuário mencionar X, então faça Y").

**O Claude Code deve mostrar AMBOS os system prompts ao usuário antes
de finalizar a sprint** para validação. Esta etapa é mandatória.

#### 4.6.4 Regra de ouro — não vazar SDKs

- `chat_service.py`, endpoints, tudo mais — chamam `get_llm_client()`,
  nunca `from anthropic import ...` ou `from openai import ...`.
- Imports diretos dos SDKs ficam confinados a `app/llm/anthropic_client.py`
  e `app/llm/openai_client.py`.
- Mesma regra do `VectorStore`. Disciplina é o que torna trocar o
  provider trivial.

### 4.7 Endpoint `POST /v1/chat`

Fluxo:

1. Valida auth (`get_current_user`).
2. Busca ou cria `conversation` (se `conversation_id` for null no payload).
3. Persiste mensagem do usuário em `messages` (Supabase).
4. Recupera histórico recente (últimas N=10 mensagens) da conversa.
5. Roda RAG: gera embedding da mensagem do usuário → `vector_store.query(top_k=5)` → extrai contexto.
6. Carrega o system prompt correto via `get_system_prompt()` (escolhe
   automaticamente entre `system_anthropic.py` e `system_openai.py`
   conforme `LLM_PROVIDER`).
7. Monta payload: system prompt + contexto RAG (injetado como bloco
   delimitado dentro do system ou da última user message — escolher e
   documentar) + histórico + mensagem atual.
8. Chama `llm_client.complete(messages=..., system=..., model=settings.LLM_MODEL)`
   via factory `get_llm_client()`. **Nunca** chamar `anthropic.*` ou
   `openai.*` diretamente.
9. Tool use: `BaseTool` registry está vazio em v1 — não passar tools
   nesta sprint.
10. Persiste resposta do assistente em `messages` com `tokens_in/out`
    e `model_used` (do `CompletionResult`).
11. Retorna payload conforme contrato do `PROJECT.md` §7.

**Streaming SSE:** apenas se o usuário confirmou na pergunta inicial.
Caso contrário, deixar `/v1/chat/stream` para depois. **Importante:** se
streaming entrar nesta sprint, ambas as implementações
(`AnthropicClient.stream` e `OpenAIClient.stream`) precisam estar
funcionais — não deixar uma só implementada.

### 4.8 Outros endpoints

- `GET /v1/health` — retorna `{"status": "ok", "version": "..."}`. Pública.
- `GET /v1/conversations` — lista conversas do usuário autenticado.
- `GET /v1/conversations/{id}/messages` — mensagens de uma conversa
  (autorização: usuário só vê suas conversas — RLS no Supabase + check
  redundante na aplicação).
- Webhooks (`/v1/webhooks/hubla`, `/v1/webhooks/whatsapp`): manter stubs
  ou implementação da Sprint 05 se já existir. Nesta sprint não é foco.

### 4.9 Observabilidade (versão dev)

- Middleware de `request_id` (UUID por request, propaga em logs).
- Log estruturado JSON via structlog em todas as rotas.
- Métricas básicas em log: latência por request, tokens consumidos.
- **Sem Sentry em dev.**

### 4.10 Rate limiting (versão dev)

Implementar com `slowapi` mas com limites generosos:

- Global: 1000 req/min por IP.
- `/v1/chat`: 200 req/min por usuário.

Documentar no README que os limites de produção (60/20/120) serão
aplicados na sprint de promoção.

### 4.11 Testes

- Unitários: `chat_service` com `vector_store` e `llm_client` ambos
  mockados (interface ABC facilita o mock).
- Integração: happy path de `/v1/chat` com Supabase apontado para projeto
  de dev (ou fixtures locais).
- Segurança: request sem JWT → 401; JWT de usuário sem plano ativo → 403.
- **Teste da abstração `VectorStore`:** trocar `VECTOR_STORE_BACKEND=pinecone`
  num fixture e verificar que a aplicação tenta instanciar
  `PineconeVectorStore` (e levanta `NotImplementedError` numa query —
  prova que a factory funciona).
- **Teste da abstração `LLMClient`:** rodar o mesmo teste de `/v1/chat`
  com `LLM_PROVIDER=anthropic` e depois com `LLM_PROVIDER=openai`,
  confirmando que ambos retornam respostas válidas (com mocks dos SDKs
  para evitar custo). Confirma que `chat_service` não tem dependência
  hardcoded em nenhum provider.

### 4.12 Critérios de aceite — Sprint 08

- [ ] `docker compose up` local: API sobe sem erro, `/v1/health` retorna 200.
- [ ] `POST /v1/chat` com JWT válido retorna resposta coerente do MaIA
      usando contexto do `LocalVectorStore`.
- [ ] **Multi-provider funcional:** o mesmo `POST /v1/chat` retorna
      resposta válida com `LLM_PROVIDER=anthropic` E com
      `LLM_PROVIDER=openai` — basta trocar no `.env` e reiniciar o
      container. Sem mexer em código.
- [ ] **System prompt correto por provider:** teste manual confirma que
      `system_anthropic.py` é carregado quando provider é Anthropic, e
      `system_openai.py` quando é OpenAI. Logar qual prompt foi usado.
- [ ] Conversa persiste em Supabase (tabelas `conversations` e
      `messages`), com campo `model_used` registrando o modelo da
      resposta.
- [ ] Guardrails dos DOIS system prompts funcionam (testar com query
      sensível manualmente em ambos os providers).
- [ ] Sem JWT → 401; com JWT inválido → 401; com JWT sem plano ativo → 403.
- [ ] Hot reload funciona: editar `.py` reflete sem rebuild.
- [ ] Logs estruturados aparecem em `docker compose logs -f`, incluindo
      `llm_provider` e `llm_model` em cada request.
- [ ] Custo estimado por conversa documentado para os 4 modelos suportados
      (`claude-sonnet-4-5`, `claude-haiku-4-5-20251001`, `gpt-5.4`,
      `gpt-5.4-mini`) — preços oficiais buscados na documentação dos
      providers.
- [ ] README contém: como subir local, como derrubar, como ver logs,
      como rodar testes, **como trocar de provider**, e **uma seção
      "Promoção a produção" listando o que vai mudar** (Nginx, Certbot,
      prod compose, Pinecone, rate limits estritos, escolha definitiva
      de provider).

### 4.13 Não fazer — Sprint 08

- Não implemente tools complexas em v1 — registry pronto mas vazio.
- Não commite `.env` nem chaves.
- Não exponha stack trace em responses de erro mesmo em dev (loga, não
  vaza).
- Não crie `docker-compose.prod.yml`, `nginx/`, GitHub Actions, scripts
  de deploy.
- Não importe `chromadb` ou `pinecone` fora de `app/rag/vector_store.py`.
- Não importe `anthropic` ou `openai` fora de `app/llm/anthropic_client.py`
  e `app/llm/openai_client.py` respectivamente. **Sempre** consumir via
  `get_llm_client()`.
- Não compartilhe um único system prompt entre os providers — eles
  divergem no estilo de instrução. São dois arquivos separados.

### 4.14 Perguntar antes de prosseguir se…

- `LLM_PROVIDER` e `LLM_MODEL` default não estiverem definidos.
- Schema das tabelas Supabase (`profiles`, `conversations`, `messages`)
  não estiver criado — pedir confirmação ou pedir SQL para criar.
  Confirmar que a tabela `messages` tem coluna `model_used` (texto) para
  registrar o modelo de cada resposta.
- Streaming SSE deve entrar agora ou depois.
- Houver dúvida sobre conteúdo dos system prompts ou guardrails.
- API correta da OpenAI para modelos `gpt-5.4*` (Chat Completions vs
  Responses API) não estiver clara — buscar na documentação atual antes
  de escolher.

---

## 5. Sprint 09 adaptado — Webapp Astro+React local-dev

**Repositório:** `maia-webapp`.
**Objetivo:** Aplicação web (Astro + React + Tailwind) rodando em
`http://localhost:4321` (porta default do Astro), conversando com a API
em `http://localhost:8000`.

### 5.1 DIFF vs sprint original

| Aspecto | Sprint original | Versão local-dev |
|---|---|---|
| Deploy | Cloudflare Pages | **Não.** `npm run dev` local. |
| Domínio | `app.maia.app` | `localhost:4321` |
| API base URL | `https://<api-domain>` | `http://localhost:8000` (via env `PUBLIC_API_BASE_URL`) |
| Lighthouse target | ≥ 90 | Não obrigatório em dev (mas manter boa prática) |
| Stack | Astro + React (islands) | **Mantido — Astro + React + Tailwind.** |

### 5.2 Stack

- **Astro** para o shell (login, roteamento de páginas estáticas).
- **React island** para o chat (estado interativo).
- **Tailwind** para styling.
- **Supabase JS client** para auth (anon key apenas no client).
- Cliente HTTP: `fetch` nativo + helper que anexa JWT do Supabase no
  header `Authorization`.
- Estado: **Zustand** (mais simples que Context API com múltiplos
  stores; sem Redux).

### 5.3 Variáveis de ambiente do webapp

```
PUBLIC_API_BASE_URL=http://localhost:8000
PUBLIC_SUPABASE_URL=...
PUBLIC_SUPABASE_ANON_KEY=...
```

(Astro requer prefixo `PUBLIC_` para variáveis expostas ao client.)

**Nunca expor** `SUPABASE_SERVICE_ROLE_KEY` no webapp.

### 5.4 Fluxo de autenticação

- `/login` — formulário de email; envia magic link via Supabase Auth.
- `/auth/callback` — recebe o magic link, cria sessão Supabase,
  redireciona para `/`.
- Middleware de rota protegida (Astro middleware): sem sessão →
  redireciona para `/login`.

### 5.5 Interface de chat (`/`)

- **Sidebar** (colapsável no mobile): lista de conversas + botão "nova
  conversa".
- **Área principal:** histórico de mensagens da conversa atual + input
  no rodapé.
- **Input:** Enter envia, Shift+Enter quebra linha.
- **Resposta:** loading indicator simples (streaming só se backend
  expor — combinado na Sprint 08).
- **Markdown** básico nas respostas do assistente: negrito, itálico,
  listas, links. Use `react-markdown` ou similar.
- **Avatar** do assistente + nome "MaIA" em cada mensagem.
- **Mobile-first:** testar em 360×640 como prioridade.

### 5.6 Cliente HTTP

- Helper `apiClient` que:
  - Anexa `Authorization: Bearer ${supabase.session.access_token}` a
    cada request.
  - Trata 401 → força re-login (limpa sessão, redireciona para `/login`).
  - Retry automático em 5xx com backoff exponencial (máx 3 tentativas).

### 5.7 Design

- Seguir `branding-book-maia.html` (cores, tipografia).
- Mobile-first.
- **Dark mode:** apenas se confirmado na pergunta inicial.

### 5.8 Acessibilidade

- Navegação por teclado completa.
- Labels em todos os inputs.
- Contraste AA mínimo.
- Respeitar `prefers-reduced-motion`.

### 5.9 PWA

Apenas se confirmado na pergunta inicial.

### 5.10 Critérios de aceite — Sprint 09

- [ ] `npm run dev` em `maia-webapp` sobe Astro em `localhost:4321`.
- [ ] Magic link do Supabase loga o usuário e redireciona para o chat.
- [ ] Usuário sem sessão é bloqueado e redirecionado para `/login`.
- [ ] Enviar mensagem em `/` → resposta do MaIA aparece (vinda de
      `localhost:8000`).
- [ ] Histórico de conversas carrega via `GET /v1/conversations` e
      permite trocar entre conversas.
- [ ] Mobile (360px) usável sem scroll horizontal.
- [ ] Erros de rede e auth tratados com mensagens amigáveis em pt-BR.
- [ ] CORS configurado no backend para aceitar `http://localhost:4321`.

### 5.11 Não fazer — Sprint 09

- Não implementar pagamento/upgrade aqui.
- Não usar libs de chat prontas (ex: `chat-ui-kit`) — controle próprio.
- Não expor `SUPABASE_SERVICE_ROLE_KEY` no client.
- Não fazer deploy para Cloudflare Pages nesta sprint.

### 5.12 Perguntar antes de prosseguir se…

- Streaming SSE está disponível no backend (depende do que foi decidido
  na Sprint 08).
- Dark mode / PWA entram agora.
- Branding (cores exatas, fonte) não estiver claro a partir do
  `branding-book-maia.html`.

---

## 6. Sequência de execução recomendada

A ordem importa porque há dependências reais entre as sprints. Siga
exatamente esta ordem, com checkpoint humano em cada transição:

1. **Sprint 07 — RAG.** Plano → aprovação → execução → validação manual
   da recuperação (rodar `eval_retrieval.py`). Só passar para a 08
   quando o usuário confirmar que os chunks recuperados fazem sentido.
2. **Sprint 08 — Backend.** Plano → aprovação → execução → testar
   `/v1/chat` via Swagger UI (`http://localhost:8000/docs`) com um JWT
   válido. Só passar para a 09 quando o backend responder corretamente
   no Swagger.
3. **Sprint 09 — Webapp.** Plano → aprovação → execução → testar fluxo
   completo end-to-end (login → chat → resposta). Só dar a sprint como
   concluída quando todo o fluxo funcionar localmente.

Em cada transição, gerar um **commit limpo** no respectivo repo com
mensagem descrevendo o que foi entregue.

---

## 7. Critérios de aceite consolidados (versão local-dev)

A versão local-dev está pronta quando:

- [ ] `cd maia-backend && docker compose up` sobe a API em `localhost:8000`.
- [ ] `cd maia-webapp && npm run dev` sobe o webapp em `localhost:4321`.
- [ ] Usuário consegue logar com magic link, abrir chat, enviar
      mensagem, e receber resposta coerente do MaIA usando contexto
      do RAG local (Chroma).
- [ ] Conversa fica persistida em Supabase, com `model_used` registrado.
- [ ] **Multi-provider validado:** trocar `LLM_PROVIDER` no `.env`
      (anthropic ↔ openai) e `LLM_MODEL` correspondente, reiniciar o
      container, e ter respostas funcionais nos quatro modelos
      suportados — sem mexer em código.
- [ ] Trocar `VECTOR_STORE_BACKEND=pinecone` no `.env` faz a aplicação
      tentar usar Pinecone — provando que a abstração está plugada e a
      promoção futura a produção é uma troca de configuração, não de
      código.
- [ ] READMEs dos dois repos descrevem como subir local, como trocar de
      LLM provider, e o que vai mudar na promoção a produção.

---

## 8. Itens fora de escopo (lista explícita — não fazer)

Para evitar drift de escopo, o Claude Code **não deve**:

- Configurar Nginx, Certbot, Let's Encrypt, ou qualquer SSL.
- Criar `docker-compose.prod.yml` ou variantes de produção.
- Fazer deploy em Contabo, AWS, Hetzner, Cloudflare Pages, ou qualquer
  provedor.
- Configurar GitHub Actions, GitLab CI, ou qualquer CI/CD.
- Implementar webhooks reais de WhatsApp ou Hub.la (apenas stubs se
  necessário para a estrutura).
- Implementar `PineconeVectorStore` além do stub.
- Adicionar providers de LLM além de Anthropic e OpenAI nesta sprint
  (DeepSeek, Qwen, etc. — ficam para sprint futura, mas a abstração já
  deve permitir adição trivial).
- Configurar Sentry, Datadog, ou observability externa.
- Configurar dark mode ou PWA (a menos que confirmado).
- Implementar streaming SSE (a menos que confirmado).
- Substituir qualquer item da stack travada na §0.2.

Se algum desses surgir como necessidade durante a execução, **parar e
perguntar** em vez de assumir.
