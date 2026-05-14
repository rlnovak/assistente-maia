# Subagente Gerador de Histórias Infantis

## Contexto

Dentro do produto de assistente para mães de crianças pequenas (1–5 anos), a vertical de **histórias customizadas** não demanda pesquisa no Perplexity — ela é uma *feature* de geração, implementada como um subagente especializado chamado pelo assistente principal.

---

## Inputs do subagente

| Campo | Descrição | Obrigatório |
|---|---|---|
| Nome da criança | Incorporado naturalmente na narrativa | Sim |
| Personagens | Separados por vírgula | Sim |
| Tema da história | O que acontece na história | Sim |
| Lição / valor | O que a história vai ensinar | Sim |
| Tamanho | Curta (~300), Média (~600) ou Longa (~1000 palavras) | Sim |
| Referência criativa | História de inspiração para estilo/estrutura | Não |

### Exemplo de referência criativa

> "Baseado na Rapunzel, mas a protagonista é uma gatinha chamada **Gatunzel** que vive numa torre feita de novelos de lã, e em vez de cabelo comprido ela tem um rabo enorme e peludo."

Esse tipo de customização — adaptar histórias clássicas com personagens e universos que a criança já ama — é um diferencial positivo do produto.

---

## System prompt do subagente

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

## Função de montagem do prompt (user message)

```javascript
function buildPrompt({ childName, characters, theme, lesson, size, reference }) {
  const sizeMap = {
    curta: '300 palavras',
    média: '600 palavras',
    longa: '1000 palavras'
  }

  const referenceBlock = reference
    ? `\n\nINSPIRAÇÃO CRIATIVA (use como referência de estilo/estrutura, mas crie algo original):\n${reference}`
    : ''

  return `Crie uma história infantil com as seguintes características:

- PROTAGONISTA: ${childName} (incorpore o nome naturalmente na história)
- PERSONAGENS: ${characters}
- TEMA: ${theme}
- LIÇÃO A TRANSMITIR: ${lesson}
- TAMANHO: aproximadamente ${sizeMap[size]}${referenceBlock}`
}
```

---

## Chamada à API (backend)

```javascript
// POST /api/gerar-historia
app.post('/api/gerar-historia', async (req, res) => {
  const { childName, characters, theme, lesson, size, reference } = req.body

  const response = await anthropic.messages.create({
    model: 'claude-sonnet-4-20250514',
    max_tokens: 1500,
    system: SYSTEM_PROMPT_HISTORIAS, // constante com o system prompt acima
    messages: [{
      role: 'user',
      content: buildPrompt({ childName, characters, theme, lesson, size, reference })
    }]
  })

  const raw = response.content.find(b => b.type === 'text')?.text || ''
  const clean = raw.replace(/```json|```/g, '').trim()
  const historia = JSON.parse(clean)

  res.json(historia)
  // retorna: { titulo, historia, moral, personagens, tags }
})
```

> **Importante:** a chave da API Anthropic nunca vai para o cliente (app mobile ou browser). Ela fica exclusivamente no backend.

---

## Arquitetura de integração

### App mobile (React Native / Flutter)

```
App mobile → seu backend (Node/Python) → API Anthropic → resposta → app
```

O app envia os campos via JSON, recebe o objeto de história e renderiza no UI nativo (SwiftUI, Jetpack Compose, React Native, etc.).

### Chatbot embedado na plataforma web

```
Mãe digita no chat → orquestrador detecta intenção GERAR_HISTORIA
                   → coleta dados faltantes (pergunta à mãe se necessário)
                   → aciona subagente de histórias
                   → Claude gera o JSON
                   → história exibida no chat
```

O assistente principal age como **orquestrador**: detecta a intenção pela conversa em linguagem natural e passa os dados extraídos automaticamente para o subagente. A mãe não precisa preencher um formulário — ela só conversa.

---

## O que extrair do protótipo HTML para a codebase

O arquivo `gerador-historinhas.html` gerado durante a conversa é apenas um protótipo visual para testes. Para integrar na codebase real, os três elementos que importam são:

1. **System prompt** — guarde como constante no backend. Nunca exposto ao cliente.
2. **`buildPrompt(inputs)`** — monta a user message a partir dos campos coletados.
3. **Parser do JSON de resposta** — o Claude retorna `{ titulo, historia, moral, personagens, tags }` para renderizar no UI.

---

## Próximos passos sugeridos

- [ ] Botão "Regenerar" — nova versão com os mesmos inputs
- [ ] Exportar história como PDF para imprimir
- [ ] Campo "idade exata" para calibrar vocabulário com mais precisão
- [ ] Modo "continuar a história" — a mãe pede um novo capítulo
- [ ] Gerar código do backend (Node ou Python) estruturado para a codebase
