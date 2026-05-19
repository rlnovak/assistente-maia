from datetime import datetime, timezone
from uuid import UUID

from app.core.config import settings
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
            .is_("deleted_at", "null")
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
        .is_("deleted_at", "null")
        .order("updated_at", desc=True)
        .execute()
    )
    return [ConversationListItem(**row) for row in (result.data or [])]


def list_messages(user_id: UUID, conversation_id: UUID) -> list[MessageOut]:
    client = get_supabase_client()

    conv = (
        client.table("conversations")
        .select("id")
        .eq("id", str(conversation_id))
        .eq("user_id", str(user_id))
        .is_("deleted_at", "null")
        .single()
        .execute()
    )
    if not conv.data:
        raise ValueError(f"Conversa {conversation_id} não encontrada para o usuário")

    result = (
        client.table("messages")
        .select("id,conversation_id,role,content,model_used,created_at")
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
    return list(reversed(messages))


def update_conversation_title(conversation_id: UUID, title: str) -> None:
    client = get_supabase_client()
    client.table("conversations").update({"title": title}).eq("id", str(conversation_id)).execute()


def delete_conversation(user_id: UUID, conversation_id: UUID) -> None:
    client = get_supabase_client()
    now = datetime.now(timezone.utc).isoformat()
    result = (
        client.table("conversations")
        .update({"deleted_at": now})
        .eq("id", str(conversation_id))
        .eq("user_id", str(user_id))
        .execute()
    )
    if not result.data:
        raise ValueError(f"Conversa {conversation_id} não encontrada para o usuário")


def export_conversation(user_id: UUID, conversation_id: UUID) -> str:
    client = get_supabase_client()

    conv_result = (
        client.table("conversations")
        .select("title,created_at")
        .eq("id", str(conversation_id))
        .eq("user_id", str(user_id))
        .single()
        .execute()
    )
    if not conv_result.data:
        raise ValueError(f"Conversa {conversation_id} não encontrada para o usuário")

    title = conv_result.data["title"]
    created_at = conv_result.data["created_at"][:10]

    msgs_result = (
        client.table("messages")
        .select("role,content,created_at")
        .eq("conversation_id", str(conversation_id))
        .order("created_at")
        .execute()
    )

    lines = [f"# {title}", f"*Conversa exportada em {created_at}*", "", "---", ""]
    for msg in (msgs_result.data or []):
        speaker = "Você" if msg["role"] == "user" else "MaIA"
        lines.append(f"**{speaker}:** {msg['content']}")
        lines.append("")
        lines.append("---")
        lines.append("")

    return "\n".join(lines)


def generate_title(first_user_message: str) -> str:
    import httpx

    prompt = (
        f"Em até 6 palavras em português, crie um título para uma conversa que começa com: "
        f"'{first_user_message}'. Responda APENAS o título, sem aspas, sem ponto final."
    )
    try:
        response = httpx.post(
            "https://api.openai.com/v1/chat/completions",
            headers={"Authorization": f"Bearer {settings.OPENAI_API_KEY}"},
            json={
                "model": settings.TITLE_LLM_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 30,
                "temperature": 0.5,
            },
            timeout=5.0,
        )
        response.raise_for_status()
        title = response.json()["choices"][0]["message"]["content"].strip()
        return title[:80] if title else "Nova conversa"
    except Exception:
        log.warning("generate_title_failed", exc_info=True)
        return "Nova conversa"
