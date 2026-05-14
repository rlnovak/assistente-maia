"""Testes de autenticação e autorização."""
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.models import UserProfile


def test_health_public(client: TestClient):
    """Health endpoint não requer auth."""
    response = client.get("/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_chat_without_jwt_returns_401(client: TestClient):
    response = client.post("/v1/chat", json={"message": "oi"})
    assert response.status_code == 403  # HTTPBearer retorna 403 quando header ausente


def test_chat_with_invalid_jwt_returns_401(client: TestClient):
    response = client.post(
        "/v1/chat",
        json={"message": "oi"},
        headers={"Authorization": "Bearer token.invalido.aqui"},
    )
    assert response.status_code == 401


def test_chat_with_inactive_plan_returns_403(client: TestClient):
    """Usuário com plano inativo recebe 403."""
    from jose import jwt
    from app.core.config import settings

    user_id = str(uuid.uuid4())
    token = jwt.encode(
        {"sub": user_id, "role": "authenticated", "iss": "supabase"},
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )

    inactive_profile = {
        "id": user_id,
        "email": "test@test.com",
        "plan": "inactive",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }

    mock_result = MagicMock()
    mock_result.data = inactive_profile

    with patch("app.api.deps.get_supabase_client") as mock_client:
        mock_table = MagicMock()
        mock_client.return_value.table.return_value = mock_table
        mock_table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result

        response = client.post(
            "/v1/chat",
            json={"message": "oi"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 403


def test_vector_store_pinecone_factory():
    """Trocar VECTOR_STORE_BACKEND=pinecone instancia PineconeVectorStore (abstração plugada)."""
    from unittest.mock import patch
    import os

    with patch.dict(os.environ, {
        "VECTOR_STORE_BACKEND": "pinecone",
        "PINECONE_API_KEY": "fake-key",
        "PINECONE_INDEX": "fake-index",
        "PINECONE_ENVIRONMENT": "fake-env",
    }):
        # Força reload das settings para pegar as envs mockadas
        from app.core.config import Settings
        test_settings = Settings(
            VECTOR_STORE_BACKEND="pinecone",
            PINECONE_API_KEY="fake-key",
            PINECONE_INDEX="fake-index",
            PINECONE_ENVIRONMENT="fake-env",
            OPENAI_API_KEY="fake",
            LLM_PROVIDER="openai",
            LLM_MODEL="gpt-5.4",
        )
        from app.rag.vector_store import PineconeVectorStore
        store = PineconeVectorStore(settings=test_settings)

        with pytest.raises(NotImplementedError):
            store.query(vector=[0.0] * 1536, top_k=5)


def test_llm_client_factory_anthropic():
    """Factory retorna AnthropicClient quando LLM_PROVIDER=anthropic."""
    from app.core.config import Settings
    test_settings = Settings(
        LLM_PROVIDER="anthropic",
        LLM_MODEL="claude-sonnet-4-5",
        ANTHROPIC_API_KEY="fake-ant-key",
        OPENAI_API_KEY="fake-oai-key",
    )
    with patch("app.llm.llm_client.settings", test_settings):
        from app.llm.llm_client import get_llm_client
        from app.llm.anthropic_client import AnthropicClient
        client = get_llm_client()
        assert isinstance(client, AnthropicClient)


def test_llm_client_factory_openai():
    """Factory retorna OpenAIClient quando LLM_PROVIDER=openai."""
    from app.core.config import Settings
    test_settings = Settings(
        LLM_PROVIDER="openai",
        LLM_MODEL="gpt-5.4",
        OPENAI_API_KEY="fake-oai-key",
        ANTHROPIC_API_KEY="fake-ant-key",
    )
    with patch("app.llm.llm_client.settings", test_settings):
        from app.llm.llm_client import get_llm_client
        from app.llm.openai_client import OpenAIClient
        client = get_llm_client()
        assert isinstance(client, OpenAIClient)
