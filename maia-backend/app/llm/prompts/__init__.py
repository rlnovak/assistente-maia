from app.core.config import settings


def get_system_prompt(provider: str | None = None) -> str:
    """Retorna o system prompt correto para o provider ativo."""
    provider = provider or settings.LLM_PROVIDER
    if provider == "anthropic":
        from app.llm.prompts.system_anthropic import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    if provider == "openai":
        from app.llm.prompts.system_openai import SYSTEM_PROMPT
        return SYSTEM_PROMPT
    raise ValueError(f"Provider sem prompt definido: {provider}")