from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel

from app.api.deps import get_current_user
from app.db.models import ConversationListItem, MessageOut, UserProfile
from app.services.conversation_service import (
    delete_conversation,
    export_conversation,
    list_conversations,
    list_messages,
    update_conversation_title,
)

router = APIRouter()


class ConversationRenameRequest(BaseModel):
    title: str


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


@router.patch("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def rename_conversation(
    conversation_id: UUID,
    body: ConversationRenameRequest,
    current_user: UserProfile = Depends(get_current_user),
) -> Response:
    try:
        update_conversation_title(conversation_id, body.title.strip() or "Nova conversa")
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/conversations/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_conversation(
    conversation_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
) -> Response:
    try:
        delete_conversation(current_user.id, conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/conversations/{conversation_id}/export")
def export_conversation_endpoint(
    conversation_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
) -> dict:
    try:
        markdown = export_conversation(current_user.id, conversation_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    return {"markdown": markdown}
