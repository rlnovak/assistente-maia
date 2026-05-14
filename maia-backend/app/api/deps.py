from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError

from app.core.security import extract_user_id
from app.db.models import UserProfile
from app.db.supabase import get_supabase_client

_bearer = HTTPBearer()


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(_bearer),
) -> UserProfile:
    token = credentials.credentials

    try:
        user_id = extract_user_id(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido ou expirado",
        )

    client = get_supabase_client()
    result = (
        client.table("profiles")
        .select("*")
        .eq("id", user_id)
        .single()
        .execute()
    )

    if not result.data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Usuário não encontrado",
        )

    profile = UserProfile(**result.data)

    if profile.plan not in ("trial", "active"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Plano inativo. Acesse o painel para reativar.",
        )

    return profile
