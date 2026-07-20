# Guia — Criação de Essays para a Nova Faixa Etária (0–12 meses e 5–6 anos)

**Data:** 2026-07-19
**Contexto:** decisão de produto de ampliar a MaIA de 1–5 anos para recém-nascido a 6 anos. O prompt já cobre 1–6 anos; a faixa 0–12 meses só entra no system prompt quando os essays-núcleo de segurança estiverem ingeridos no Pinecone e validados por canários.
**Pipeline:** Perplexity Pro (pesquisa) → Claude Opus (redação) → revisão humana → ingestão → canários no maia-eval. O prompt-mestre de referência está em `docs/prompt-criacao-referencias.md` — este guia lista o que muda nele para a nova faixa.

---

## 1. Essays a criar

### Núcleo de segurança 0–12m — bloqueiam a liberação da faixa no prompt

| # | Arquivo | Tema | Observações críticas |
|---|---------|------|----------------------|
| 20 | `20-sono-seguro-0-12m.md` | Sono seguro do bebê | SIDS/morte súbita, posição de barriga para cima, berço vazio, compartilhamento de quarto vs de cama (apresentar posições da AAP e da SBP), temperatura. NÃO recomendar sleep training antes dos 6 meses. |
| 21 | `21-febre-sinais-alarme-bebes.md` | Febre e sinais de alarme no 1º ano | Regra inegociável: febre em menor de 3 meses = avaliação médica imediata, sempre. Sinais de alarme por faixa (letargia, gemência, recusa de mamadas, fontanela, manchas). Quando pediatra vs pronto-socorro vs SAMU. |
| 22 | `22-amamentacao.md` | Amamentação | Pega, dor, fissura, produção percebida vs real, complemento, desmame gentil, volta ao trabalho. Tom sem culpa para quem usa fórmula. |
| 23 | `23-introducao-alimentar.md` | Introdução alimentar | Início aos 6 meses, BLW vs tradicional vs misto (neutro), gag vs engasgo, alergênicos, água, sal/açúcar. |

### Complementares 0–12m — segunda leva

| # | Arquivo | Tema |
|---|---------|------|
| 24 | `24-choro-e-colicas.md` | Choro normal do bebê, cólicas, período PURPLE, quando o choro é sinal de alerta, exaustão dos pais e risco de shaken baby (colocar o bebê no berço e sair é ok) |
| 25 | `25-desenvolvimento-0-12m.md` | Marcos motores e de comunicação do 1º ano, variação normal, red flags que pedem pediatra |
| 26 | `26-sono-0-12m.md` | Expectativas realistas de sono por mês, regressões, sonecas, associações de sono — separado do essay de segurança (20) |
| 27 | — | Puerpério e saúde mental: **verificar antes** o que `01-saude-mental-materna.md` já cobre; provavelmente expandir o existente em vez de criar novo |

### 5–6 anos — terceira leva (baixo risco, sem urgência)

| # | Arquivo | Tema |
|---|---------|------|
| 28 | `28-vida-escolar-5-6.md` | Adaptação escolar, alfabetização (expectativas, não adiantar), lição de casa, queixas da escola |
| 29 | `29-autonomia-e-amizades-5-6.md` | Autonomia, regressões de comportamento, amizades, comparação com colegas — checar sobreposição com `13-colaboracao-responsabilidade.md` |

Numeração continua a partir do 19. Atualizar `00-indice.md` a cada leva (o índice é chunked e recuperável — é god node do grafo).

---

## 2. O que muda no prompt-mestre (vs `prompt-criacao-referencias.md`)

O template existente permanece válido (piloto de tom `01-saude-mental-materna.md`, 5.000–7.000 palavras, seções H2, glossário, referências `[^N]`, regra "sem invenção"). Adicionar/alterar:

1. **Metadados de faixa etária** no bloco HTML do topo:
   ```
   age_range: 0-12m        (ou 5-6a, 1-6a)
   ```
   Também registrar no manifest de ingestão. Hoje não filtra nada; na Fase 3 do plano de qualidade, o retrieval vai poder filtrar chunks pela idade da criança do perfil.

2. **Seção `## Quando procurar ajuda profissional` obrigatória** em todo essay 0–12m, com red flags concretos. O chunking é por H2 — essa seção vira chunk recuperável isolado, que é exatamente o que o RAG precisa achar em pergunta de sintoma.

3. **Fontes restritas para temas de segurança** (essays 20, 21, 23, 24): apenas autoridades — SBP, AAP, OMS, NHS, CDC, Ministério da Saúde. Blogs, influencers e consultorias de sono não entram como fonte de afirmação de segurança. Nos demais temas, a regra atual (fontes numeradas, zero invenção) basta.

4. **Debates com posição neutra e explícita**: cosleeping (apresentar posição AAP e a prática real brasileira, com redução de danos), sleep training (não antes de 6 meses; depois, dois lados como no essay 11), fórmula vs peito (sem culpa).

5. **Volume menor aceitável**: essays 0–12m podem ficar em 4.000–6.000 palavras — o tema é mais delimitado que os comportamentais.

---

## 3. Checklist de revisão humana (antes de ingerir)

- [ ] Spot-check de 3 referências aleatórias: existem e dizem o que o texto afirma
- [ ] Nenhum número/percentual sem referência `[^N]`
- [ ] Seção de red flags presente e correta (comparar com fonte de autoridade)
- [ ] Febre < 3 meses = emergência aparece no essay 21 sem ambiguidade
- [ ] Tom bate com o piloto (ler a Visão Geral em voz alta — soa como amiga, não como bula)
- [ ] Seções H2 entre ~300 e 800 palavras (chunking semântico corta por H2; seção gigante vira chunk diluído)
- [ ] Metadados HTML no topo com `age_range`
- [ ] Acentuação e ortografia pt-BR corretas

---

## 4. Ingestão (por leva)

```bash
# 1. Copiar os .md aprovados para knowledge/
# 2. Atualizar 00-indice.md com os novos essays
# 3. Conferir .env do maia-backend: VECTOR_STORE_BACKEND=pinecone (index assistente-maes)
#    Embedding travado: text-embedding-3-small — NÃO trocar
cd maia-backend
python -m app.rag.ingest --source ../knowledge
```

O hash tracking é incremental: só arquivos novos/alterados são reprocessados. Chunking atual em produção: `max_words=1000, overlap=10%` (decisão do benchmark de 2026-05-14 — não mudar sem re-benchmark).

---

## 5. Canários no maia-eval (por essay)

Para cada essay ingerido, adicionar em `maia-eval/scenarios/rag_canary.yml`:

- 2–3 perguntas-canário que puxem conteúdo específico do essay (taxonomia, framing ou recomendação que só existe nele — não conhecimento genérico de LLM)
- Check `keywords_any` com quorum de markers (paráfrase derruba match exato)
- `max_chars: 3000` (respostas RAG são longas)
- 1 anti-canário por leva: tema dentro da faixa etária mas fora do corpus → MaIA deve admitir limite

Rodar: `python runner.py rag_canary` (com `$env:PYTHONIOENCODING="utf-8"` no Windows) e também a suite `safety` como regressão.

---

## 6. Critério de liberação da faixa 0–12m no system prompt

Só editar o escopo dos dois prompts (`system_openai.py` + `system_anthropic.py`, em paridade) quando:

1. Essays 20–23 (núcleo de segurança) ingeridos no Pinecone
2. Canários dos 4 essays passando 100%
3. Suite `safety` sem regressão
4. Perfil suportando idade em meses (`child_birth_date` preenchida — Fase 2 do plano de qualidade), para a MaIA saber que o bebê tem 4 meses e não "0 anos"

Ao liberar: atualizar o bloco de escopo nos dois prompts, manter o guardrail "febre < 3 meses = avaliação imediata" (já presente desde a Fase 1) e adicionar canários de ponta a ponta com perfil de bebê.
