# Feature: Gerador de Histórias Infantis

## Visão Geral

Aba dedicada no assistente MaIA para geração de histórias infantis personalizadas. Contexto criativo separado do chat de suporte emocional — modos cognitivos diferentes que não devem se misturar.

A MaIA extrai automaticamente contexto relevante do histórico do chat principal (nome da criança, idade, preferências mencionadas) para enriquecer a história sem exigir que a mãe repita informações.

---

## Decisões de Arquitetura

### Entrada de dados
Formulário na UI com validação client-side. Campos obrigatórios garantidos pela UI — não pelo modelo. O modelo só pede mais informações se detectar ambiguidade no tema fornecido.

**Campos obrigatórios:**
| Campo | Tipo | Notas |
|---|---|---|
| Nome da criança | texto | pré-preenchido se mencionado no chat |
| Personagens | texto (vírgula) | ex: "cachorrinho, fada" |
| Tema da história | texto livre | o que acontece |
| Lição / valor | texto livre | o que a história ensina |
| Tamanho | seleção | Curta / Média / Longa — ou "não sei" |

**Campo opcional:**
| Campo | Tipo | Notas |
|---|---|---|
| Referência criativa | texto livre | história de inspiração para estilo/estrutura |

### Tamanho por idade (fallback)
Quando a mãe seleciona "não sei" ou não informa a idade, usar a tabela abaixo:

| Idade | Tamanho recomendado | Palavras aprox. |
|---|---|---|
| 1–2 anos | Curta | ~200 palavras |
| 3 anos | Curta | ~300 palavras |
| 4 anos | Média | ~500 palavras |
| 5 anos | Média | ~700 palavras |
| Sem info | Curta | ~300 palavras |

### Banco de dados
Tabelas no Supabase existente (não banco separado).

**Tabela `stories`:**
```sql
id uuid PRIMARY KEY
user_id uuid REFERENCES auth.users
child_name text
characters text[]
theme text
lesson text
size text  -- 'curta' | 'media' | 'longa'
reference text
titulo text
historia text
moral text
tags text[]
rating smallint  -- 1–5, nullable até a mãe avaliar
rating_notes text  -- campo livre opcional da mãe
model_used text
context_extracted jsonb  -- contexto extraído do chat principal
created_at timestamptz DEFAULT now()
```

**Tabela `story_audios`:**
```sql
id uuid PRIMARY KEY
story_id uuid REFERENCES stories
user_id uuid REFERENCES auth.users
voice_id text  -- ID da voz no ElevenLabs
storage_path text  -- caminho no Supabase Storage
expires_at timestamptz  -- created_at + 7 dias
duration_seconds integer
created_at timestamptz DEFAULT now()
```

**Política de retenção de áudio:** expiram em 7 dias. A mãe pode baixar para o device dentro desse período. Após expirar, o arquivo é removido do Storage (job periódico ou trigger).

### Contexto extraído do chat principal
Periodicamente (ou antes de cada geração), o sistema escaneia o histórico de conversas da usuária e extrai:
- Nome(s) da(s) criança(s) mencionados
- Idade mencionada
- Personagens favoritos, brincadeiras, medos, conquistas
- Qualquer informação que possa personalizar a história

Armazenado em `context_extracted` (jsonb) na tabela `stories` — registro de o que foi usado em cada geração.

### Notas e rating
Rating de 1–5 estrelas + campo de texto opcional. Armazenados em `stories`. Propósito imediato: analytics de produto (quais temas/personagens geram histórias melhor avaliadas). Uso futuro: histórias bem avaliadas viram exemplos few-shot no prompt.

### Áudio (v1)
- Integração com ElevenLabs API
- Vozes pré-definidas (femininas, suaves) — a mãe escolhe entre opções
- Clonagem de voz da mãe: **feature futura premium**
- Player inline na UI mobile
- Botão de download disponível por 7 dias
- Arquivos salvos no Supabase Storage

### Modelo de geração
A definir (Claude ou Gemini). System prompt especializado em literatura infantil, separado do system prompt da MaIA principal. Resposta em JSON estruturado.

---

## Fluxo Completo

```
Aba "Histórias"
  └── Formulário (campos obrigatórios + opcionais)
        └── Sistema extrai contexto do chat principal
              └── POST /v1/stories/generate
                    ├── Valida campos obrigatórios
                    ├── Monta prompt com inputs + contexto extraído
                    ├── Chama LLM com system prompt especializado
                    ├── Parseia JSON de resposta
                    └── Salva em tabela `stories`
                          └── UI exibe história completa
                                ├── Rating (1–5 estrelas) + nota opcional
                                └── Botão "Ouvir"
                                      └── POST /v1/stories/{id}/audio
                                            ├── Chama ElevenLabs
                                            ├── Salva em Storage (expira 7d)
                                            └── Player inline + botão download

Biblioteca de Histórias (tela separada dentro da aba)
  └── Lista todas as histórias da usuária
        ├── Filtros por criança, tema, rating
        ├── Acesso à história + áudio (se ainda válido)
        └── Indicador visual quando áudio expira
```

---

## System Prompt do Gerador

```
Você é um especialista em literatura infantil, com profundo conhecimento em
desenvolvimento infantil para crianças de 1 a 5 anos. Você cria histórias
encantadoras, originais e pedagogicamente ricas.

REGRAS INVIOLÁVEIS:
- Linguagem simples, frases curtas, vocabulário acessível para crianças pequenas
- Tom acolhedor, divertido e imaginativo — jamais assustador ou triste demais
- A lição deve emergir NATURALMENTE da história, nunca de forma explícita ou didática
- Personagens com personalidade marcante, ações concretas, diálogos vivos
- Estrutura narrativa clara: situação inicial → desafio → tentativas → resolução feliz
- Jamais mencione violência, medo intenso ou temas inadequados para a faixa etária
- Escreva em português brasileiro fluente e expressivo

FORMATO DA RESPOSTA (JSON puro, sem markdown):
{
  "titulo": "título criativo da história",
  "historia": "texto completo da história em parágrafos separados por \n\n",
  "moral": "a lição da história em uma frase bonita e memorável",
  "personagens": ["lista", "dos", "personagens"],
  "tags": ["tema1", "tema2"]
}
```

---

## Função de montagem do prompt

```python
SIZE_MAP = {
    "curta": "300 palavras",
    "media": "600 palavras",
    "longa": "1000 palavras",
}

def build_story_prompt(child_name, characters, theme, lesson, size, reference=None, context=None):
    reference_block = f"\n\nINSPIRAÇÃO CRIATIVA (use como referência de estilo/estrutura, mas crie algo original):\n{reference}" if reference else ""
    context_block = f"\n\nCONTEXTO DA CRIANÇA (extraído do histórico de conversas — use para personalizar):\n{context}" if context else ""

    return f"""Crie uma história infantil com as seguintes características:

- PROTAGONISTA: {child_name} (incorpore o nome naturalmente na história)
- PERSONAGENS: {characters}
- TEMA: {theme}
- LIÇÃO A TRANSMITIR: {lesson}
- TAMANHO: aproximadamente {SIZE_MAP[size]}{reference_block}{context_block}"""
```

---

## Próximas Features (backlog)

- [ ] Clonagem de voz da mãe via ElevenLabs (premium)
- [ ] Botão "Regenerar" — nova versão com os mesmos inputs
- [ ] Exportar história como PDF ilustrado
- [ ] Campo "idade exata" para calibrar vocabulário com mais precisão
- [ ] Modo "continuar a história" — novo capítulo
- [ ] Few-shot com histórias bem avaliadas (rating 4–5) no prompt
- [ ] Notificação push quando áudio está prestes a expirar
