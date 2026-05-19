from uuid import UUID

import structlog

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import ChatResponse, MessageOut
from app.llm.llm_client import LLMMessage, get_llm_client
from app.llm.prompts import get_system_prompt
from app.rag.embeddings import embed_single
from app.rag.vector_store import get_vector_store
from app.services.conversation_service import (
    generate_title,
    get_or_create_conversation,
    get_recent_messages,
    save_message,
    update_conversation_title,
)
from app.services.profile_service import extract_and_update_profile, get_or_create_profile

log = get_logger(__name__)

_RAG_TOP_K = 5
_HISTORY_LIMIT = 10


def _build_rag_context(query: str) -> str:
    """Recupera chunks relevantes e formata como bloco de contexto."""
    try:
        vector = embed_single(query)
        store = get_vector_store()
        results = store.query(vector, top_k=_RAG_TOP_K)
        if not results:
            return ""
        chunks = "\n\n---\n\n".join(r.content for r in results)
        return f"<contexto_rag>\n{chunks}\n</contexto_rag>"
    except Exception:
        log.warning("rag_context_failed", exc_info=True)
        return ""


def handle_chat(user_id: UUID, message: str, conversation_id: UUID | None) -> ChatResponse:
    log.info("chat_start", user_id=str(user_id), provider=settings.LLM_PROVIDER, model=settings.LLM_MODEL)

    # 1. Busca ou cria conversa
    conversation = get_or_create_conversation(user_id, conversation_id)

    # 2. Persiste mensagem do usuário
    save_message(conversation.id, role="user", content=message)

    # 3. Histórico recente
    history = get_recent_messages(conversation.id, limit=_HISTORY_LIMIT)
    history_messages = [
        LLMMessage(role=m.role, content=m.content)
        for m in history[:-1]
    ]
    history_messages.append(LLMMessage(role="user", content=message))

    # 4. Perfil da família
    profile = get_or_create_profile(user_id)

    # 5. RAG context
    rag_context = _build_rag_context(message)
    system = get_system_prompt(profile=profile)
    if rag_context:
        system = f"{system}\n\n{rag_context}"

    # 6. Chama LLM via factory
    llm = get_llm_client()
    result = llm.complete(
        messages=history_messages,
        system=system,
        model=settings.LLM_MODEL,
    )

    log.info(
        "chat_complete",
        provider=settings.LLM_PROVIDER,
        model=result.model_used,
        tokens_in=result.input_tokens,
        tokens_out=result.output_tokens,
        stop_reason=result.stop_reason,
    )

    # 7. Persiste resposta do assistente
    assistant_msg = save_message(
        conversation.id,
        role="assistant",
        content=result.text,
        model_used=result.model_used,
        tokens_in=result.input_tokens,
        tokens_out=result.output_tokens,
    )

    # 8. Extrai perfil da mensagem do usuário (não bloqueia)
    try:
        extract_and_update_profile(user_id, message)
    except Exception:
        log.warning("profile_extract_error", exc_info=True)

    # 9. Gera título automático na primeira mensagem
    if conversation.title == "Nova conversa":
        try:
            title = generate_title(message)
            update_conversation_title(conversation.id, title)
        except Exception:
            log.warning("title_generation_error", exc_info=True)

    return ChatResponse(
        conversation_id=conversation.id,
        message=MessageOut(
            id=assistant_msg.id,
            conversation_id=conversation.id,
            role="assistant",
            content=result.text,
            model_used=result.model_used,
            created_at=assistant_msg.created_at,
        ),
    )
