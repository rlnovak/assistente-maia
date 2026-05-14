import openai
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.llm.llm_client import CompletionResult, LLMClient, LLMMessage

_MAX_TOKENS = 2048


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, openai.RateLimitError):
        return True
    if isinstance(exc, openai.APIStatusError) and exc.status_code >= 500:
        return True
    return False


class OpenAIClient(LLMClient):
    def __init__(self, api_key: str) -> None:
        self._client = openai.OpenAI(api_key=api_key)

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
        # OpenAI: system prompt como primeira mensagem com role="system"
        openai_messages = [{"role": "system", "content": system}]
        openai_messages += [{"role": m.role, "content": m.content} for m in messages]

        response = self._client.chat.completions.create(
            model=model,
            messages=openai_messages,
            max_completion_tokens=_MAX_TOKENS,
            **kwargs,
        )
        choice = response.choices[0]
        usage = response.usage
        return CompletionResult(
            text=choice.message.content or "",
            input_tokens=usage.prompt_tokens if usage else 0,
            output_tokens=usage.completion_tokens if usage else 0,
            stop_reason=choice.finish_reason or "stop",
            model_used=response.model,
        )
