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


class ChatResponse(BaseModel):
    conversation_id: UUID
    message_id: UUID
    content: str
    model_used: str
    tokens_in: int
    tokens_out: int


class ConversationListItem(BaseModel):
    id: UUID
    title: str
    created_at: datetime
    updated_at: datetime


class MessageOut(BaseModel):
    id: UUID
    role: str
    content: str
    model_used: str | None = None
    created_at: datetime
