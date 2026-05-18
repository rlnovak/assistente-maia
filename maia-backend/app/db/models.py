from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


# ── Supabase entities ──────────────────────────────────────────────────────────

class UserProfile(BaseModel):
    id: UUID
    email: str | None = None
    plan: str  # 'trial' | 'active' | 'inactive'
    created_at: datetime
    updated_at: datetime


class Conversation(BaseModel):
    id: UUID
    user_id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class Message(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str  # 'user' | 'assistant'
    content: str
    model_used: str | None = None
    tokens_in: int | None = None
    tokens_out: int | None = None
    created_at: datetime


# ── API request / response ─────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    conversation_id: UUID | None = None


class MessageOut(BaseModel):
    id: UUID
    conversation_id: UUID
    role: str
    content: str
    model_used: str | None = None
    created_at: datetime


class ChatResponse(BaseModel):
    conversation_id: UUID
    message: MessageOut


class ConversationListItem(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


# ── Stories ────────────────────────────────────────────────────────────────────

class StoryGenerateRequest(BaseModel):
    child_name: str = Field(..., min_length=1, max_length=100)
    characters: list[str] = Field(..., min_length=1)
    theme: str = Field(..., min_length=1, max_length=500)
    lesson: str = Field(..., min_length=1, max_length=500)
    size: str = Field(..., pattern="^(curta|media|longa)$")
    reference: str | None = Field(None, max_length=1000)
    child_age: int | None = Field(None, ge=1, le=10)


class StoryOut(BaseModel):
    id: UUID
    user_id: UUID
    child_name: str
    characters: list[str]
    theme: str
    lesson: str
    size: str
    reference: str | None = None
    child_age: int | None = None
    titulo: str | None = None
    historia: str | None = None
    moral: str | None = None
    personagens: list[str] = []
    tags: list[str] = []
    model_used: str | None = None
    rating: int | None = None
    rating_notes: str | None = None
    created_at: datetime
    updated_at: datetime


class StoryRatingRequest(BaseModel):
    rating: int = Field(..., ge=1, le=5)
    notes: str | None = Field(None, max_length=1000)


class StoryGenerateResponse(BaseModel):
    story: StoryOut


# ── Story Audios ───────────────────────────────────────────────────────────────

class AudioGenerateRequest(BaseModel):
    voice_id: str = Field(..., min_length=1)


class StoryAudioOut(BaseModel):
    id: UUID
    story_id: UUID
    voice_id: str
    voice_name: str | None = None
    expires_at: datetime
    created_at: datetime


class AudioUrlResponse(BaseModel):
    url: str
    expires_at: datetime


class Voice(BaseModel):
    id: str
    name: str
    description: str
    preview_text: str
