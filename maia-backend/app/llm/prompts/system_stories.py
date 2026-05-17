SYSTEM_PROMPT_STORIES = """Você é um especialista em literatura infantil, com profundo conhecimento em desenvolvimento infantil para crianças de 1 a 5 anos. Você cria histórias encantadoras, originais e pedagogicamente ricas.

REGRAS INVIOLÁVEIS:
- Linguagem simples, frases curtas, vocabulário acessível para crianças pequenas
- Tom acolhedor, divertido e imaginativo — jamais assustador ou triste demais
- A lição deve emergir NATURALMENTE da história, nunca de forma explícita ou didática
- Personagens com personalidade marcante, ações concretas, diálogos vivos
- Estrutura narrativa clara: situação inicial → desafio → tentativas → resolução feliz
- Jamais mencione violência, medo intenso ou temas inadequados para a faixa etária
- Escreva em português brasileiro fluente e expressivo

FORMATO DA RESPOSTA (JSON puro, sem markdown, sem ```):
{
  "titulo": "título criativo da história",
  "historia": "texto completo da história em parágrafos separados por \\n\\n",
  "moral": "a lição da história em uma frase bonita e memorável",
  "personagens": ["lista", "dos", "personagens"],
  "tags": ["tema1", "tema2"]
}"""

# Palavras aproximadas por tamanho escolhido pela mãe
SIZE_MAP: dict[str, str] = {
    "curta": "300 palavras",
    "media": "600 palavras",
    "longa": "1000 palavras",
}

# Fallback quando mãe não sabe o tamanho mas informa a idade
AGE_SIZE_FALLBACK: dict[int, str] = {
    1: "curta",
    2: "curta",
    3: "curta",
    4: "media",
    5: "media",
}
DEFAULT_SIZE = "curta"


def resolve_size(size: str, child_age: int | None) -> str:
    """Retorna o size canônico, usando fallback por idade se necessário."""
    if size in SIZE_MAP:
        return size
    if child_age is not None:
        return AGE_SIZE_FALLBACK.get(child_age, DEFAULT_SIZE)
    return DEFAULT_SIZE


def build_story_prompt(
    child_name: str,
    characters: list[str],
    theme: str,
    lesson: str,
    size: str,
    reference: str | None = None,
    context: dict | None = None,
) -> str:
    characters_str = ", ".join(characters)
    word_count = SIZE_MAP.get(size, SIZE_MAP[DEFAULT_SIZE])

    reference_block = (
        f"\n\nINSPIRAÇÃO CRIATIVA (use como referência de estilo/estrutura, mas crie algo original):\n{reference}"
        if reference
        else ""
    )

    context_parts = []
    if context:
        if context.get("child_age"):
            context_parts.append(f"Idade da criança: {context['child_age']} anos")
        if context.get("interests"):
            context_parts.append(f"Interesses mencionados: {', '.join(context['interests'])}")
        if context.get("recent_topics"):
            context_parts.append(f"Temas recentes nas conversas: {', '.join(context['recent_topics'])}")
    context_block = (
        f"\n\nCONTEXTO DA CRIANÇA (extraído do histórico de conversas — use para enriquecer a história):\n"
        + "\n".join(context_parts)
        if context_parts
        else ""
    )

    return f"""Crie uma história infantil com as seguintes características:

- PROTAGONISTA: {child_name} (incorpore o nome naturalmente na história)
- PERSONAGENS: {characters_str}
- TEMA: {theme}
- LIÇÃO A TRANSMITIR: {lesson}
- TAMANHO: aproximadamente {word_count}{reference_block}{context_block}"""
