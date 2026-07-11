from abc import ABC, abstractmethod
from dataclasses import dataclass

from app.core.config import settings


@dataclass
class LLMMessage:
    role: str  # 'user' | 'assistant'
    content: str


@dataclass
class CompletionResult:
    text: str
    input_tokens: int
    output_tokens: int
    stop_reason: str
    model_used: str


DEFAULT_MAX_TOKENS = 2048


class LLMClient(ABC):
    @abstractmethod
    def complete(
        self,
        messages: list[LLMMessage],
        system: str,
        model: str,
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **kwargs,
    ) -> CompletionResult:
        ...


def get_llm_client() -> LLMClient:
    """Retorna a implementação configurada via LLM_PROVIDER."""
    provider = settings.LLM_PROVIDER
    if provider == "anthropic":
        from app.llm.anthropic_client import AnthropicClient
        return AnthropicClient(api_key=settings.ANTHROPIC_API_KEY)
    if provider == "openai":
        from app.llm.openai_client import OpenAIClient
        return OpenAIClient(api_key=settings.OPENAI_API_KEY)
    raise ValueError(f"LLM_PROVIDER inválido: {provider}")
