from fastapi import APIRouter, Depends, HTTPException, Request, status

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.db.models import ChatRequest, ChatResponse, UserProfile
from app.services.chat_service import handle_chat

router = APIRouter()
log = get_logger(__name__)


@router.post("/chat", response_model=ChatResponse)
def post_chat(
    request: Request,
    body: ChatRequest,
    current_user: UserProfile = Depends(get_current_user),
) -> ChatResponse:
    request_id = getattr(request.state, "request_id", "?")
    log.info(
        "chat_request",
        request_id=request_id,
        user_id=str(current_user.id),
        conversation_id=str(body.conversation_id) if body.conversation_id else None,
    )
    try:
        return handle_chat(
            user_id=current_user.id,
            message=body.message,
            conversation_id=body.conversation_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception:
        log.error("chat_unhandled_error", request_id=request_id, exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro interno. Tente novamente.",
        )
