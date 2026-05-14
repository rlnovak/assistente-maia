from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import get_current_user
from app.db.models import ConversationListItem, MessageOut, UserProfile
from app.services.conversation_service import list_conversations, list_messages

router = APIRouter()


@router.get("/conversations", response_model=list[ConversationListItem])
def get_conversations(
    current_user: UserProfile = Depends(get_current_user),
) -> list[ConversationListItem]:
    return list_conversations(current_user.id)


@router.get("/conversations/{conversation_id}/messages", response_model=list[MessageOut])
def get_messages(
    conversation_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
) -> list[MessageOut]:
    try:
        return list_messages(current_user.id, conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
