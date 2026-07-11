import openai
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential

from app.llm.llm_client import DEFAULT_MAX_TOKENS, CompletionResult, LLMClient, LLMMessage

# Endpoint compatível com OpenAI da Alibaba (DashScope, região internacional).
# Região China: https://dashscope.aliyuncs.com/compatible-mode/v1
DASHSCOPE_BASE_URL = "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"


def _is_retryable(exc: BaseException) -> bool:
    if isinstance(exc, openai.RateLimitError):
        return True
    if isinstance(exc, openai.APIStatusError) and exc.status_code >= 500:
        return True
    return False


class QwenClient(LLMClient):
    """Qwen via API compatível com OpenAI (DashScope)."""

    def __init__(self, api_key: str, base_url: str = DASHSCOPE_BASE_URL) -> None:
        self._client = openai.OpenAI(api_key=api_key, base_url=base_url)

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
        max_tokens: int = DEFAULT_MAX_TOKENS,
        **kwargs,
    ) -> CompletionResult:
        qwen_messages = [{"role": "system", "content": system}]
        qwen_messages += [{"role": m.role, "content": m.content} for m in messages]

        # DashScope aceita max_tokens, não max_completion_tokens
        response = self._client.chat.completions.create(
            model=model,
            messages=qwen_messages,
            max_tokens=max_tokens,
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
