from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from slowapi import Limiter
from slowapi.util import get_remote_address

from app.api.deps import get_current_user
from app.core.logging import get_logger
from app.db.models import (
    AudioGenerateRequest,
    AudioUrlResponse,
    StoryAudioOut,
    StoryGenerateRequest,
    StoryGenerateResponse,
    StoryOut,
    StoryRatingRequest,
    UserProfile,
    Voice,
)
from app.services import audio_service, story_service

router = APIRouter(prefix="/stories", tags=["stories"])
log = get_logger(__name__)
limiter = Limiter(key_func=get_remote_address)


# ── Vozes ─────────────────────────────────────────────────────────────────────

@router.get("/voices", response_model=list[Voice])
def get_voices() -> list[Voice]:
    return audio_service.list_voices()


# ── Geração ───────────────────────────────────────────────────────────────────

@router.post("/generate", response_model=StoryGenerateResponse, status_code=status.HTTP_201_CREATED)
def generate_story(
    request: Request,
    body: StoryGenerateRequest,
    current_user: UserProfile = Depends(get_current_user),
) -> StoryGenerateResponse:
    log.info("story_generate_request", user_id=str(current_user.id), theme=body.theme)
    try:
        story = story_service.create_story(user_id=current_user.id, req=body)
        return StoryGenerateResponse(story=story)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except Exception:
        log.error("story_generate_error", user_id=str(current_user.id), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar história. Tente novamente.",
        )


# ── Listagem e detalhe ────────────────────────────────────────────────────────

@router.get("", response_model=list[StoryOut])
def list_stories(
    current_user: UserProfile = Depends(get_current_user),
    child_name: str | None = Query(None, description="Filtrar por nome da criança"),
    tag: str | None = Query(None, description="Filtrar por tag/tema"),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[StoryOut]:
    return story_service.get_stories(
        user_id=current_user.id,
        child_name=child_name,
        tag=tag,
        limit=limit,
        offset=offset,
    )


@router.get("/{story_id}", response_model=StoryOut)
def get_story(
    story_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
) -> StoryOut:
    try:
        return story_service.get_story(user_id=current_user.id, story_id=story_id)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Rating ────────────────────────────────────────────────────────────────────

@router.post("/{story_id}/rating", response_model=StoryOut)
def rate_story(
    story_id: UUID,
    body: StoryRatingRequest,
    current_user: UserProfile = Depends(get_current_user),
) -> StoryOut:
    try:
        return story_service.rate_story(
            user_id=current_user.id,
            story_id=story_id,
            rating=body.rating,
            notes=body.notes,
        )
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Áudio ─────────────────────────────────────────────────────────────────────

@router.post("/{story_id}/audio", response_model=StoryAudioOut, status_code=status.HTTP_201_CREATED)
def generate_audio(
    story_id: UUID,
    body: AudioGenerateRequest,
    current_user: UserProfile = Depends(get_current_user),
) -> StoryAudioOut:
    try:
        return audio_service.generate_audio(
            user_id=current_user.id,
            story_id=story_id,
            voice_id=body.voice_id,
        )
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception:
        log.error("audio_generate_error", story_id=str(story_id), exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Erro ao gerar áudio. Tente novamente.",
        )


@router.get("/{story_id}/audio", response_model=AudioUrlResponse)
def get_audio_url(
    story_id: UUID,
    current_user: UserProfile = Depends(get_current_user),
) -> AudioUrlResponse:
    try:
        return audio_service.get_audio_url(user_id=current_user.id, story_id=story_id)
    except NotImplementedError as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))


# ── Manutenção ────────────────────────────────────────────────────────────────

@router.post("/cleanup", include_in_schema=False)
def cleanup_expired_audios(
    current_user: UserProfile = Depends(get_current_user),
) -> dict:
    """Endpoint interno — chamado por cron externo para limpar áudios expirados."""
    deleted = audio_service.cleanup_expired_audios()
    return {"deleted": len(deleted), "paths": deleted}
