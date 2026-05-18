"""Testes do endpoint /v1/chat com mocks de VectorStore e LLMClient."""
import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.models import ChatResponse, UserProfile
from app.llm.llm_client import CompletionResult


def _make_token(user_id: str) -> str:
    from jose import jwt
    from app.core.config import settings
    return jwt.encode(
        {"sub": user_id, "role": "authenticated", "iss": "supabase"},
        settings.SUPABASE_JWT_SECRET,
        algorithm="HS256",
    )


def _mock_supabase_with_user(user_id: str, plan: str = "active"):
    profile_data = {
        "id": user_id,
        "email": "test@test.com",
        "plan": plan,
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    mock_result = MagicMock()
    mock_result.data = profile_data

    mock_client = MagicMock()
    mock_table = MagicMock()
    mock_client.table.return_value = mock_table
    # profile lookup
    mock_table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
    mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = mock_result
    return mock_client


def test_chat_happy_path(client: TestClient):
    """POST /v1/chat com JWT válido, mocks de DB + LLM, retorna ChatResponse."""
    user_id = str(uuid.uuid4())
    conv_id = str(uuid.uuid4())
    msg_id = str(uuid.uuid4())
    token = _make_token(user_id)

    fake_completion = CompletionResult(
        text="Olá! Como posso ajudar?",
        input_tokens=50,
        output_tokens=20,
        stop_reason="end_turn",
        model_used="gpt-5.4",
    )

    # Mock Supabase client
    mock_supabase = _mock_supabase_with_user(user_id)

    conv_data = {
        "id": conv_id,
        "user_id": user_id,
        "title": "Nova conversa",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    msg_data = {
        "id": msg_id,
        "conversation_id": conv_id,
        "role": "assistant",
        "content": "Olá! Como posso ajudar?",
        "model_used": "gpt-5.4",
        "tokens_in": 50,
        "tokens_out": 20,
        "created_at": datetime.utcnow().isoformat(),
    }

    insert_result = MagicMock()
    insert_result.data = [conv_data]
    insert_msg_result = MagicMock()
    insert_msg_result.data = [{"id": str(uuid.uuid4()), "conversation_id": conv_id,
                               "role": "user", "content": "oi", "model_used": None,
                               "tokens_in": None, "tokens_out": None,
                               "created_at": datetime.utcnow().isoformat()}]
    insert_asst_result = MagicMock()
    insert_asst_result.data = [msg_data]

    history_result = MagicMock()
    history_result.data = []

    mock_table = MagicMock()
    mock_supabase.table.return_value = mock_table

    # profile
    profile_result = MagicMock()
    profile_result.data = {
        "id": user_id, "email": "t@t.com", "plan": "active",
        "created_at": datetime.utcnow().isoformat(),
        "updated_at": datetime.utcnow().isoformat(),
    }
    mock_table.select.return_value.eq.return_value.single.return_value.execute.return_value = profile_result
    mock_table.select.return_value.eq.return_value.eq.return_value.single.return_value.execute.return_value = profile_result
    mock_table.insert.return_value.execute.side_effect = [
        insert_result,       # create conversation
        insert_msg_result,   # save user message
        insert_asst_result,  # save assistant message
    ]
    mock_table.select.return_value.eq.return_value.order.return_value.limit.return_value.execute.return_value = history_result

    # Mock LLM
    mock_llm = MagicMock()
    mock_llm.complete.return_value = fake_completion

    # Mock VectorStore
    mock_store = MagicMock()
    mock_store.query.return_value = []

    with (
        patch("app.api.deps.get_supabase_client", return_value=mock_supabase),
        patch("app.services.conversation_service.get_supabase_client", return_value=mock_supabase),
        patch("app.services.chat_service.get_llm_client", return_value=mock_llm),
        patch("app.services.chat_service.get_vector_store", return_value=mock_store),
        patch("app.services.chat_service.embed_single", return_value=[0.0] * 1536),
    ):
        response = client.post(
            "/v1/chat",
            json={"message": "oi"},
            headers={"Authorization": f"Bearer {token}"},
        )

    assert response.status_code == 200
    data = response.json()
    assert data["message"]["content"] == "Olá! Como posso ajudar?"
    assert data["message"]["role"] == "assistant"
    assert data["message"]["model_used"] == "gpt-5.4"
    assert "conversation_id" in data


def test_system_prompt_anthropic():
    """system_anthropic.py é carregado quando provider=anthropic."""
    from app.llm.prompts import get_system_prompt
    from app.llm.prompts.system_anthropic import SYSTEM_PROMPT as ANTHROPIC_PROMPT
    result = get_system_prompt("anthropic")
    assert result == ANTHROPIC_PROMPT
    assert "<persona>" in result


def test_system_prompt_openai():
    """system_openai.py é carregado quando provider=openai."""
    from app.llm.prompts import get_system_prompt
    from app.llm.prompts.system_openai import SYSTEM_PROMPT as OPENAI_PROMPT
    result = get_system_prompt("openai")
    assert result == OPENAI_PROMPT
    assert "## Identidade" in result


def test_system_prompts_are_different():
    """Os dois prompts são arquivos distintos."""
    from app.llm.prompts import get_system_prompt
    assert get_system_prompt("anthropic") != get_system_prompt("openai")
