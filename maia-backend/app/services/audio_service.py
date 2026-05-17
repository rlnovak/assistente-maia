"""Serviço de geração de áudio via ElevenLabs."""
from datetime import datetime, timedelta, timezone
from uuid import UUID

import httpx

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import AudioUrlResponse, StoryAudioOut, Voice
from app.db.supabase import get_supabase_client

log = get_logger(__name__)

# Vozes pré-definidas disponíveis na v1
AVAILABLE_VOICES: list[Voice] = [
    Voice(
        id="21m00Tcm4TlvDq8ikWAM",
        name="Rachel",
        description="Voz feminina suave e clara, ideal para histórias infantis",
        preview_text="Era uma vez uma princesinha muito corajosa...",
    ),
    Voice(
        id="AZnzlk1XvdvUeBnXmlld",
        name="Domi",
        description="Voz feminina jovem e animada, ótima para aventuras",
        preview_text="Num reino muito distante, vivia um dragãozinho...",
    ),
    Voice(
        id="EXAVITQu4vr4xnSDxMaL",
        name="Bella",
        description="Voz feminina calorosa e acolhedora, perfeita para histórias de ninar",
        preview_text="A lua brilhava suave sobre o jardim encantado...",
    ),
]


def list_voices() -> list[Voice]:
    return AVAILABLE_VOICES


def _get_voice(voice_id: str) -> Voice | None:
    return next((v for v in AVAILABLE_VOICES if v.id == voice_id), None)


def generate_audio(user_id: UUID, story_id: UUID, voice_id: str) -> StoryAudioOut:
    """Gera áudio da história via ElevenLabs e salva no Supabase Storage."""
    if not settings.ELEVENLABS_API_KEY:
        raise NotImplementedError(
            "ELEVENLABS_API_KEY não configurada. Adicione a chave ao .env."
        )

    voice = _get_voice(voice_id)
    if not voice:
        raise ValueError(f"Voz '{voice_id}' não disponível. Use GET /v1/stories/voices para listar.")

    db = get_supabase_client()

    story_result = (
        db.table("stories")
        .select("id, historia")
        .eq("id", str(story_id))
        .eq("user_id", str(user_id))
        .single()
        .execute()
    )
    if not story_result.data:
        raise ValueError(f"História {story_id} não encontrada")

    historia_text = story_result.data["historia"]

    response = httpx.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers={"xi-api-key": settings.ELEVENLABS_API_KEY},
        json={
            "text": historia_text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.75},
        },
        timeout=60.0,
    )
    response.raise_for_status()
    audio_bytes = response.content

    storage_path = f"{user_id}/{story_id}.mp3"
    db.storage.from_(settings.SUPABASE_STORAGE_BUCKET_AUDIOS).upload(
        path=storage_path,
        file=audio_bytes,
        file_options={"content-type": "audio/mpeg"},
    )

    expires_at = datetime.now(timezone.utc) + timedelta(days=settings.AUDIO_EXPIRY_DAYS)

    result = (
        db.table("story_audios")
        .insert({
            "story_id": str(story_id),
            "user_id": str(user_id),
            "voice_id": voice_id,
            "voice_name": voice.name,
            "storage_path": storage_path,
            "expires_at": expires_at.isoformat(),
        })
        .execute()
    )

    log.info("story_audio_generated", story_id=str(story_id), voice_id=voice_id)
    return StoryAudioOut(**result.data[0])


def get_audio_url(user_id: UUID, story_id: UUID) -> AudioUrlResponse:
    """Retorna signed URL do Storage para o áudio da história."""
    db = get_supabase_client()
    result = (
        db.table("story_audios")
        .select("*")
        .eq("story_id", str(story_id))
        .eq("user_id", str(user_id))
        .order("created_at", desc=True)
        .limit(1)
        .execute()
    )
    if not result.data:
        raise ValueError(f"Nenhum áudio encontrado para história {story_id}")

    audio = result.data[0]
    expires_at = datetime.fromisoformat(audio["expires_at"])

    if datetime.now(timezone.utc) > expires_at:
        raise ValueError("Áudio expirado. Gere um novo áudio.")

    # Signed URL válida por 1 hora
    signed = db.storage.from_(settings.SUPABASE_STORAGE_BUCKET_AUDIOS).create_signed_url(
        path=audio["storage_path"],
        expires_in=3600,
    )
    return AudioUrlResponse(url=signed["signedURL"], expires_at=expires_at)


def cleanup_expired_audios() -> list[str]:
    """
    Remove registros de áudios expirados do DB e retorna os storage_paths
    para deleção manual ou pelo job de Storage.
    """
    db = get_supabase_client()
    result = db.rpc("cleanup_expired_audios").execute()
    paths = [row["deleted_storage_path"] for row in (result.data or [])]

    for path in paths:
        try:
            db.storage.from_(settings.SUPABASE_STORAGE_BUCKET_AUDIOS).remove([path])
        except Exception as e:
            log.warning("audio_storage_delete_failed", path=path, error=str(e))

    log.info("audio_cleanup_done", deleted_count=len(paths))
    return paths
