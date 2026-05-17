from functools import lru_cache
from typing import Literal

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # === App ===
    ENV: Literal["development", "production"] = "development"

    # === LLM ===
    LLM_PROVIDER: Literal["anthropic", "openai"] = "openai"
    LLM_MODEL: str = "gpt-5.4"
    ANTHROPIC_API_KEY: str = ""
    OPENAI_API_KEY: str = ""

    # === Embeddings (travado) ===
    EMBEDDING_PROVIDER: Literal["openai"] = "openai"
    EMBEDDING_MODEL: str = "text-embedding-3-small"

    # === Vector store ===
    VECTOR_STORE_BACKEND: Literal["local", "pinecone"] = "local"
    CHROMA_PATH: str = "./.chroma"
    CHROMA_COLLECTION: str = "maia-rag"
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX: str = ""
    PINECONE_ENVIRONMENT: str = ""

    # === Supabase ===
    SUPABASE_URL: str = ""
    SUPABASE_ANON_KEY: str = ""
    SUPABASE_SERVICE_ROLE_KEY: str = ""
    SUPABASE_JWT_SECRET: str = ""

    # === Email ===
    RESEND_API_KEY: str = ""

    # === Stories LLM (independente do chat) ===
    STORIES_LLM_PROVIDER: Literal["anthropic", "openai"] = "anthropic"
    STORIES_LLM_MODEL: str = "claude-sonnet-4-6"

    # === ElevenLabs (áudio) ===
    ELEVENLABS_API_KEY: str = ""

    # === Storage ===
    SUPABASE_STORAGE_BUCKET_AUDIOS: str = "story-audios"
    AUDIO_EXPIRY_DAYS: int = 7

    @model_validator(mode="after")
    def validate_llm_config(self) -> "Settings":
        if self.LLM_PROVIDER == "anthropic":
            if not self.ANTHROPIC_API_KEY:
                raise ValueError("ANTHROPIC_API_KEY obrigatória quando LLM_PROVIDER=anthropic")
            if not self.LLM_MODEL.startswith("claude-"):
                raise ValueError(
                    f"LLM_MODEL inválido para provider anthropic: '{self.LLM_MODEL}'. "
                    "Deve começar com 'claude-'."
                )
        elif self.LLM_PROVIDER == "openai":
            if not self.OPENAI_API_KEY:
                raise ValueError("OPENAI_API_KEY obrigatória quando LLM_PROVIDER=openai")
            if not self.LLM_MODEL.startswith("gpt-"):
                raise ValueError(
                    f"LLM_MODEL inválido para provider openai: '{self.LLM_MODEL}'. "
                    "Deve começar com 'gpt-'."
                )
        return self

    @model_validator(mode="after")
    def validate_pinecone_config(self) -> "Settings":
        if self.VECTOR_STORE_BACKEND == "pinecone":
            missing = [
                k for k, v in {
                    "PINECONE_API_KEY": self.PINECONE_API_KEY,
                    "PINECONE_INDEX": self.PINECONE_INDEX,
                    "PINECONE_ENVIRONMENT": self.PINECONE_ENVIRONMENT,
                }.items() if not v
            ]
            if missing:
                raise ValueError(
                    f"VECTOR_STORE_BACKEND=pinecone exige: {', '.join(missing)}"
                )
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
