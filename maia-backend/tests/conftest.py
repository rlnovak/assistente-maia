import uuid
from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.db.models import UserProfile


@pytest.fixture()
def active_user() -> UserProfile:
    return UserProfile(
        id=uuid.uuid4(),
        email="test@example.com",
        plan="active",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture()
def inactive_user() -> UserProfile:
    return UserProfile(
        id=uuid.uuid4(),
        email="inactive@example.com",
        plan="inactive",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )


@pytest.fixture()
def client():
    from app.main import app
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture()
def valid_jwt(active_user: UserProfile) -> str:
    """Gera JWT válido assinado com SUPABASE_JWT_SECRET de teste."""
    from jose import jwt
    from app.core.config import settings
    payload = {
        "sub": str(active_user.id),
        "role": "authenticated",
        "iss": "supabase",
    }
    return jwt.encode(payload, settings.SUPABASE_JWT_SECRET, algorithm="HS256")


@pytest.fixture()
def invalid_jwt() -> str:
    return "Bearer invalid.token.here"
