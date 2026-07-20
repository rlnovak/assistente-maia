Você vai escrever um ensaio longo, em português brasileiro, sobre **conflitos e brigas entre irmãos em famílias com crianças de 1 a 5 anos**. Esse texto vai compor a base de conhecimento de um chatbot RAG voltado a mães. Quem te lê é uma mãe leiga, esgotada, em busca de orientação prática e embasada — não um pesquisador.



# Contexto do projeto

Rafa está construindo um assistente virtual (chatbot RAG) para mães de crianças de 1 a 5 anos. Você é uma "amiga especialista": acolhedora, mas com lastro científico. Linguagem cotidiana, sem ser informal demais. Sem academicismo. Cada conceito complexo precisa ser traduzido com analogia ou exemplo concreto. Cada recomendação precisa ser acionável **hoje**, com a criança real, em casa real, com energia real.



**Importante — diferença entre 08 e 09:** O arquivo 08 (já escrito) trata de **ciúme** (a emoção subjacente, especialmente em torno da chegada de um irmão e da disputa por atenção dos pais). Este arquivo 09 trata de **conflito comportamental** (brigar, gritar, bater, disputar brinquedo, acusar, "ele começou", roubar, expulsar do quarto). Foque no manejo do CONFLITO em si, na mediação, em estratégias de resolução de disputas e de cultivo de relação fraterna positiva ao longo do tempo. Pode mencionar ciúme como uma das raízes possíveis, mas não desenvolva — esse é o tema do 08.



# Insumos obrigatórios — leia TODOS antes de escrever

1. **Arquivo-fonte (Perplexity Pro):** `C:\Users\rlnov\Arsenal de Funis com IA\referencias\Realize uma pesquisa aprofundada sobre abordagens.md` — esse é o material primário sobre conflitos e brigas entre irmãos. Use como base. As referências numeradas dentro dele são suas fontes principais.

2. **Piloto aprovado (sua referência de tom/estilo/estrutura):** `C:\Users\rlnov\Arsenal de Funis com IA\referencias\consolidado\01-saude-mental-materna.md` — leia INTEIRO. Replique o padrão: bloco de metadados HTML no topo, seções H2 fluídas como ensaio, glossário, lista de referências numeradas. O tom de voz deste arquivo é o teu norte.

3. **Briefing do produto:** `/sessions/nice-nifty-archimedes/mnt/Arsenal de Funis com IA/briefing-assistente-ia-maes.html` — entenda persona, voz e princípios da MaIA.

4. **Pesquisa de mercado:** `/sessions/nice-nifty-archimedes/mnt/Arsenal de Funis com IA/pesquisa-mercado-assistente-ia-maternidade.md` — para alinhamento de público.



# Enriquecimento por busca web

Use **WebSearch** (não WebFetch, que está bloqueado). Faça **no máximo 4 a 6 buscas web** focadas — não esgote tempo em busca. Foque em: Faber & Mazlish ("Siblings Without Rivalry") como referência cultural, Laurie Kramer (sibling intervention programs, "More Fun With Sisters and Brothers"), Hildy Ross e Nina Howe sobre mediação de conflito fraterno, mediação parental vs. não-intervenção, Ross Greene/Collaborative Problem Solving aplicado a conflitos fraternos, posição da AAP / Zero to Three sobre brigas entre irmãos, Janet Lansbury ("sportscasting"), Mona Delahooke. Procure dados quantitativos (effect sizes, RCTs recentes) e prevalências quando aparecerem naturalmente. Não invente nada. Se uma busca falhar, registre que aquele ponto ficou apenas no que está na fonte.



**Atenção a tempo:** o agente anterior nessa tarefa teve timeout. Seja eficiente — leia rápido, busque pouco, escreva direto.



# Formato do entregável

Crie o arquivo: `C:\Users\rlnov\Arsenal de Funis com IA\referencias\consolidado\09-conflitos-irmaos.md`



Estrutura obrigatória (espelhar 01-saude-mental-materna.md):

- Bloco `<!-- ... -->` HTML no topo com metadados (keywords, audiences, authorities, fontes principais, data)

- `# Título`

- `## Visão geral` (~400-500 palavras, abre com cena concreta — ex.: dois irmãos disputando o mesmo brinquedo aos berros, mãe tentando cozinhar enquanto o caos se forma)

- Várias seções `##` que conduzem o leitor por: brigar é normal nessa fase (frequência típica em estudos), por que brigar tem função desenvolvimental (treinar negociação, regulação, perspectiva), o que NÃO funciona (julgar quem começou, intervir cedo demais, comparar, tomar partido sistemático, punir o mais velho "porque ele já é grande", deixar 100% por conta deles em idade muito cedo), o que funciona (preparar o ambiente, ensinar negociação e turn-taking, mediar com método, "describe-don't-judge", emotion coaching antes da resolução, criar momentos positivos entre irmãos, ritualizar tempo conjunto, intervir quando há agressão física ou desequilíbrio de poder, ensinar reparação em vez de "pedir desculpa por automatismo"), guia prático passo-a-passo para situações típicas (briga por brinquedo, "ele me bateu", expulsão de quarto, acusação, viagem de carro, mesa de refeição, tablet/tv em comum, presentes), quando a briga sinaliza algo que precisa de profissional (red flags como agressão recorrente que machuca, padrão de bullying intra-familiar, sofrimento emocional persistente em um dos irmãos), micro-rotinas e roteiros de fala

- `## Glossário` (10–15 termos-chave traduzidos)

- `## Referências` — lista numerada `[^N]: Autor, Título, Veículo, Ano. URL/DOI`. Preserve TODAS as referências do arquivo-fonte e adicione as novas que vier da busca web.



# Regras invioláveis

- **Volume-alvo:** 5.000–7.000 palavras de corpo (não conta metadados, glossário, refs).

- **Tom:** acolhedor, validador, evidência traduzida. Comece capítulos com cenas/exemplos. Evite jargão; quando precisar, traduza.

- **Sem invenção:** zero dados ou estudos fabricados. Se não tem fonte, não fala. Se não tem certeza do número, omita o número.

- **Refs numeradas com `[^N]`** ao longo do texto, batendo com a lista final.

- **Português brasileiro**, ortografia atual.

- **Acionabilidade:** toda seção teórica precisa terminar com pelo menos um "como aplicar isso amanhã de manhã".

- **Mensagem central que precisa atravessar o ensaio:** brigas entre irmãos são parte natural da convivência e até teem valor desenvolvimental — não são sinal de família falida. O papel da mãe não é julgar nem evitar todo conflito, mas mediar com método, ensinar habilidades, e cultivar momentos positivos entre eles. Em paralelo, intervenção firme quando há agressão física, desequilíbrio recorrente de poder, ou sofrimento emocional.



# Como você sabe que terminou

Antes de declarar pronto, rode `wc -w` no arquivo final e reporte o número. Se ficou abaixo de 5.000 palavras (corpo), expanda. Se passou de 7.500, enxugue.



Reporte ao final: caminho do arquivo, contagem de palavras, número de seções H2, número de referências numeradas. Não cole o texto inteiro — só o sumário.




-----


Você vai escrever um ensaio longo, em português brasileiro, sobre **rotinas saudáveis de sono em crianças de 1 a 5 anos**. Esse texto vai compor a base de conhecimento de um chatbot RAG voltado a mães. Quem te lê é uma mãe leiga, esgotada, em busca de orientação prática e embasada — não um pesquisador.



# Contexto do projeto

Rafa está construindo um assistente virtual (chatbot RAG) para mães de crianças de 1 a 5 anos. Você é uma "amiga especialista": acolhedora, mas com lastro científico. Linguagem cotidiana, sem ser informal demais. Sem academicismo. Cada conceito complexo precisa ser traduzido com analogia ou exemplo concreto. Cada recomendação precisa ser acionável **hoje**, com a criança real, em casa real, com energia real.



# Insumos obrigatórios — leia TODOS antes de escrever

1. **Arquivo-fonte (Perplexity Pro):** `C:\Users\rlnov\Arsenal de Funis com IA\referencias\Realize uma pesquisa aprofundada sobre métodos mod.md` — material primário sobre métodos modernos baseados em evidências para rotinas saudáveis de sono em crianças de 1 a 5 anos. Use como base. As referências numeradas dentro dele são suas fontes principais.

2. **Piloto aprovado (referência de tom/estilo/estrutura):** `C:\Users\rlnov\Arsenal de Funis com IA\referencias\consolidado\01-saude-mental-materna.md` — leia INTEIRO. Replique o padrão.

3. **Briefing do produto:** `/sessions/nice-nifty-archimedes/mnt/Arsenal de Funis com IA/briefing-assistente-ia-maes.html`

4. **Pesquisa de mercado:** `/sessions/nice-nifty-archimedes/mnt/Arsenal de Funis com IA/pesquisa-mercado-assistente-ia-maternidade.md`



# Enriquecimento por busca web

Use **WebSearch** (não WebFetch). Faça **no máximo 4 a 6 buscas web** focadas — não esgaste tempo em busca. Foque em: AASM (American Academy of Sleep Medicine) consensus on sleep duration por faixa etária, AAP recomendações de sono e cosleeping, métodos de "extinção" — Ferber, "extinção gradual", "chair method", Pamela Druckerman "pause", Pinky McKay no contexto attachment, debate científico sobre sleep training (Mindell vs. Middlemiss), Sociedade Brasileira de Pediatria (SBP) sobre sono infantil, screen time e sono (AAP, melatonina), sonecas (transição de 2 para 1, abandono de soneca), terror noturno, pesadelos, sonolência diurna excessiva, parassonias na primeira infância. Não invente nada. Se uma busca falhar, use só o que está na fonte.



**Atenção a tempo:** seja eficiente — leia rápido, busque pouco, escreva direto.



**Posicionamento sobre debate sleep-training:** apresente os DOIS lados (extinção/Ferber vs. abordagens responsivas/atachment), com evidência para cada, e deixe a mãe escolher. Não tome partido ideológico. Foque no que funciona com base em evidência e no que respeita o ritmo de cada família.



# Formato do entregável

Crie o arquivo: `C:\Users\rlnov\Arsenal de Funis com IA\referencias\consolidado\11-rotinas-sono.md`



Estrutura obrigatória (espelhar 01-saude-mental-materna.md):

- Bloco `<!-- ... -->` HTML no topo com metadados (keywords, audiences, authorities, fontes principais, data)

- `# Título`

- `## Visão geral` (~400-500 palavras, abre com cena concreta — ex.: madrugada das 3h, criança chorando no berço pela quinta vez, pais exaustos)

- Várias seções `##` que conduzem o leitor por: por que sono importa (consolidação cerebral, regulação emocional, saúde mental dos pais), quanto a criança precisa dormir por idade (AASM/AAP), o que NÃO funciona (telas até cair no sono, horários totalmente erráticos, expectativa de "dorme a noite toda" muito cedo, comparação com outras crianças, métodos rígidos sem adaptação), o que funciona (rotina ritualizada de "wind-down", ambiente de sono — quarto escuro, fresco, sem tela, ancoragem do horário, exposição à luz natural de dia, alimentação adequada, atividade física, sleep associations saudáveis), o debate dos métodos (extinção/Ferber vs. abordagens responsivas — apresente os dois lados com evidência e respeite a escolha da família), guia prático para situações típicas (recusar dormir, despertares noturnos, transição do berço para a cama, transição de soneca, terror noturno, pesadelo, viagem/jet lag, doença), red flags que pedem profissional (apneia, sonolência diurna excessiva, ronco persistente, sintomas de privação crônica), micro-rotinas e roteiros (rotina noturna em 30-45 min, "boa noite" estruturada).

- `## Glossário` (10–15 termos-chave traduzidos)

- `## Referências` — lista numerada `[^N]: Autor, Título, Veículo, Ano. URL/DOI`. Preserve TODAS as referências do arquivo-fonte e adicione as novas que vier da busca web.



# Regras invioláveis

- **Volume-alvo:** 5.000–7.000 palavras de corpo (não conta metadados, glossário, refs).

- **Tom:** acolhedor, validador, evidência traduzida. Comece capítulos com cenas/exemplos. Evite jargão; quando precisar, traduza.

- **Sem invenção:** zero dados ou estudos fabricados. Se não tem fonte, não fala. Se não tem certeza do número, omita o número.

- **Refs numeradas com `[^N]`** ao longo do texto, batendo com a lista final.

- **Português brasileiro**, ortografia atual.

- **Acionabilidade:** toda seção teórica precisa terminar com pelo menos um "como aplicar isso amanhã de manhã".

- **Mensagem central:** dormir bem é uma habilidade que se aprende — e se ensina. Não existe método único certo, mas há estrutura, ritual, ambiente e consistência que aumentam muito as chances. Privação de sono dos pais não é "parte natural da maternidade", é problema de saúde pública.



# Como você sabe que terminou

Antes de declarar pronto, rode `wc -w` no arquivo final e reporte o número. Se ficou abaixo de 5.000 palavras (corpo), expanda. Se passou de 7.500, enxugue.



Reporte ao final: caminho do arquivo, contagem de palavras, número de seções H2, número de referências numeradas. Não cole o texto inteiro — só o sumário.