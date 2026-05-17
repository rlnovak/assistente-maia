import re
from uuid import UUID

from app.core.logging import get_logger
from app.db.models import StoryGenerateRequest, StoryOut
from app.db.supabase import get_supabase_client
from app.llm.prompts.system_stories import (
    SYSTEM_PROMPT_STORIES,
    build_story_prompt,
    resolve_size,
)
from app.llm.story_client import StoryClient

log = get_logger(__name__)

_story_client = StoryClient()

# Padrões simples para extração de contexto do histórico do chat
_AGE_PATTERN = re.compile(
    r"(\d+)\s*(?:ano[s]?|mês(?:es)?)",
    re.IGNORECASE,
)
_NAME_INDICATORS = [
    "minha filha", "meu filho", "minha criança",
    "chama", "nome é", "nome dela", "nome dele",
]


def extract_context_from_conversations(user_id: UUID) -> dict:
    """Varre histórico do chat e extrai contexto relevante para histórias."""
    client = get_supabase_client()

    # Pega as últimas 50 mensagens do usuário em todas as conversas
    result = (
        client.table("messages")
        .select("content, role, conversations!inner(user_id)")
        .eq("conversations.user_id", str(user_id))
        .eq("role", "user")
        .order("created_at", desc=True)
        .limit(50)
        .execute()
    )

    messages = [row["content"] for row in (result.data or [])]
    full_text = " ".join(messages).lower()

    context: dict = {}

    # Tenta extrair idade
    age_matches = _AGE_PATTERN.findall(full_text)
    if age_matches:
        ages = [int(a) for a in age_matches if 1 <= int(a) <= 10]
        if ages:
            context["child_age"] = ages[0]

    # Tenta extrair interesses mencionados (palavras-chave simples)
    interest_keywords = [
        "dinossauro", "princesa", "super-herói", "cachorro", "gato",
        "unicórnio", "dragão", "fada", "robô", "astronauta", "sereia",
        "leão", "elefante", "coelho", "borboleta",
    ]
    found_interests = [kw for kw in interest_keywords if kw in full_text]
    if found_interests:
        context["interests"] = found_interests[:5]

    # Temas recentes (birra, sono, alimentação etc.)
    topic_keywords = {
        "birra": "birras e emoções",
        "sono": "rotina de sono",
        "alimentação": "alimentação",
        "escola": "escola e socialização",
        "medo": "medos infantis",
        "amigo": "amizades",
        "compartilhar": "compartilhar",
        "limite": "limites e regras",
    }
    found_topics = [label for kw, label in topic_keywords.items() if kw in full_text]
    if found_topics:
        context["recent_topics"] = found_topics[:3]

    log.info("story_context_extracted", user_id=str(user_id), context_keys=list(context.keys()))
    return context


def create_story(user_id: UUID, req: StoryGenerateRequest) -> StoryOut:
    context = extract_context_from_conversations(user_id)

    # Resolve tamanho (com fallback por idade)
    size = resolve_size(req.size, req.child_age or context.get("child_age"))

    # Monta prompt
    user_prompt = build_story_prompt(
        child_name=req.child_name,
        characters=req.characters,
        theme=req.theme,
        lesson=req.lesson,
        size=size,
        reference=req.reference,
        context=context if context else None,
    )

    # Gera história
    output = _story_client.generate(
        system_prompt=SYSTEM_PROMPT_STORIES,
        user_prompt=user_prompt,
    )

    # Salva no DB
    db = get_supabase_client()
    payload = {
        "user_id": str(user_id),
        "child_name": req.child_name,
        "characters": req.characters,
        "theme": req.theme,
        "lesson": req.lesson,
        "size": size,
        "reference": req.reference,
        "child_age": req.child_age,
        "titulo": output.titulo,
        "historia": output.historia,
        "moral": output.moral,
        "personagens": output.personagens,
        "tags": output.tags,
        "model_used": output.model_used,
        "context_extracted": context,
    }
    result = db.table("stories").insert(payload).execute()
    row = result.data[0]
    log.info("story_saved", story_id=row["id"], user_id=str(user_id))
    return StoryOut(**row)


def get_stories(
    user_id: UUID,
    child_name: str | None = None,
    tag: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> list[StoryOut]:
    db = get_supabase_client()
    query = (
        db.table("stories")
        .select("*")
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .range(offset, offset + limit - 1)
    )
    if child_name:
        query = query.ilike("child_name", f"%{child_name}%")
    if tag:
        query = query.contains("tags", [tag])

    result = query.execute()
    return [StoryOut(**row) for row in (result.data or [])]


def get_story(user_id: UUID, story_id: UUID) -> StoryOut:
    db = get_supabase_client()
    result = (
        db.table("stories")
        .select("*")
        .eq("id", str(story_id))
        .eq("user_id", str(user_id))
        .single()
        .execute()
    )
    if not result.data:
        raise ValueError(f"História {story_id} não encontrada")
    return StoryOut(**result.data)


def rate_story(user_id: UUID, story_id: UUID, rating: int, notes: str | None) -> StoryOut:
    db = get_supabase_client()
    payload: dict = {"rating": rating}
    if notes is not None:
        payload["rating_notes"] = notes

    result = (
        db.table("stories")
        .update(payload)
        .eq("id", str(story_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    if not result.data:
        raise ValueError(f"História {story_id} não encontrada")
    log.info("story_rated", story_id=str(story_id), rating=rating)
    return StoryOut(**result.data[0])
