from uuid import UUID

from app.core.logging import get_logger
from app.db.models import Conversation, ConversationListItem, Message, MessageOut
from app.db.supabase import get_supabase_client

log = get_logger(__name__)


def get_or_create_conversation(user_id: UUID, conversation_id: UUID | None) -> Conversation:
    client = get_supabase_client()

    if conversation_id:
        result = (
            client.table("conversations")
            .select("*")
            .eq("id", str(conversation_id))
            .eq("user_id", str(user_id))
            .single()
            .execute()
        )
        if not result.data:
            raise ValueError(f"Conversa {conversation_id} não encontrada para o usuário")
        return Conversation(**result.data)

    result = (
        client.table("conversations")
        .insert({"user_id": str(user_id), "title": "Nova conversa"})
        .execute()
    )
    return Conversation(**result.data[0])


def list_conversations(user_id: UUID) -> list[ConversationListItem]:
    client = get_supabase_client()
    result = (
        client.table("conversations")
        .select("id,title,created_at,updated_at")
        .eq("user_id", str(user_id))
        .order("updated_at", desc=True)
        .execute()
    )
    return [ConversationListItem(**row) for row in (result.data or [])]


def list_messages(user_id: UUID, conversation_id: UUID) -> list[MessageOut]:
    client = get_supabase_client()

    # Verifica ownership antes de retornar mensagens
    conv = (
        client.table("conversations")
        .select("id")
        .eq("id", str(conversation_id))
        .eq("user_id", str(user_id))
        .single()
        .execute()
    )
    if not conv.data:
        raise ValueError(f"Conversa {conversation_id} não encontrada para o usuário")

    result = (
        client.table("messages")
        .select("id,role,content,model_used,created_at")
        .eq("conversation_id", str(conversation_id))
        .order("created_at")
        .execute()
    )
    return [MessageOut(**row) for row in (result.data or [])]


def save_message(
    conversation_id: UUID,
    role: str,
    content: str,
    model_used: str | None = None,
    tokens_in: int | None = None,
    tokens_out: int | None = None,
) -> Message:
    client = get_supabase_client()
    payload = {
        "conversation_id": str(conversation_id),
        "role": role,
        "content": content,
    }
    if model_used is not None:
        payload["model_used"] = model_used
    if tokens_in is not None:
        payload["tokens_in"] = tokens_in
    if tokens_out is not None:
        payload["tokens_out"] = tokens_out

    result = client.table("messages").insert(payload).execute()
    return Message(**result.data[0])


def get_recent_messages(conversation_id: UUID, limit: int = 10) -> list[Message]:
    client = get_supabase_client()
    result = (
        client.table("messages")
        .select("*")
        .eq("conversation_id", str(conversation_id))
        .order("created_at", desc=True)
        .limit(limit)
        .execute()
    )
    messages = [Message(**row) for row in (result.data or [])]
    return list(reversed(messages))  # ordem cronológica
