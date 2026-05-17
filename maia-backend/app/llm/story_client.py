import json
import re
from dataclasses import dataclass

from app.core.config import settings
from app.core.logging import get_logger
from app.llm.llm_client import LLMMessage

log = get_logger(__name__)

_MAX_TOKENS_STORIES = 3000  # histórias longas chegam a ~1000 palavras


@dataclass
class StoryOutput:
    titulo: str
    historia: str
    moral: str
    personagens: list[str]
    tags: list[str]
    model_used: str


class StoryParseError(Exception):
    pass


def _parse_story_json(raw: str) -> dict:
    """Extrai e valida JSON da resposta do LLM."""
    # remove blocos markdown se o modelo ignorar a instrução
    clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
    try:
        data = json.loads(clean)
    except json.JSONDecodeError as e:
        raise StoryParseError(f"JSON inválido na resposta do modelo: {e}") from e

    required = {"titulo", "historia", "moral", "personagens", "tags"}
    missing = required - data.keys()
    if missing:
        raise StoryParseError(f"Campos ausentes na resposta: {missing}")

    return data


def _get_story_llm_client():
    """Cliente LLM para geração de histórias — provider configurável independente do chat."""
    provider = settings.STORIES_LLM_PROVIDER
    if provider == "anthropic":
        from app.llm.anthropic_client import AnthropicClient
        return AnthropicClient(api_key=settings.ANTHROPIC_API_KEY), settings.STORIES_LLM_MODEL
    if provider == "openai":
        from app.llm.openai_client import OpenAIClient
        return OpenAIClient(api_key=settings.OPENAI_API_KEY), settings.STORIES_LLM_MODEL
    raise ValueError(f"STORIES_LLM_PROVIDER inválido: {provider}")


class StoryClient:
    def generate(self, system_prompt: str, user_prompt: str) -> StoryOutput:
        client, model = _get_story_llm_client()

        log.info("story_generate_start", model=model)
        result = client.complete(
            messages=[LLMMessage(role="user", content=user_prompt)],
            system=system_prompt,
            model=model,
            max_tokens=_MAX_TOKENS_STORIES,
        )

        try:
            data = _parse_story_json(result.text)
        except StoryParseError:
            log.warning("story_parse_error_retry", raw=result.text[:200])
            raise

        log.info(
            "story_generate_done",
            model=result.model_used,
            tokens_in=result.input_tokens,
            tokens_out=result.output_tokens,
        )

        return StoryOutput(
            titulo=data["titulo"],
            historia=data["historia"],
            moral=data["moral"],
            personagens=data.get("personagens", []),
            tags=data.get("tags", []),
            model_used=result.model_used,
        )
