import anthropic
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.llm.llm_client import CompletionResult, LLMClient, LLMMessage

_SUPPORTED_MODELS = {"claude-sonnet-4-5", "claude-haiku-4-5-20251001"}
_MAX_TOKENS = 2048


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, anthropic.RateLimitError):
        return True
    if isinstance(exc, anthropic.APIStatusError) and exc.status_code >= 500:
        return True
    return False


class AnthropicClient(LLMClient):
    def __init__(self, api_key: str) -> None:
        self._client = anthropic.Anthropic(api_key=api_key)

    @retry(
        retry=retry_if_exception(_is_retryable),
        wait=wait_exponential(multiplier=1, min=2, max=30),
        stop=stop_after_attempt(4),
        reraise=True,
    )
    def complete(
        self,
        messages: list[LLMMessage],
        system: str,
        model: str,
        **kwargs,
    ) -> CompletionResult:
        anthropic_messages = [
            {"role": m.role, "content": m.content} for m in messages
        ]
        response = self._client.messages.create(
            model=model,
            system=system,
            messages=anthropic_messages,
            max_tokens=_MAX_TOKENS,
            **kwargs,
        )
        return CompletionResult(
            text=response.content[0].text,
            input_tokens=response.usage.input_tokens,
            output_tokens=response.usage.output_tokens,
            stop_reason=response.stop_reason or "end_turn",
            model_used=response.model,
        )
